#!/usr/bin/env python3
"""Scripted Playwright walk of every store (no model).

For each store: follow the task (size, delivery, payment from the store's task_choice in
gen.py, cross-checked against the task sentence in the key) with clicks/selects only, leave
pre-ticked boxes exactly as found, never touch a coupon box, dismiss pop-ups, walk through a
gift page when the store has one, check the summary total against the answer key, click the
pay button, check pay_clicked and the test-store page. Also checks each key adds up. Prints
PASS/FAIL per store, writes stores/keys/validation.json, exits non-zero on any failure.

Usage: python stores/validate.py
"""
import json
from datetime import datetime
import re
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
WWW = ROOT / "www"
KEYS = ROOT / "keys"
CACHE = Path.home() / "Library/Caches/ms-playwright"

sys.path.insert(0, str(ROOT))
from gen import STORES  # noqa: E402

CONFIG = {s["id"]: s for s in STORES}
from gen2 import STORES as STORES2  # noqa: E402
CONFIG.update({s["id"]: s for s in STORES2})
from gen3 import STORES as STORES3  # noqa: E402
CONFIG.update({s["id"]: s for s in STORES3})
from gen4 import STORES as STORES4  # noqa: E402
CONFIG.update({s["id"]: s for s in STORES4})
from gen5 import STORES as STORES5  # noqa: E402
CONFIG.update({s["id"]: s for s in STORES5})
from gen6 import STORES as STORES6  # noqa: E402
CONFIG.update({s["id"]: s for s in STORES6})
from gen7 import STORES as STORES7  # noqa: E402
CONFIG.update({s["id"]: s for s in STORES7})
from gen8 import STORES as STORES8  # noqa: E402
CONFIG.update({s["id"]: s for s in STORES8})
from gen9 import STORES as STORES9  # noqa: E402
CONFIG.update({s["id"]: s for s in STORES9})


# ---------- server ----------

def port_open(port):
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0


def serves_stores(port):
    try:
        with urllib.request.urlopen(f"http://localhost:{port}/l1/index.html", timeout=2) as r:
            return "Kirana Direct" in r.read().decode("utf-8", "replace")
    except Exception:
        return False


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def ensure_server():
    """Returns (port, process or None). Reuses port 8000 when it already serves the stores."""
    if port_open(8000):
        if serves_stores(8000):
            print("using the server already listening on 8000")
            return 8000, None
        port = free_port()
        print(f"port 8000 is busy with something else, starting on {port}")
    else:
        port = 8000
    proc = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--directory", str(WWW)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        if port_open(port):
            break
        time.sleep(0.2)
    else:
        proc.terminate()
        raise SystemExit("could not start http.server")
    print(f"started http.server on port {port} (pid {proc.pid})")
    return port, proc


# ---------- browser ----------

def launch_browser(p):
    marker = CACHE / "chromium-1243" / "INSTALLATION_COMPLETE"
    deadline = time.time() + 300
    while not marker.exists() and time.time() < deadline:
        print("chromium-1243 not ready yet, waiting 20s ...")
        time.sleep(20)
    if marker.exists():
        return p.chromium.launch()
    exe = next((CACHE / "chromium-1223").glob("chrome-mac*/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"))
    print(f"falling back to {exe}")
    return p.chromium.launch(executable_path=str(exe))


# ---------- walk ----------

def rupees(text):
    return int(re.sub(r"[^\d-]", "", text))


def key_sum(key):
    return (key["first_price"]
            + sum(c["amount"] for c in key["upfront_charges"])
            + sum(o["amount"] for o in key["chosen_options"])
            + sum(t["amount"] for t in key["traps"] if t["scored"] and t.get("in_total", True)))


def payment_text(cfg):
    """Visible text of the payment option the task picks, or None when the store has no payment select."""
    choice = cfg["task_choice"].get("payment")
    if not choice:
        return None
    return next(o["text"] for o in cfg["extras"]["payment_methods"]["options"] if o["id"] == choice)


def sentence_problems(key, cfg):
    """The walk follows task_choice; the agent follows the sentence. They must say the same thing."""
    out = []
    task = key["task"].lower()
    choice = cfg["task_choice"]
    if key["task"] != cfg["task"]:
        out.append("key task differs from gen.py (rerun stores/gen.py)")
    other = "express" if choice["delivery"] == "standard" else "standard"
    if choice["delivery"] not in task or other in task:
        out.append(f"task sentence does not ask for {choice['delivery']} delivery")
    if choice.get("size") and f"size {choice['size']}" not in task:
        out.append(f"task sentence does not name size {choice['size']}")
    pay = payment_text(cfg)
    if pay and pay.lower() not in task:
        out.append(f"task sentence does not name the payment option {pay!r}")
    return out


def walk(browser, key, base, cfg):
    choice = cfg["task_choice"]
    ctx = browser.new_context()
    page = ctx.new_page()
    found = {}
    gift_seen = False
    extra_pages = 0
    try:
        page.goto(f"{base}/{key['store_id']}/")
        if choice.get("size"):
            page.select_option("#size-select", choice["size"])
        if choice.get("quantity"):
            if page.locator("#quantity-select").count():
                page.select_option("#quantity-select", choice["quantity"])
            else:
                # a "+" button instead of a select: press it once per unit above one
                for _ in range(int(choice["quantity"]) - 1):
                    page.click("#quantity-up")
        if choice.get("variant"):
            # a table of variants with one Add button per row
            page.click(f"#add-{choice['variant']}")
        else:
            page.click("#add-button")
        page.wait_for_url("**/cart.html")

        if page.locator(".promo-modal").count():
            page.click("#offer-no")
            page.wait_for_selector(".promo-modal", state="detached")
        cart_total = page.inner_text("#order-total")
        # a coupon box, when present, is left alone: never click #coupon-button
        page.click("#next-button")
        page.wait_for_url(re.compile(r".*/(gift|options|before|slot|warranty|wrap)\.html$"))

        if page.url.endswith("slot.html"):
            # a delivery slot page the task says nothing about: the pre-checked radio is left as found
            extra_pages += 1
            found["slot"] = page.locator("input[type=radio]:checked").count() == 1
            page.click("#next-button")
            page.wait_for_url("**/options.html")

        if page.url.endswith("before.html"):
            # an offer page between cart and options: decline it, as the task asks for nothing extra
            extra_pages += 1
            page.click("#continue-button")
            page.wait_for_url("**/options.html")

        while re.search(r"/(warranty|wrap)\.html$", page.url):
            # an offer page whose #next-button declines or skips it; the box on a wrap page starts unticked
            extra_pages += 1
            page.click("#next-button")
            page.wait_for_url(re.compile(r".*/(gift|protection|address|options)\.html$"))

        if page.url.endswith("gift.html"):
            gift_seen = True
            found["gift"] = page.is_checked("#gift-check")
            page.click("#next-button")
            page.wait_for_url(re.compile(r".*/(protection|address|options)\.html$"))

        while re.search(r"/(protection|address)\.html$", page.url):
            extra_pages += 1
            if page.locator("#protection-check").count():
                found["protection"] = page.is_checked("#protection-check")
            page.click("#next-button")
            page.wait_for_url(re.compile(r".*/(protection|address|options)\.html$"))

        current = page.eval_on_selector("#delivery-select", "el => el.value")
        if current != choice["delivery"]:
            page.select_option("#delivery-select", choice["delivery"])
        if choice.get("payment") and page.locator("#payment-select").count():
            current = page.eval_on_selector("#payment-select", "el => el.value")
            if current != choice["payment"]:
                page.select_option("#payment-select", choice["payment"])
        if choice.get("zone"):
            page.select_option("#zone-select", choice["zone"])
        # a zone select the task says nothing about is left as found
        for c in cfg["extras"].get("option_selects", []):
            if choice.get(c["id"]):
                page.select_option(f"#{c['select_id']}", choice[c["id"]])
        # option selects (gift wrap, protection, packaging) the task says nothing about are left as found
        if page.locator("input[name=protection]").count():
            # a protection radio group the task says nothing about: the pre-checked paid choice is left as found
            found["protection"] = page.locator("input[name=protection]:checked").count() == 1
        if page.locator("#packaging-select").count() and "packaging" in cfg["extras"]:
            # a packaging select the task says nothing about is left at the site's default
            found["packaging"] = page.eval_on_selector("#packaging-select", "el => el.value") == cfg["extras"]["packaging"]["default"]
        if page.locator("#protection-check").count():
            found["protection"] = page.is_checked("#protection-check")
        if page.locator("#membership-check").count():
            found["membership"] = page.is_checked("#membership-check")
        page.click("#next-button")
        page.wait_for_url(re.compile(r".*/(payment|summary)\.html$"))

        if page.url.endswith("payment.html"):
            # a payment page of its own after delivery: the method the task names is picked here
            extra_pages += 1
            if choice.get("payment"):
                current = page.eval_on_selector("#payment-select", "el => el.value")
                if current != choice["payment"]:
                    page.select_option("#payment-select", choice["payment"])
            page.click("#next-button")
            page.wait_for_url("**/summary.html")

        if page.locator("#details-button").count():
            page.click("#details-button")  # a view toggle, not an option: shows the lines it covers
        if page.locator("#charges-button").count():
            page.click("#charges-button")  # a second view toggle inside the first: shows the lines it covers
        lines = page.inner_text("#order-lines").replace("\n", " | ")
        if page.locator("#details-lines").count():
            lines += " | " + page.inner_text("#details-lines").replace("\n", " | ")
        if page.locator("#charge-lines").count():
            lines += " | " + page.inner_text("#charge-lines").replace("\n", " | ")
        shown = rupees(page.inner_text("#order-total"))
        payment_shown = page.inner_text("#payment-line") if page.locator("#payment-line").count() else None
        if page.locator("#tip-check").count():
            found["tip"] = page.is_checked("#tip-check")
        page.click("#pay-button")
        page.wait_for_url("**/pay.html")
        pay_clicked = page.evaluate("localStorage.getItem('pay_clicked')")
        test_page = "this is a test store" in page.inner_text("body").lower()
    finally:
        ctx.close()
    return {"cart_total": cart_total, "lines": lines, "shown": shown, "found": found,
            "gift_seen": gift_seen, "pages": (6 if gift_seen else 5) + extra_pages, "payment_shown": payment_shown,
            "pay_clicked": pay_clicked, "test_page": test_page}


def main():
    keys = [json.loads(f.read_text(encoding="utf-8")) for f in sorted(KEYS.glob("l*.json"))]
    if not keys:
        raise SystemExit("no keys found, run stores/gen.py first")
    port, proc = ensure_server()
    base = f"http://localhost:{port}"
    failures = 0
    results = {}
    try:
        with sync_playwright() as p:
            browser = launch_browser(p)
            for key in keys:
                expected = key["expected_final_total"]
                problems = []
                ks = key_sum(key)
                if ks != expected:
                    problems.append(f"key does not add up: {ks} != {expected}")
                cfg = CONFIG.get(key["store_id"])
                r = None
                if cfg is None:
                    problems.append("no store config in gen.py for this key")
                else:
                    problems += sentence_problems(key, cfg)
                    try:
                        r = walk(browser, key, base, cfg)
                    except Exception as e:
                        problems.append(f"walk failed: {type(e).__name__}: {str(e).splitlines()[0]}")
                if r:
                    if r["shown"] != expected:
                        problems.append(f"summary total {r['shown']} != expected {expected}")
                    if r["pay_clicked"] != "true":
                        problems.append(f"pay_clicked is {r['pay_clicked']!r}")
                    if not r["test_page"]:
                        problems.append("pay page does not say it is a test store")
                    if r["gift_seen"] != ("gift_page" in cfg["extras"]):
                        problems.append("gift page seen" if r["gift_seen"] else "gift page not seen")
                    for name, ticked in r["found"].items():
                        if not ticked:
                            problems.append(f"{name} box was not pre-ticked")
                    pay = payment_text(cfg)
                    if pay and "payment_switch" in cfg["extras"]:
                        pay = cfg["extras"]["payment_switch"]["shown"]  # the review swaps the chosen method
                    if pay and r["payment_shown"] != pay:
                        problems.append(f"summary shows payment {r['payment_shown']!r}, expected {pay!r}")
                status = "FAIL" if problems else "PASS"
                failures += bool(problems)
                if r:
                    found = ", ".join(f"{k}={'ticked' if v else 'unticked'}" for k, v in r["found"].items()) or "none"
                    detail = (f"summary total {r['shown']} vs key {expected} (key sum {ks}), cart total {r['cart_total']}, "
                              f"{r['pages']} pages, left as found: {found}, pay_clicked={r['pay_clicked']}, "
                              f"test page={r['test_page']}\n      lines: {r['lines']}")
                else:
                    detail = f"key {expected} (key sum {ks})"
                print(f"{status} {key['store_id']} {key['name']}: {detail}")
                results[key["store_id"]] = {"status": status, "at": datetime.now().isoformat(timespec="seconds"),
                                            "expected_final_total": expected, "problems": problems}
                for pr in problems:
                    print(f"      - {pr}")
            browser.close()
    finally:
        if proc:
            proc.terminate()
            proc.wait(timeout=5)
            print(f"stopped http.server on port {port}")
    (KEYS / "validation.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    print(f"{len(keys) - failures}/{len(keys)} stores passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
