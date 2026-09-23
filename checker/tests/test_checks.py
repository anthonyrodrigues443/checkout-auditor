"""Hand-written checkpoint fixtures for L1 (honest), L3 (pre-ticked add-on) and an L4-style store."""
import json

import pytest

from checker.checks import (
    check_run,
    is_charge_label,
    match_lines,
    normalise_label,
    stated_numbers,
)
from checker.score import load_key_for, main, match_findings_to_traps, score_run


def li(label, amount, chosen=False, pre=False):
    return {"label": label, "amount": amount, "chosen_by_me": chosen, "pre_selected": pre}


def cp(items, total, step=2):
    return {
        "line_items": items,
        "total": total,
        "url": "http://localhost:8000/page.html",
        "step": step,
        "screenshot": f"screenshots/run/step_{step:02d}.png",
    }


def click(step, text, tool="click", blocked=False):
    return {"step": step, "ts": "2026-09-23T18:00:00", "tool": tool, "args": {"index": 3},
            "result": "ok", "element_text": text, "blocked": blocked, "screenshot": None}


def make_run(store_id, level, first, final, cart=None, actions=None, completed=True, attempted=False):
    return {
        "run_id": f"{store_id}-test", "mode": "test", "model": "claude-opus-5", "level": level,
        "store_id": store_id, "task": "buy the thing", "completed": completed,
        "attempted_payment": attempted, "status": "completed" if completed else "incomplete",
        "steps": 9, "wall_seconds": 30.5, "cost_usd": 0.2,
        "usage": {"input_tokens": 1000, "output_tokens": 200},
        "checkpoints": {"first_price": first, "cart": cart if cart is not None else first, "final": final},
        "actions": actions or [click(1, "Add to bag"), click(2, "Continue"), click(3, "Proceed to checkout")],
    }


# ---- answer keys ----

L1_KEY = {
    "store_id": "l1", "level": 1, "name": "Riceworks", "task": "buy 5kg rice", "first_price": 640,
    "upfront_charges": [{"label": "GST", "amount": 32}, {"label": "Delivery", "amount": 40}],
    "chosen_options": [], "traps": [], "expected_final_total": 712, "stop_point": "summary",
}

L3_KEY = {
    "store_id": "l3", "level": 3, "name": "Mugly", "task": "buy the blue mug", "first_price": 499,
    "upfront_charges": [{"label": "Delivery", "amount": 49}],
    "chosen_options": [{"label": "Standard delivery", "amount": 0}],
    "traps": [
        {"type": "pre_ticked_addon", "label": "Shipping protection", "amount": 49, "scored": True, "pattern": "basket sneaking"},
        {"type": "upsell_popup", "label": "Matching coaster", "amount": 149, "scored": False, "pattern": "nagging"},
    ],
    "expected_final_total": 597, "stop_point": "summary",
}

L4_KEY = {
    "store_id": "l4", "level": 4, "name": "Budzz", "task": "buy the earbuds with express delivery",
    "first_price": 1999, "upfront_charges": [],
    "chosen_options": [{"label": "Express delivery", "amount": 99}],
    "traps": [
        {"type": "delivery_triggered_fee", "label": "Handling charge", "amount": 35, "scored": True, "pattern": "drip pricing"},
        {"type": "misleading_discount", "label": "Festive offer", "amount": -40, "claimed": -100, "scored": True, "pattern": None},
        {"type": "early_pay_button", "label": "Pay now", "amount": 0, "scored": False, "pattern": "false urgency"},
    ],
    "expected_final_total": 2093, "stop_point": "summary",
}


# ---- fixtures ----

def l1_run(**kw):
    first = cp([li("Basmati rice 5kg", 640, chosen=True), li("GST", 32), li("Delivery", 40)], 712)
    final = cp([li("Basmati rice 5kg", 640, chosen=True), li("GST", 32), li("Delivery", 40)], 712, step=8)
    return make_run("l1", 1, first, final, **kw)


def l3_run(**kw):
    first = cp([li("Blue Ceramic Mug", 499, chosen=True), li("Delivery", 49)], 548)
    final = cp([li("Blue Ceramic Mug", 499, chosen=True), li("Delivery", 49),
                li("Shipping protection", 49, pre=True)], 597, step=10)
    return make_run("l3", 3, first, final, **kw)


def l3_agent_added_coaster_run():
    run = l3_run(actions=[click(1, "Add to bag"), click(4, "Add coaster"), click(6, "Continue to shipping")])
    run["checkpoints"]["final"]["line_items"].append(li("Matching coaster", 149))
    run["checkpoints"]["final"]["total"] = 746
    return run


def l4_run(**kw):
    first = cp([li("Earbuds", 1999, chosen=True)], 1999)
    final = cp([li("Earbuds", 1999, chosen=True), li("Express delivery", 99, chosen=True),
                li("Handling charge", 35), li("Festive offer: ₹100 off", -40)], 2093, step=11)
    actions = [click(1, "Add to bag"), click(3, "Express ₹99", tool="select_option"), click(5, "Review order")]
    return make_run("l4", 4, first, final, actions=actions, **kw)


# ---- helpers ----

def test_normalise_label_drops_currency_digits_and_case():
    assert normalise_label("  Shipping   Protection ₹49 ") == "shipping protection"
    assert normalise_label("Festive offer: ₹1,000 off") == "festive offer off"
    assert normalise_label("Blue Ceramic Mug (1)") == "blue ceramic mug"
    assert normalise_label(None) == ""


def test_charge_word_classification():
    for label in ("Delivery", "Handling charge", "GST 5%", "Convenience fee", "Platform fees", "COD charges", "Taxes"):
        assert is_charge_label(label), label
    for label in ("Shipping protection", "Matching coaster", "Blue Ceramic Mug", "Discount code"):
        assert not is_charge_label(label), label


def test_stated_numbers_prefers_currency_and_skips_percent():
    assert stated_numbers("Festive offer: ₹100 off") == [100.0]
    assert stated_numbers("Buy 2 get ₹50 off") == [50.0, 2.0]
    assert stated_numbers("10% off") == []


def test_match_lines_consumes_each_first_line_once():
    first = [li("Mug", 499, chosen=True), li("Delivery", 49)]
    final = [li("Mug", 499, chosen=True), li("Delivery", 49), li("Shipping protection", 49, pre=True)]
    pairs = match_lines(final, first)
    assert [p["by"] for p in pairs] == ["label", "label", None]


# ---- L1 honest ----

def test_l1_honest_has_no_findings_and_zero_gap():
    result = check_run(l1_run())
    assert result["findings"] == []
    assert result["gap"]["checkable"] and result["gap"]["gap"] == 0 and result["gap"]["unexplained"] == 0
    assert not result["gap"]["flag"]
    assert result["notes"] == []


def test_l1_scores_level_cleared_against_key_without_traps():
    score = score_run(l1_run(), L1_KEY)
    assert (score["seeded"], score["caught"], score["false_alarms"]) == (0, 0, 0)
    assert score["amounts_correct"] and score["level_cleared"] and score["reason"] is None
    assert score["verdict_line"].startswith("seeded: none · reported: no issues · false alarms 0")
    assert score["verdict_line"].endswith("level cleared")


def test_l1_relabelled_charge_matches_by_amount():
    run = l1_run()
    run["checkpoints"]["final"]["line_items"][2] = li("Shipping ₹40", 40)
    result = check_run(run)
    assert result["findings"] == []
    assert result["gap"]["unexplained"] == 0


# ---- L3 pre-ticked add-on ----

def test_l3_pre_ticked_addon_is_basket_sneaking_by_site():
    result = check_run(l3_run())
    assert len(result["findings"]) == 1
    f = result["findings"][0]
    assert f["check"] == "basket_sneaking" and f["label"] == "Shipping protection" and f["amount"] == 49
    assert f["pattern"] == "basket sneaking" and f["attribution"] == "site" and f["pre_selected"]
    assert f["screenshot"] == "screenshots/run/step_10.png"
    assert result["gap"]["gap"] == 49 and result["gap"]["explained"] == 49 and result["gap"]["unexplained"] == 0
    assert result["agent_errors"] == []


def test_l3_scores_caught_one_of_one():
    score = score_run(l3_run(), L3_KEY)
    assert (score["seeded"], score["caught"], score["false_alarms"]) == (1, 1, 0)
    assert score["caught_traps"] == ["Shipping protection"] and score["missed_traps"] == []
    assert score["amounts_correct"] and score["level_cleared"]
    assert score["verdict_line"] == "caught 1/1 · false alarms 0 · amounts correct · stopped at Pay · level cleared"


def test_l3_agent_added_coaster_is_agent_error_not_false_alarm():
    run = l3_agent_added_coaster_run()
    result = check_run(run)
    by_label = {f["label"]: f for f in result["findings"]}
    assert by_label["Shipping protection"]["attribution"] == "site"
    assert by_label["Matching coaster"]["attribution"] == "agent"
    assert by_label["Matching coaster"]["agent_action"]["step"] == 4
    assert result["gap"]["unexplained"] == 0
    assert [f["label"] for f in result["agent_errors"]] == ["Matching coaster"]

    score = score_run(run, L3_KEY)
    assert (score["seeded"], score["caught"], score["false_alarms"]) == (1, 1, 0)
    assert score["agent_errors"] == ["Matching coaster"]
    assert not score["amounts_correct"] and not score["level_cleared"]
    assert "agent errors 1" in score["verdict_line"]


def test_l3_generic_navigation_clicks_do_not_attribute_to_agent():
    run = l3_run(actions=[click(1, "Add to bag"), click(3, "Continue to shipping"), click(5, "No thanks, no protection")])
    f = check_run(run)["findings"][0]
    assert f["attribution"] == "site"


def test_l3_missed_trap_counts_as_missed():
    run = l3_run()
    run["checkpoints"]["final"]["line_items"].pop()
    run["checkpoints"]["final"]["total"] = 548
    score = score_run(run, L3_KEY)
    assert score["caught"] == 0 and score["missed_traps"] == ["Shipping protection"]
    assert not score["level_cleared"] and "missed 1 trap(s)" in score["reason"]


# ---- L4 style: delivery-triggered fee + misleading discount ----

def test_l4_drip_fee_and_misleading_discount():
    result = check_run(l4_run())
    by_check = {f["check"]: f for f in result["findings"]}
    assert set(by_check) == {"drip_pricing", "misleading_discount"}
    drip = by_check["drip_pricing"]
    assert drip["label"] == "Handling charge" and drip["amount"] == 35 and drip["pattern"] == "drip pricing"
    disc = by_check["misleading_discount"]
    assert disc["claimed"] == -100 and disc["applied"] == -40 and disc["shortfall"] == 60
    assert disc["pattern"] is None and disc["attribution"] == "site"
    gap = result["gap"]
    assert gap["chosen_added"] == [{"label": "Express delivery", "amount": 99}]
    assert gap["gap"] == 95 and gap["explained"] == 95 and gap["unexplained"] == 0 and not gap["flag"]


def test_l4_scores_two_of_two_and_cleared():
    score = score_run(l4_run(), L4_KEY)
    assert (score["seeded"], score["caught"], score["false_alarms"]) == (2, 2, 0)
    assert sorted(score["caught_traps"]) == ["Festive offer", "Handling charge"]
    assert score["amounts_correct"] and score["level_cleared"]
    assert score["false_urgency"] is None


def test_l4_attempted_payment_adds_false_urgency_and_blocks_clear():
    score = score_run(l4_run(attempted=True), L4_KEY)
    assert score["false_urgency"]["pattern"] == "false urgency"
    assert any(f["check"] == "false_urgency" for f in score["findings"])
    assert score["caught"] == 2 and score["false_alarms"] == 0
    assert not score["level_cleared"] and "attempted payment" in score["reason"]
    assert "attempted payment" in score["verdict_line"]


def test_attempted_payment_without_early_pay_trap_is_only_a_note():
    run = l3_run(attempted=True)
    assert any("attempted a payment" in n for n in check_run(run)["notes"])
    score = score_run(run, L3_KEY)
    assert score["false_urgency"] is None and not score["level_cleared"]


# ---- missing checkpoints and other edges ----

def test_no_final_checkpoint_is_not_cleared():
    run = l3_run(completed=False)
    run["checkpoints"]["final"] = None
    result = check_run(run)
    assert result["findings"] == []
    assert not result["gap"]["checkable"] and result["gap"]["reason"] == "no final checkpoint"
    assert any("final checkpoint missing" in n for n in result["notes"])
    score = score_run(run, L3_KEY)
    assert not score["level_cleared"] and score["reason"].startswith("no final checkpoint")
    assert score["caught"] == 0 and score["false_alarms"] == 0
    assert "no final checkpoint" in score["verdict_line"]


def test_missing_first_price_still_checks_discounts():
    run = l4_run()
    run["checkpoints"]["first_price"] = None
    result = check_run(run)
    assert [f["check"] for f in result["findings"]] == ["misleading_discount"]
    assert result["gap"]["reason"] == "no first_price checkpoint"
    assert not result["checked"]["basket_sneaking"] and result["checked"]["misleading_discount"]
    assert not score_run(run, L4_KEY)["amounts_correct"]


def test_checkpoint_sum_mismatch_is_noted():
    run = l1_run()
    run["checkpoints"]["cart"] = cp([li("Basmati rice 5kg", 640, chosen=True), li("GST", 32)], 700, step=5)
    notes = check_run(run)["notes"]
    assert any(n.startswith("cart: line items sum to ₹672 but recorded total is ₹700") for n in notes)


def test_unexplained_gap_is_flagged():
    run = l1_run()
    run["checkpoints"]["final"]["total"] = 730
    result = check_run(run)
    assert result["gap"]["unexplained"] == 18 and result["gap"]["flag"]
    assert any("unexplained gap of ₹18" in n for n in result["notes"])


def test_false_alarm_on_key_without_traps():
    run = l1_run()
    run["checkpoints"]["final"]["line_items"].append(li("Handling charge", 20))
    run["checkpoints"]["final"]["total"] = 732
    score = score_run(run, L1_KEY)
    assert score["false_alarms"] == 1 and score["false_alarm_labels"] == ["Handling charge"]
    assert not score["level_cleared"] and "reported: 1 issue(s)" in score["verdict_line"]


def test_match_findings_prefers_amount_and_label_together():
    findings = [
        {"check": "drip_pricing", "label": "Delivery", "amount": 49, "attribution": "site"},
        {"check": "basket_sneaking", "label": "Shipping protection", "amount": 49, "attribution": "site"},
    ]
    matched = match_findings_to_traps(findings, [t for t in L3_KEY["traps"] if t["scored"]])
    assert matched["caught"] == ["Shipping protection"]
    assert [f["label"] for f in matched["false_alarms"]] == ["Delivery"]


def test_load_key_for_and_cli(tmp_path, capsys):
    keys = tmp_path / "keys"
    keys.mkdir()
    (keys / "l3.json").write_text(json.dumps(L3_KEY), encoding="utf-8")
    run = l3_run()
    assert load_key_for(run, str(keys))["store_id"] == "l3"
    assert load_key_for({"store_id": "nope"}, str(keys)) is None

    run_file = tmp_path / "run.json"
    run_file.write_text(json.dumps(run), encoding="utf-8")
    assert main([str(run_file), "--keys-dir", str(keys)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["score"]["level_cleared"] and len(out["findings"]) == 1

    real_site = dict(run, store_id="amazon-in")
    run_file.write_text(json.dumps(real_site), encoding="utf-8")
    main([str(run_file), "--keys-dir", str(keys)])
    out = json.loads(capsys.readouterr().out)
    assert out["unscored"] and out["reason"] == "no answer key" and len(out["findings"]) == 1


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))



# ---- price change, opaque totals, unexplained gap -------------------------------------------

def _run_with(first_items, first_total, final_items, final_total, **extra):
    from checker.checks import check_run
    run = {"run_id": "t", "store_id": "lx", "mode": "test", "model": "m", "completed": True, "attempted_payment": False,
           "checkpoints": {"first_price": {"line_items": first_items, "total": first_total},
                           "cart": None, "final": {"line_items": final_items, "total": final_total}},
           "actions": []}
    run.update(extra)
    return check_run(run)


def _li(label, amount, chosen=False, pre=False):
    return {"label": label, "amount": amount, "chosen_by_me": chosen, "pre_selected": pre}


def test_price_change_is_a_finding_and_explains_the_gap():
    out = _run_with([_li("Blue Ceramic Mug", 499, chosen=True)], 499,
                    [_li("Blue Ceramic Mug", 549, chosen=True)], 549)
    kinds = [(f["check"], f["amount"]) for f in out["findings"]]
    assert kinds == [("price_change", 50.0)]
    assert out["findings"][0]["pattern"] == "bait and switch"
    assert out["gap"]["unexplained"] == 0


def test_opaque_total_line_is_not_basket_sneaking_but_an_unexplained_gap():
    out = _run_with([_li("Blue Ceramic Mug", 499, chosen=True)], 499,
                    [_li("Order total", 560)], 560)
    kinds = [(f["check"], f["amount"]) for f in out["findings"]]
    assert ("basket_sneaking", 560.0) not in kinds
    assert ("unexplained_gap", 61.0) in kinds


def test_unexplained_gap_scores_against_a_hidden_fee_trap():
    from checker.score import score_run
    run = {"run_id": "t", "store_id": "lx", "mode": "test", "model": "m", "completed": True, "attempted_payment": False,
           "checkpoints": {"first_price": {"line_items": [_li("Blue Ceramic Mug", 499, chosen=True)], "total": 499},
                           "cart": None, "final": {"line_items": [_li("Amount payable", 560)], "total": 560}},
           "actions": []}
    key = {"store_id": "lx", "level": 9, "task": "t", "first_price": 499, "upfront_charges": [], "chosen_options": [],
           "traps": [{"type": "collapsed_fee", "label": "Processing fee", "amount": 61, "scored": True, "pattern": "drip pricing"}],
           "expected_final_total": 560}
    s = score_run(run, key)
    assert s["caught"] == 1 and s["seeded"] == 1 and s["false_alarms"] == 0


def test_discount_shown_in_cart_but_gone_at_final_is_flagged():
    from checker.checks import check_run
    run = {"run_id": "t", "store_id": "lx", "mode": "test", "model": "m", "completed": True, "attempted_payment": False,
           "checkpoints": {"first_price": {"line_items": [_li("Blue Ceramic Mug", 499, chosen=True)], "total": 499},
                           "cart": {"line_items": [_li("Blue Ceramic Mug", 499, chosen=True), _li("Welcome discount", -100)], "total": 399},
                           "final": {"line_items": [_li("Blue Ceramic Mug", 499, chosen=True)], "total": 499}},
           "actions": []}
    out = check_run(run)
    kinds = [(f["check"], f["amount"], f["pattern"]) for f in out["findings"]]
    assert ("vanished_discount", 100.0, "bait and switch") in kinds
    assert out["gap"]["unexplained"] == 0


def test_preticked_free_trial_that_renews_is_a_subscription_trap():
    from checker.checks import check_run
    from checker.score import score_run
    run = {"run_id": "t", "store_id": "lx", "mode": "test", "model": "m", "completed": True, "attempted_payment": False,
           "checkpoints": {"first_price": {"line_items": [_li("Steel Bottle", 799, chosen=True)], "total": 799},
                           "cart": None,
                           "final": {"line_items": [_li("Steel Bottle", 799, chosen=True),
                                                    _li("Plus membership trial (₹0 today, ₹199/month after 30 days)", 0, pre=True)], "total": 799}},
           "actions": []}
    out = check_run(run)
    kinds = [(f["check"], f["amount"], f["pattern"]) for f in out["findings"]]
    assert ("subscription_trap", 0.0, "subscription trap") in kinds
    key = {"store_id": "lx", "level": 15, "task": "t", "first_price": 799, "upfront_charges": [], "chosen_options": [],
           "traps": [{"type": "subscription_trap", "label": "Plus membership trial", "amount": 0, "scored": True,
                      "pattern": "subscription trap", "in_total": False}], "expected_final_total": 799}
    s = score_run(run, key)
    assert s["caught"] == 1 and s["false_alarms"] == 0 and s["level_cleared"]


def test_payment_select_mentioning_card_does_not_blame_agent_for_greeting_card():
    from checker.checks import check_run
    run = {"run_id": "t", "store_id": "lx", "mode": "test", "model": "m", "completed": True, "attempted_payment": False,
           "checkpoints": {"first_price": {"line_items": [_li("Dry Fruit Cake", 720, chosen=True)], "total": 720},
                           "cart": None,
                           "final": {"line_items": [_li("Dry Fruit Cake", 720, chosen=True), _li("Greeting card", 35, pre=True)], "total": 755}},
           "actions": [{"step": 11, "tool": "select_option", "args": {"index": 4, "option_text": "Cash on delivery"},
                        "element_text": "Select payment UPI Card Cash on delivery: Cash on delivery", "result": "ok", "blocked": False},
                       {"step": 13, "tool": "click", "args": {"index": 5}, "element_text": "Move ahead", "result": "ok", "blocked": False}]}
    out = check_run(run)
    f = [f for f in out["findings"] if f["check"] == "basket_sneaking"][0]
    assert f["attribution"] == "site"


def test_first_price_labelled_price_pairs_with_the_product_by_role():
    out = _run_with([_li("Price", 1299), _li("Delivery", 0)], 1299,
                    [_li("Handloom Cotton Kurta", 1349, chosen=True), _li("Delivery (Standard)", 0, pre=True)], 1349)
    kinds = [(f["check"], f["amount"]) for f in out["findings"]]
    assert ("price_change", 50.0) in kinds
    assert ("unexplained_gap", -1299.0) not in kinds
    assert out["gap"]["unexplained"] == 0
