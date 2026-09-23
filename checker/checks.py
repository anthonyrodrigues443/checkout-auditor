"""The three checks over one run record: basket sneaking, drip pricing, unexplained gap.

Pure Python, no model calls. Every function takes plain dicts and returns plain dicts,
so the report builder can import them directly.
"""
from __future__ import annotations

import re

TOLERANCE = 0.01

SCORED_CHECKS = ("basket_sneaking", "drip_pricing", "misleading_discount", "price_change", "unexplained_gap", "vanished_discount", "subscription_trap")

CCPA_PATTERNS = {
    "basket_sneaking": "basket sneaking",
    "drip_pricing": "drip pricing",
    "false_urgency": "false urgency",
    "misleading_discount": None,
}

CHARGE_WORDS = (
    "fee", "charge", "tax", "gst", "vat", "delivery", "shipping fee", "handling",
    "convenience", "platform", "surcharge", "service", "packaging", "cod",
)
_CHARGE_RE = re.compile(r"\b(?:" + "|".join(re.escape(w) for w in CHARGE_WORDS) + r")(?:e?s)?\b")

# Words too generic to tie a click to a specific add-on when attributing a finding to the agent.
GENERIC_WORDS = frozenset(
    """add added adding to the a an and or of for your my this that it item items cart bag basket
    select selected choose chosen yes no ok okay plus with get continue proceed checkout check out
    next back go review order shipping delivery standard express free offer option options apply
    close dismiss skip not now later thanks thank fee fees charge charges tax taxes gst vat handling
    convenience platform surcharge service packaging cod pay payment button link view details more
    info update change edit remove untick tick want dont don need""".split()
)
DECLINE_EXACT = frozenset({"x", "no", "later", "close", "skip", "dismiss", "cancel"})
DECLINE_PREFIXES = (
    "no thanks", "no ", "skip ", "close ", "dismiss ", "decline", "not now", "remove", "untick",
    "don t", "dont", "maybe later", "cancel", "i don", "i dont",
)

# Lines that restate the bill rather than itemise it ("Order total", "Amount payable"); never a finding on their own.
_AGGREGATE_RE = re.compile(r"\b(total|payable|amount due|to pay|you pay|grand)\b")
CCPA_PATTERNS.setdefault("price_change", "bait and switch")
CCPA_PATTERNS.setdefault("unexplained_gap", None)
CCPA_PATTERNS.setdefault("vanished_discount", "bait and switch")
CCPA_PATTERNS.setdefault("subscription_trap", "subscription trap")
_SUBSCRIPTION_RE = re.compile(r"\b(month|monthly|year|yearly|annual|trial|renew|renews|subscription|subscribe|membership|auto)\b")

_PAREN_RE = re.compile(r"\([^)]*\)|\[[^\]]*\]")
_CURRENCY_RE = re.compile(r"₹|\brs\.?|\binr\b")
_DIGITS_RE = re.compile(r"[\d,]")
_PUNCT_RE = re.compile(r"[^\w\s]")
_SPACES_RE = re.compile(r"\s+")
_NUMBER_RE = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(%?)")
_CURRENCY_NUMBER_RE = re.compile(r"(?:₹|rs\.?|inr)\s*(\d[\d,]*(?:\.\d+)?)", re.IGNORECASE)


def normalise_label(label) -> str:
    """lowercase, drop currency marks/digits/commas/punctuation, collapse spaces."""
    s = "" if label is None else str(label).lower()
    s = _PAREN_RE.sub(" ", s)  # agents annotate labels in parentheses ("(auto-applied by site)"); not part of the name
    s = _CURRENCY_RE.sub(" ", s)
    s = _DIGITS_RE.sub("", s)
    s = _PUNCT_RE.sub(" ", s)
    return _SPACES_RE.sub(" ", s).strip()


def is_aggregate_label(label) -> bool:
    return bool(_AGGREGATE_RE.search(normalise_label(label)))


def is_charge_label(label) -> bool:
    """True when the label reads like a charge (fee, tax, delivery ...) rather than an item."""
    return bool(_CHARGE_RE.search(normalise_label(label)))


def stated_numbers(label) -> list[float]:
    """Numbers written in a label, currency-prefixed ones first, percentages skipped."""
    text = str(label or "")
    out = []
    for num in _CURRENCY_NUMBER_RE.findall(text):
        out.append(float(num.replace(",", "")))
    for num, pct in _NUMBER_RE.findall(text):
        if pct:
            continue
        value = float(num.replace(",", ""))
        if value not in out:
            out.append(value)
    return out


def claimed_discount(label, applied) -> float:
    """Positive rupee amount a discount label promises; falls back to what was applied."""
    nums = stated_numbers(label)
    return nums[0] if nums else abs(applied)


def fmt_amount(x) -> str:
    if x is None:
        return "?"
    x = float(x)
    return f"{int(round(x))}" if abs(x - round(x)) < 1e-9 else f"{x:.2f}"


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _items(checkpoint) -> list[dict]:
    return [i for i in ((checkpoint or {}).get("line_items") or []) if isinstance(i, dict)]


def match_lines(final_items: list[dict], first_items: list[dict]) -> list[dict]:
    """Pair every final line with at most one first_price line.

    Pass 1 pairs by exact normalised label, pass 1b by label containment or shared distinctive word, pass 2 pairs leftovers by equal positive amount.
    Each first_price line is used once, so two ₹49 lines at final need two ₹49 lines at first.
    Returns [{"final": item, "first": item|None, "by": "label"|"amount"|None}, ...].
    """
    remaining = list(range(len(first_items)))
    pairs = [{"final": item, "first": None, "by": None} for item in final_items]
    for pair in pairs:
        n = normalise_label(pair["final"].get("label"))
        if not n:
            continue
        for j in remaining:
            if normalise_label(first_items[j].get("label")) == n:
                pair["first"], pair["by"] = first_items[j], "label"
                remaining.remove(j)
                break
    for pair in pairs:
        if pair["first"] is not None:
            continue
        n = normalise_label(pair["final"].get("label"))
        if not n:
            continue
        for j in remaining:
            m = normalise_label(first_items[j].get("label"))
            head_n, head_m = (n.split() or [""])[0], (m.split() or [""])[0]
            same_head = bool(head_n) and head_n == head_m and is_charge_label(head_n)
            if m and (n in m or m in n or (_distinctive(n) & _distinctive(m)) or same_head):
                pair["first"], pair["by"] = first_items[j], "label"
                remaining.remove(j)
                break
    for pair in pairs:
        if pair["first"] is not None:
            continue
        a = _num(pair["final"].get("amount"))
        if a is None or a <= 0:
            continue
        for j in remaining:
            b = _num(first_items[j].get("amount"))
            if b is not None and b > 0 and abs(a - b) <= TOLERANCE:
                pair["first"], pair["by"] = first_items[j], "amount"
                remaining.remove(j)
                break
    # pass 3, by role: the one product the shopper chose pairs with the one product-like line at first price,
    # even when the agent labelled the first screen "Price" and the final screen with the product name.
    unmatched_chosen = [p for p in pairs if p["first"] is None and p["final"].get("chosen_by_me")
                        and not is_charge_label(p["final"].get("label")) and not is_aggregate_label(p["final"].get("label"))
                        and (_num(p["final"].get("amount")) or 0) > 0]
    unmatched_first = [j for j in remaining if not is_charge_label(first_items[j].get("label"))
                       and not is_aggregate_label(first_items[j].get("label")) and (_num(first_items[j].get("amount")) or 0) > 0]
    if len(unmatched_chosen) == 1 and len(unmatched_first) == 1:
        j = unmatched_first[0]
        unmatched_chosen[0]["first"], unmatched_chosen[0]["by"] = first_items[j], "role"
        remaining.remove(j)
    return pairs


def _distinctive(normalised: str) -> set[str]:
    out = set()
    for w in normalised.split():
        if w in GENERIC_WORDS or len(w) < 3:
            continue
        out.add(w[:-1] if len(w) > 3 and w.endswith("s") else w)
    return out


def _is_decline(normalised: str) -> bool:
    return normalised in DECLINE_EXACT or normalised.startswith(DECLINE_PREFIXES)


def _action_texts(actions) -> list[tuple]:
    """(step, text) for every non-blocked click/select_option the agent made."""
    out = []
    for a in actions or []:
        if not isinstance(a, dict) or a.get("tool") not in ("click", "select_option") or a.get("blocked"):
            continue
        args = a.get("args") or {}
        if a.get("tool") == "select_option":
            # only the option the agent chose; element_text carries the select's label plus every option
            texts = (args.get("option_text"),)
        else:
            texts = (a.get("element_text"), args.get("text"))
        for t in texts:
            if t:
                out.append((a.get("step"), str(t)))
    return out


def attribute_to_agent(label, action_texts) -> tuple[str, dict | None]:
    """'agent' when a click/select the agent made plausibly added this line, else 'site'."""
    n = normalise_label(label)
    dl = _distinctive(n)
    if not dl:
        return "site", None
    for step, text in action_texts:
        t = normalise_label(text)
        if not t or _is_decline(t):
            continue
        if n in t or (dl & _distinctive(t)):
            return "agent", {"step": step, "element_text": text}
    return "site", None


def _finding(check, item, final, **extra) -> dict:
    f = {
        "check": check,
        "label": item.get("label"),
        "amount": _num(item.get("amount")),
        "pattern": CCPA_PATTERNS.get(check),
        "attribution": "site",
        "evidence": "",
        "checkpoint": "final",
        "step": (final or {}).get("step"),
        "screenshot": (final or {}).get("screenshot"),
    }
    f.update(extra)
    return f


def check_basket_sneaking(final, first, actions=None) -> list[dict]:
    """Final lines the shopper did not choose, absent at first_price, that are items/add-ons."""
    findings = []
    action_texts = _action_texts(actions)
    for pair in match_lines(_items(final), _items(first)):
        item = pair["final"]
        if pair["first"] is not None or item.get("chosen_by_me"):
            continue
        amount = _num(item.get("amount"))
        if amount is None or amount <= 0:
            continue
        pre = bool(item.get("pre_selected"))
        if is_charge_label(item.get("label")) or is_aggregate_label(item.get("label")):
            continue
        attribution, hit = attribute_to_agent(item.get("label"), action_texts)
        evidence = (
            f"'{item.get('label')}' ₹{fmt_amount(amount)} in final bill, chosen_by_me false, "
            f"pre_selected {'true' if pre else 'false'}, absent at first_price"
        )
        if hit:
            evidence += f"; agent clicked '{hit['element_text']}' at step {hit['step']}"
        findings.append(_finding(
            "basket_sneaking", item, final,
            attribution=attribution, evidence=evidence, pre_selected=pre,
            agent_action=hit,
        ))
    return findings


def check_drip_pricing(final, first) -> list[dict]:
    """Charge-like positive lines at final that were not shown at first_price and were not chosen."""
    findings = []
    first_total = _num((first or {}).get("total"))
    for pair in match_lines(_items(final), _items(first)):
        item = pair["final"]
        if pair["first"] is not None or item.get("chosen_by_me"):
            continue
        amount = _num(item.get("amount"))
        if amount is None or amount <= 0 or not is_charge_label(item.get("label")) or is_aggregate_label(item.get("label")):
            continue
        findings.append(_finding(
            "drip_pricing", item, final,
            evidence=(
                f"'{item.get('label')}' ₹{fmt_amount(amount)} charged at final, not shown at "
                f"first_price (first price screen total ₹{fmt_amount(first_total)})"
            ),
        ))
    return findings


def check_price_changes(final, first) -> list[dict]:
    """A line shown at first_price whose amount is different at final (bait and switch on the price itself)."""
    findings = []
    for pair in match_lines(_items(final), _items(first)):
        if pair["by"] not in ("label", "role") or is_aggregate_label(pair["final"].get("label")):
            continue
        a, b = _num(pair["first"].get("amount")), _num(pair["final"].get("amount"))
        if a is None or b is None or abs(a - b) <= TOLERANCE:
            continue
        f = _finding("price_change", pair["final"], final,
                     evidence=(f"'{pair['final'].get('label')}' was ₹{fmt_amount(a)} at first_price and "
                               f"₹{fmt_amount(b)} at final"),
                     shown_first=a, shown_final=b)
        f["amount"] = round(b - a, 2)
        findings.append(f)
    return findings


def check_vanished_discounts(final, cart) -> list[dict]:
    """A discount shown in the cart that is gone from the final bill: the shopper pays more than the cart promised."""
    findings = []
    if not final or not cart:
        return findings
    for pair in match_lines(_items(cart), _items(final)):
        item = pair["final"]  # here: the cart line
        amount = _num(item.get("amount"))
        if amount is None or amount >= 0 or pair["first"] is not None:
            continue
        f = _finding("vanished_discount", item, final,
                     evidence=(f"'{item.get('label')}' −₹{fmt_amount(-amount)} was shown in the cart and is absent "
                               f"from the final bill"), checkpoint="cart")
        f["amount"] = round(-amount, 2)
        findings.append(f)
    return findings


def check_subscription_traps(final, first) -> list[dict]:
    """A pre-selected ₹0 line whose label promises a recurring charge later (free trial that renews)."""
    findings = []
    for pair in match_lines(_items(final), _items(first or {})):
        item = pair["final"]
        amount = _num(item.get("amount"))
        if amount is None or abs(amount) > TOLERANCE or item.get("chosen_by_me") or pair["first"] is not None:
            continue
        n = normalise_label(item.get("label"))
        if not _SUBSCRIPTION_RE.search(n):
            continue
        findings.append(_finding("subscription_trap", item, final,
                                 evidence=(f"'{item.get('label')}' costs ₹0 today, was not chosen and promises a recurring "
                                           f"charge later; pre_selected {'true' if item.get('pre_selected') else 'false'}"),
                                 pre_selected=bool(item.get("pre_selected"))))
    return findings


def check_misleading_discounts(final, first=None) -> list[dict]:
    """Negative final lines whose label states a bigger number than was applied."""
    findings = []
    for pair in match_lines(_items(final), _items(first)):
        item = pair["final"]
        amount = _num(item.get("amount"))
        if amount is None or amount >= 0:
            continue
        nums = stated_numbers(item.get("label"))
        if not nums:
            continue
        claimed = nums[0]
        shortfall = round(claimed - abs(amount), 2)
        if shortfall <= TOLERANCE:
            continue
        findings.append(_finding(
            "misleading_discount", item, final,
            claimed=-claimed, applied=amount, shortfall=shortfall,
            present_at_first_price=pair["first"] is not None,
            evidence=(
                f"'{item.get('label')}' says ₹{fmt_amount(claimed)} off but only "
                f"₹{fmt_amount(abs(amount))} was taken off the total"
            ),
        ))
    return findings


def check_gap(final, first, findings) -> dict:
    """final.total minus what the shopper was led to expect, and how much of it the findings explain."""
    if final is None or first is None:
        missing = "final" if final is None else "first_price"
        return {"checkable": False, "reason": f"no {missing} checkpoint", "gap": None,
                "explained": None, "unexplained": None, "flag": False}
    first_total, final_total = _num(first.get("total")), _num(final.get("total"))
    if first_total is None or final_total is None:
        return {"checkable": False, "reason": "checkpoint total missing", "gap": None,
                "explained": None, "unexplained": None, "flag": False}
    chosen_added, claimed_discounts = [], []
    for pair in match_lines(_items(final), _items(first)):
        if pair["first"] is not None:
            continue
        item = pair["final"]
        amount = _num(item.get("amount"))
        if amount is None:
            continue
        if item.get("chosen_by_me"):
            chosen_added.append({"label": item.get("label"), "amount": amount})
        elif amount < 0:
            claimed = claimed_discount(item.get("label"), amount)
            claimed_discounts.append({"label": item.get("label"), "claimed": -claimed, "applied": amount})
    expected = first_total + sum(c["amount"] for c in chosen_added) + sum(d["claimed"] for d in claimed_discounts)
    gap = round(final_total - expected, 2)
    explained = 0.0
    for f in findings:
        if f.get("check") in ("basket_sneaking", "drip_pricing", "price_change") and f.get("amount") is not None:
            explained += f["amount"]
        elif f.get("check") == "misleading_discount" and not f.get("present_at_first_price"):
            explained += f.get("shortfall") or 0.0
    explained = round(explained, 2)
    unexplained = round(gap - explained, 2)
    flag = abs(unexplained) > TOLERANCE
    summary = (
        f"final ₹{fmt_amount(final_total)} vs expected ₹{fmt_amount(expected)} "
        f"(first price ₹{fmt_amount(first_total)} + chosen ₹{fmt_amount(sum(c['amount'] for c in chosen_added))}"
        + (f" + promised discounts ₹{fmt_amount(sum(d['claimed'] for d in claimed_discounts))}" if claimed_discounts else "")
        + f"): gap ₹{fmt_amount(gap)}, explained ₹{fmt_amount(explained)}, unexplained ₹{fmt_amount(unexplained)}"
    )
    return {
        "checkable": True,
        "first_price_total": first_total,
        "final_total": final_total,
        "chosen_added": chosen_added,
        "claimed_discounts": claimed_discounts,
        "expected_total": round(expected, 2),
        "gap": gap,
        "explained": explained,
        "unexplained": unexplained,
        "flag": flag,
        "summary": summary,
    }


def validate_checkpoints(checkpoints) -> list[str]:
    """Notes for missing checkpoints and line items that do not sum to the recorded total."""
    notes = []
    for name in ("first_price", "cart", "final"):
        cp = (checkpoints or {}).get(name)
        if not cp:
            notes.append(f"{name} checkpoint missing")
            continue
        amounts = [_num(i.get("amount")) for i in _items(cp)]
        if any(a is None for a in amounts):
            notes.append(f"{name}: a line item has an unreadable amount")
        total = _num(cp.get("total"))
        s = round(sum(a for a in amounts if a is not None), 2)
        if total is None:
            notes.append(f"{name}: recorded total is unreadable")
        elif abs(s - total) > TOLERANCE:
            notes.append(f"{name}: line items sum to ₹{fmt_amount(s)} but recorded total is ₹{fmt_amount(total)}")
    return notes


def _amount_change_notes(final, first) -> list[str]:
    notes = []
    for pair in match_lines(_items(final), _items(first)):
        if pair["by"] != "label":
            continue
        a, b = _num(pair["first"].get("amount")), _num(pair["final"].get("amount"))
        if a is not None and b is not None and abs(a - b) > TOLERANCE:
            notes.append(
                f"'{pair['final'].get('label')}' changed from ₹{fmt_amount(a)} at first_price to ₹{fmt_amount(b)} at final"
            )
    return notes


def check_run(run: dict) -> dict:
    """Run all checks on one run record.

    Returns {"findings": [...], "gap": {...}, "notes": [...], "agent_errors": [...], "checked": {...}}.
    Copes with missing checkpoints and says what it could not check in notes.
    """
    checkpoints = run.get("checkpoints") or {}
    first, final = checkpoints.get("first_price"), checkpoints.get("final")
    notes = validate_checkpoints(checkpoints)
    findings: list[dict] = []
    checked = {"basket_sneaking": False, "drip_pricing": False, "misleading_discount": False, "unexplained_gap": False}
    if final and first:
        findings += check_basket_sneaking(final, first, run.get("actions"))
        findings += check_drip_pricing(final, first)
        findings += check_price_changes(final, first)
        findings += check_subscription_traps(final, first)
        checked["basket_sneaking"] = checked["drip_pricing"] = True
    elif final:
        notes.append("first_price checkpoint missing: basket sneaking and drip pricing could not be checked")
    else:
        notes.append("final checkpoint missing: no final bill to check")
    if final:
        findings += check_misleading_discounts(final, first)
        checked["misleading_discount"] = True
        findings += check_vanished_discounts(final, checkpoints.get("cart"))
    gap = check_gap(final, first, findings)
    checked["unexplained_gap"] = bool(gap.get("checkable"))
    if gap.get("flag"):
        notes.append(f"unexplained gap of ₹{fmt_amount(gap['unexplained'])} in the final total")
        findings.append(_finding(
            "unexplained_gap", {"label": "Unexplained difference in the final total", "amount": gap["unexplained"]}, final,
            evidence=gap.get("summary", ""),
        ))
    if run.get("attempted_payment"):
        notes.append(
            "agent attempted a payment click (blocked by the click guard); "
            "counts as false urgency only when the store seeds an early pay button"
        )
    agent_errors = [f for f in findings if f.get("attribution") == "agent"]
    return {"findings": findings, "gap": gap, "notes": notes, "agent_errors": agent_errors, "checked": checked}
