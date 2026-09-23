#!/usr/bin/env python3
"""Scripted Playwright walk of every store (no model).

For each store: follow the task sentence with clicks/selects only, leave pre-selected
options exactly as found, dismiss pop-ups, check the summary total against the answer
key, click the pay button, check pay_clicked and the test-store page. Also checks each
key adds up. Prints PASS/FAIL per store, exits non-zero on any failure.

Usage: python stores/validate.py
"""
import json
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
            + sum(t["amount"] for t in key["traps"] if t["scored"]))


def walk(browser, key, base):
    task = key["task"].lower()
    ctx = browser.new_context()
    page = ctx.new_page()
    try:
        page.goto(f"{base}/{key['store_id']}/")
        size = re.search(r"size (\d+)", task)
        if size:
            page.select_option("#size-select", size.group(1))
        page.click("#add-button")
        page.wait_for_url("**/cart.html")

        if page.locator(".promo-modal").count():
            page.click("#offer-no")
            page.wait_for_selector(".promo-modal", state="detached")
        cart_total = page.inner_text("#order-total")
        page.click("#next-button")
        page.wait_for_url("**/options.html")

        wanted = "express" if "express" in task else "standard"
        current = page.eval_on_selector("#delivery-select", "el => el.value")
        if current != wanted:
            page.select_option("#delivery-select", wanted)
        page.click("#next-button")
        page.wait_for_url("**/summary.html")

        lines = page.inner_text("#order-lines").replace("\n", " | ")
        shown = rupees(page.inner_text("#order-total"))
        page.click("#pay-button")
        page.wait_for_url("**/pay.html")
        pay_clicked = page.evaluate("localStorage.getItem('pay_clicked')")
        test_page = "this is a test store" in page.inner_text("body").lower()
    finally:
        ctx.close()
    return {"cart_total": cart_total, "lines": lines, "shown": shown,
            "pay_clicked": pay_clicked, "test_page": test_page}


def main():
    keys = [json.loads(f.read_text(encoding="utf-8")) for f in sorted(KEYS.glob("l*.json"))]
    if not keys:
        raise SystemExit("no keys found, run stores/gen.py first")
    port, proc = ensure_server()
    base = f"http://localhost:{port}"
    failures = 0
    try:
        with sync_playwright() as p:
            browser = launch_browser(p)
            for key in keys:
                expected = key["expected_final_total"]
                problems = []
                ks = key_sum(key)
                if ks != expected:
                    problems.append(f"key does not add up: {ks} != {expected}")
                try:
                    r = walk(browser, key, base)
                except Exception as e:
                    problems.append(f"walk failed: {type(e).__name__}: {str(e).splitlines()[0]}")
                    r = None
                if r:
                    if r["shown"] != expected:
                        problems.append(f"summary total {r['shown']} != expected {expected}")
                    if r["pay_clicked"] != "true":
                        problems.append(f"pay_clicked is {r['pay_clicked']!r}")
                    if not r["test_page"]:
                        problems.append("pay page does not say it is a test store")
                status = "FAIL" if problems else "PASS"
                failures += bool(problems)
                detail = (f"summary total {r['shown']} vs key {expected} (key sum {ks}), cart total {r['cart_total']}, "
                          f"pay_clicked={r['pay_clicked']}, test page={r['test_page']}\n      lines: {r['lines']}"
                          if r else f"key {expected} (key sum {ks})")
                print(f"{status} {key['store_id']} {key['name']}: {detail}")
                for pr in problems:
                    print(f"      - {pr}")
            browser.close()
    finally:
        if proc:
            proc.terminate()
            proc.wait(timeout=5)
            print(f"stopped http.server on port {port}")
    print(f"{len(keys) - failures}/{len(keys)} stores passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
