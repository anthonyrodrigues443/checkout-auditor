#!/usr/bin/env python3
"""Generate the second ladder of practice stores (L9-L12) and their answer keys.

Usage: python stores/gen2.py
Writes stores/www/l9 .. l12 and stores/keys/l9.json .. l12.json and nothing else: l1-l8 stay
exactly as gen.py wrote them (checked with git diff at the end). Re-running overwrites.

The product, cart, gift, options and pay pages come from gen.py's builders. The review page,
the script and the styles are this file's own because the new mechanics need markup that
gen.py does not have. Extras a store can switch on:

  details           the review page prints "Amount payable" and a "View price details" button;
                    a charge that appeared nowhere earlier sits in a container that is
                    display:none until the button is clicked (key type collapsed_fee). With
                    "panel": "all" (the default) the whole itemisation is in that container;
                    with "panel": "charge" the other lines stay visible above the amount and
                    only that charge is behind the button, so the visible lines fall short of
                    the amount payable by exactly that charge. A delivery-switch note is
                    always plain visible text, never inside the container. At most one scored
                    charge may sit behind the button (checked at build time): the checker folds
                    every unreported rupee into one gap finding that pairs with one trap only,
                    so a record that never presses the button scores 0/n once two scored lines
                    share a fold
  delivery_upgrade  whatever delivery the shopper picks, the review page applies and shows the
                    express option, with a note and a "Change delivery" link back to the
                    options page (key type delivery_switched; the key keeps the shopper's
                    choice in chosen_options)
  price_update      the product line costs more in the cart than on the product page, with a
                    "Price updated" tag next to it and no extra line (key type price_change)
  cart_offer        a negative line in the cart's order box that is gone from the review
                    page (key type vanished_discount, in_total false: it never reached the
                    final total)
  gift_page, payment_methods, preticked: as in gen.py

Key invariant: first_price + upfront_charges + chosen_options + amounts of scored traps whose
in_total is not false == expected_final_total.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from gen import (  # noqa: E402
    ADDRESS, BASE_URL, CONTACT, CSS, FORBIDDEN_WORDS, KEYS, WWW,
    cart_page, gift_page, money, options_page, page, pay_page, product_page,
)

EARLIER_STORES = [f"l{n}" for n in range(1, 9)]

STORES = [
    {
        "id": "l9", "level": 9, "name": "Leaf Nook",
        "storage_key": "leafnook_crate",
        "words": {"cart": "crate", "add": "Add to crate", "next": "Carry on", "pay": "Pay and finish"},
        "colours": {"header": "#556b2f", "header_text": "#fff", "accent": "#6b8e23", "page": "#f7f9f1",
                    "font": "Courier New, Courier, monospace"},
        "layout": "receipt",
        "product": {"name": "Money Plant in Ceramic Pot", "price": 549,
                    "blurb": "Trailing money plant in a 6 inch glazed pot. Pet safe, low light is fine.",
                    "note": None},
        "sizes": None,
        "fixed_charges": [],
        "delivery": {
            "shown_upfront": True, "placeholder": None, "default": "standard",
            "options": [
                {"id": "standard", "text": "Standard ₹60", "line": "Delivery", "amount": 60},
                {"id": "express", "text": "Express ₹150", "line": "Express delivery", "amount": 150},
            ],
        },
        "extras": {
            "details": {"show": "View price details", "hide": "Hide price details",
                        "charge": {"label": "Processing fee", "amount": 29}},
        },
        "task": "Buy one money plant in a ceramic pot with standard delivery.",
        "task_choice": {"size": None, "delivery": "standard"},
    },
    {
        "id": "l10", "level": 10, "name": "Brew Lane",
        "storage_key": "brewlane_bundle",
        "words": {"cart": "bundle", "add": "Add to bundle", "next": "Keep going", "pay": "Place my order"},
        "colours": {"header": "#37474f", "header_text": "#eceff1", "accent": "#455a64", "page": "#f4f6f7",
                    "font": "Futura, Century Gothic, sans-serif"},
        "layout": "ribbon",
        "product": {"name": "Assam Black Tea 250 g", "price": 380,
                    "blurb": "Second flush leaf tea from a single Assam estate. Resealable pouch.",
                    "note": None},
        "sizes": None,
        "fixed_charges": [],
        "delivery": {
            "shown_upfront": False, "placeholder": "Choose a delivery speed", "default": None,
            "options": [
                {"id": "standard", "text": "Standard – Free", "line": "Standard delivery", "amount": 0},
                {"id": "express", "text": "Express ₹79", "line": "Express delivery", "amount": 79},
            ],
        },
        "extras": {
            "delivery_upgrade": {"to": "express", "note": "We upgraded your delivery to Express",
                                 "link": "Change delivery"},
        },
        "task": "Buy one 250 g pouch of Assam black tea with standard delivery.",
        "task_choice": {"size": None, "delivery": "standard"},
    },
    {
        "id": "l11", "level": 11, "name": "Loom Room",
        "storage_key": "loomroom_trunk",
        "words": {"cart": "trunk", "add": "Add to trunk", "next": "Onward", "pay": "Finish and pay"},
        "colours": {"header": "#7b1f3a", "header_text": "#fff", "accent": "#9c2c4f", "page": "#fdf6f8",
                    "font": "Times New Roman, Times, serif"},
        "layout": "narrow",
        "product": {"name": "Handloom Cotton Kurta", "price": 1299,
                    "blurb": "Block-printed cotton kurta, relaxed fit, machine washable.",
                    "note": "Free delivery"},
        "sizes": None,
        "fixed_charges": [],
        "delivery": {
            "shown_upfront": True, "placeholder": None, "default": "standard",
            "options": [
                {"id": "standard", "text": "Standard – Free", "line": "Delivery", "amount": 0},
                {"id": "express", "text": "Express ₹99", "line": "Express delivery", "amount": 99},
            ],
        },
        "extras": {
            "price_update": {"amount": 50, "text": "Price updated"},
            "cart_offer": {"label": "Welcome offer", "amount": -100},
        },
        "task": "Buy one handloom cotton kurta with standard delivery.",
        "task_choice": {"size": None, "delivery": "standard"},
    },
    {
        "id": "l12", "level": 12, "name": "Crumb Corner",
        "storage_key": "crumbcorner_box",
        "words": {"cart": "box", "add": "Add to box", "next": "Move ahead", "pay": "Order and pay"},
        "colours": {"header": "#212121", "header_text": "#ffe082", "accent": "#ff8f00", "page": "#fffdf7",
                    "font": "Avenir, Franklin Gothic Medium, Arial, sans-serif"},
        "layout": "ledger",
        "product": {"name": "Dry Fruit Cake 500 g", "price": 720,
                    "blurb": "Dry fruit cake with cashews, raisins and candied peel. Keeps for two weeks.",
                    "note": "Taxes included"},
        "sizes": None,
        "fixed_charges": [],
        "delivery": {
            "shown_upfront": False, "placeholder": "Select delivery", "default": None,
            "options": [
                {"id": "standard", "text": "Standard – Free", "line": "Standard delivery", "amount": 0},
                {"id": "express", "text": "Express ₹89", "line": "Express delivery", "amount": 89},
            ],
        },
        "extras": {
            "gift_page": {"heading": "Add a message", "text": "Is this cake a present? Pick what goes in the box.",
                          "label": "Greeting card", "amount": 35, "next": "Move ahead"},
            "delivery_upgrade": {"to": "express", "note": "We upgraded your delivery to Express",
                                 "link": "Change delivery"},
            "details": {"show": "View price details", "hide": "Hide price details",
                        "charge": {"label": "Service fee", "amount": 39}, "panel": "charge"},
            "payment_methods": {
                "default": None, "placeholder": "Select payment",
                "options": [{"id": "upi", "text": "UPI"}, {"id": "card", "text": "Card"},
                            {"id": "cod", "text": "Cash on delivery"}],
                "cod_option": "cod", "cod_charge": {"label": "Cash handling", "amount": 45},
            },
        },
        "task": "Buy one 500 g dry fruit cake with standard delivery and pay by cash on delivery.",
        "task_choice": {"size": None, "delivery": "standard", "payment": "cod"},
    },
]

FORBIDDEN_WORDS2 = FORBIDDEN_WORDS + ["switch-trap", "switched", "bait", "vanish", "collaps", "fold", "forced"]


# ---------- review page ----------

def review_box(s):
    """The order box of the review page. With "details" some or all lines sit behind a button.

    The delivery-switch note is always outside the panel: it must be readable without a click.
    """
    e = s["extras"]
    lines = '<div id="order-lines"></div>'
    note = ""
    if "delivery_upgrade" in e:
        du = e["delivery_upgrade"]
        note = f'\n  <p id="delivery-note" class="small">{du["note"]}. <a href="options.html">{du["link"]}</a></p>'
    if "details" in e:
        dt = e["details"]
        payable = f"""  <p class="payable">Amount payable <span id="order-total"></span></p>
  <button id="details-button" type="button">{dt['show']}</button>
  <div id="details-panel" class="details">"""
        if dt.get("panel", "all") == "charge":
            return f"""<aside class="order-box">
  <h2>Order summary</h2>
  {lines}{note}
{payable}
  <div id="details-lines"></div>
  </div>
</aside>"""
        return f"""<aside class="order-box">
  <h2>Order summary</h2>{note}
{payable}
  {lines}
  </div>
</aside>"""
    return f"""<aside class="order-box">
  <h2>Order summary</h2>
  {lines}{note}
  <div class="line total"><span>Total</span><span id="order-total"></span></div>
</aside>"""


def summary_page(s):
    parts = [f'<div class="address"><strong>Deliver to</strong><br>{ADDRESS}<br>{CONTACT}</div>']
    if "payment_methods" in s["extras"]:
        parts.append('<div class="address"><strong>Payment</strong><br><span id="payment-line"></span></div>')
    parts.append(review_box(s))
    parts.append(f'<p><button id="pay-button" type="button" data-pay>{s["words"]["pay"]}</button></p>')
    body = "<h1>Review your order</h1>\n<section class=\"content\">\n" + "".join(parts) + "\n</section>"
    return page(s, "summary", f"Review your order – {s['name']}", body)


# ---------- script and styles ----------

JS_BODY = r"""
var KEY = STORE.storageKey;

function money(n) {
  var sign = n < 0 ? "-" : "";
  return sign + "₹" + Math.abs(n).toLocaleString("en-IN");
}
function load() {
  try { return JSON.parse(localStorage.getItem(KEY)) || null; } catch (e) { return null; }
}
function save(s) { localStorage.setItem(KEY, JSON.stringify(s)); }
function notice(msg) { var n = document.getElementById("notice"); if (n) n.textContent = msg; }
function findOption(id) {
  var opts = STORE.delivery.options;
  for (var i = 0; i < opts.length; i++) if (opts[i].id === id) return opts[i];
  return null;
}
function deliveryChoice(s) { return findOption(s.delivery || STORE.delivery.default); }
function reviewPage(pageName) { return pageName === "summary" || pageName === "pay"; }

function productLine(s, pageName) {
  var label = STORE.product.name + (s.size ? " (size " + s.size + ")" : "");
  var amount = STORE.product.price;
  if (STORE.priceUpdate) {
    amount = STORE.product.price + STORE.priceUpdate.amount;
    if (pageName === "cart") label += ' <small class="tag">' + STORE.priceUpdate.text + "</small>";
  }
  return {label: label, amount: amount};
}

function orderLines(s, pageName) {
  var out = [productLine(s, pageName)];
  STORE.fixedCharges.forEach(function (c) { out.push(c); });
  if (STORE.protection && s.protection && pageName !== "cart") out.push(STORE.protection);
  if (STORE.gift && s.gift && pageName !== "cart") out.push(STORE.gift);
  var d = deliveryChoice(s);
  if (STORE.deliveryUpgrade && reviewPage(pageName)) d = findOption(STORE.deliveryUpgrade.to);
  if (d) out.push({label: d.line, amount: d.amount});
  if (STORE.cartOffer && pageName === "cart") out.push(STORE.cartOffer);
  if (reviewPage(pageName)) {
    if (STORE.details && STORE.details.charge) out.push(STORE.details.charge);
    if (STORE.payment && STORE.payment.codCharge && s.payment === STORE.payment.codOption) out.push(STORE.payment.codCharge);
  }
  return out;
}

function renderOrder(pageName) {
  var s = load();
  var box = document.getElementById("order-lines");
  var tot = document.getElementById("order-total");
  if (!s) {
    if (box) box.innerHTML = "<p>Your " + STORE.words.cart + " is empty.</p>";
    if (tot) tot.textContent = money(0);
    return 0;
  }
  var lines = orderLines(s, pageName);
  if (box) {
    box.innerHTML = lines.map(function (l) {
      return '<div class="line"><span>' + l.label + "</span><span>" + money(l.amount) + "</span></div>";
    }).join("");
  }
@@DETAILS_LINES@@  var t = lines.reduce(function (a, l) { return a + l.amount; }, 0);
  if (tot) tot.textContent = money(t);
  return t;
}

function initProduct() {
  var sizeSel = document.getElementById("size-select");
  document.getElementById("add-button").addEventListener("click", function () {
    var size = sizeSel ? sizeSel.value : null;
    if (sizeSel && !size) { notice("Please choose a size first."); return; }
    save({qty: 1, size: size || null, protection: !!STORE.protection, gift: !!STORE.gift,
          delivery: null, payment: null});
    location.href = "cart.html";
  });
}

function initCart() {
  renderOrder("cart");
  document.getElementById("next-button").addEventListener("click", function () {
    location.href = STORE.gift ? "gift.html" : "options.html";
  });
}

function initGift() {
  var s = load();
  if (!s) { renderOrder("gift"); return; }
  var chk = document.getElementById("gift-check");
  chk.checked = !!s.gift;
  chk.addEventListener("change", function () { s.gift = chk.checked; save(s); renderOrder("gift"); });
  renderOrder("gift");
  document.getElementById("next-button").addEventListener("click", function () { location.href = "options.html"; });
}

function initOptions() {
  var s = load();
  if (!s) { renderOrder("options"); return; }
  var sel = document.getElementById("delivery-select");
  if (!s.delivery && STORE.delivery.default) { s.delivery = STORE.delivery.default; save(s); }
  sel.value = s.delivery || "";
  sel.addEventListener("change", function () { s.delivery = sel.value || null; save(s); renderOrder("options"); });
  var chk = document.getElementById("protection-check");
  if (chk) {
    chk.checked = !!s.protection;
    chk.addEventListener("change", function () { s.protection = chk.checked; save(s); renderOrder("options"); });
  }
  var paySel = document.getElementById("payment-select");
  if (paySel) {
    if (!s.payment && STORE.payment.default) { s.payment = STORE.payment.default; save(s); }
    paySel.value = s.payment || "";
    paySel.addEventListener("change", function () { s.payment = paySel.value || null; save(s); renderOrder("options"); });
  }
  renderOrder("options");
  document.getElementById("next-button").addEventListener("click", function () {
    if (!s.delivery) { notice("Please choose a delivery option."); return; }
    if (STORE.payment && !s.payment) { notice("Please choose a payment method."); return; }
    location.href = "summary.html";
  });
}

function initSummary() {
  var s = load();
  var t = renderOrder("summary");
  var payLine = document.getElementById("payment-line");
  if (payLine && STORE.payment) {
    var chosen = null;
    if (s) STORE.payment.options.forEach(function (o) { if (o.id === s.payment) chosen = o; });
    payLine.textContent = chosen ? chosen.text : "Not chosen";
  }
  var note = document.getElementById("delivery-note");
  if (note && s && STORE.deliveryUpgrade && s.delivery === STORE.deliveryUpgrade.to) note.style.display = "none";
  var btn = document.getElementById("details-button");
  var panel = document.getElementById("details-panel");
  if (btn && panel) btn.addEventListener("click", function () {
    var open = panel.classList.toggle("open");
    btn.textContent = open ? STORE.details.hide : STORE.details.show;
  });
  var buttons = document.querySelectorAll("[data-pay]");
  Array.prototype.forEach.call(buttons, function (b) {
    b.textContent = b.textContent.replace("{total}", money(t));
    b.addEventListener("click", function () {
      localStorage.setItem("pay_clicked", "true");
      location.href = "pay.html";
    });
  });
}

var PAGE = document.body.getAttribute("data-page");
if (PAGE === "index") initProduct();
else if (PAGE === "cart") initCart();
else if (PAGE === "gift") initGift();
else if (PAGE === "options") initOptions();
else if (PAGE === "summary") initSummary();
else if (PAGE === "pay") renderOrder("pay");
"""

# Inserted at @@DETAILS_LINES@@ only for a "panel": "charge" store: the line flagged inDetails
# (the charge behind the button) renders into the panel, everything else stays in #order-lines.
JS_DETAILS_LINES = r"""  var panelBox = document.getElementById("details-lines");
  if (box && panelBox) {
    var lineHtml = function (l) {
      return '<div class="line"><span>' + l.label + "</span><span>" + money(l.amount) + "</span></div>";
    };
    box.innerHTML = lines.filter(function (l) { return !l.inDetails; }).map(lineHtml).join("");
    panelBox.innerHTML = lines.filter(function (l) { return l.inDetails; }).map(lineHtml).join("");
  }
"""


def details_config(e):
    """STORE.details for app.js, or None. The charge carries inDetails when only it sits in the panel."""
    if "details" not in e:
        return None
    dt = e["details"]
    charge = dict(dt["charge"])
    if dt.get("panel", "all") == "charge":
        charge["inDetails"] = True
    return {"show": dt["show"], "hide": dt["hide"], "charge": charge}


def app_js(s):
    e = s["extras"]
    cfg = {
        "storageKey": s["storage_key"],
        "words": s["words"],
        "product": {"name": s["product"]["name"], "price": s["product"]["price"]},
        "fixedCharges": s["fixed_charges"],
        "delivery": {"default": s["delivery"]["default"], "options": s["delivery"]["options"]},
        "protection": e.get("preticked"),
        "gift": ({"label": e["gift_page"]["label"], "amount": e["gift_page"]["amount"]} if "gift_page" in e else None),
        "deliveryUpgrade": ({"to": e["delivery_upgrade"]["to"]} if "delivery_upgrade" in e else None),
        "details": details_config(e),
        "priceUpdate": e.get("price_update"),
        "cartOffer": e.get("cart_offer"),
        "payment": None,
    }
    if "payment_methods" in e:
        pm = e["payment_methods"]
        cfg["payment"] = {"default": pm["default"], "options": pm["options"],
                          "codOption": pm.get("cod_option"), "codCharge": pm.get("cod_charge")}
    panel_charge = "details" in e and e["details"].get("panel", "all") == "charge"
    body = JS_BODY.replace("@@DETAILS_LINES@@", JS_DETAILS_LINES if panel_charge else "")
    if "@@" in body:
        raise SystemExit("unfilled script marker in " + s["id"])
    return "var STORE = " + json.dumps(cfg, ensure_ascii=False, indent=2) + ";\n" + body


EXTRA_CSS = """
.payable { font-size: 20px; font-weight: bold; margin: 8px 0 12px; }
.details { display: none; margin-top: 12px; border-top: 1px solid #ddd; padding-top: 6px; }
.details.open { display: block; }
.tag { font-size: 12px; color: #b00; margin-left: 6px; font-weight: normal; }
.small { font-size: 13px; color: #555; margin: 6px 0 0; }
"""

LAYOUT_CSS = {
    "receipt": """.shell { max-width: 560px; }
.site-header { flex-direction: column; gap: 6px; text-align: center; }
.order-box, .price-lines { border: 1px dashed #666; background: #fffef8; }
.order-box h2 { text-transform: uppercase; letter-spacing: 2px; text-align: center; }
.line { border-bottom: 1px dotted #999; }
button { width: 100%; }""",
    "ribbon": """.site-header { padding: 6px 24px; font-size: 14px; border-bottom: 4px solid #90a4ae; }
.shell { max-width: 900px; }
h1 { font-weight: normal; border-bottom: 1px solid #b0bec5; padding-bottom: 8px; }
.content { display: grid; grid-template-columns: 3fr 2fr; gap: 20px; align-items: start; }
.content > * { margin: 0; }
.content > .order-box { grid-column: 2; grid-row: 1 / span 6; }
.content > :not(.order-box) { grid-column: 1; }
.product { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }""",
    "narrow": """.shell { max-width: 430px; padding: 12px; }
.site-header { flex-direction: column; align-items: flex-start; gap: 4px; padding: 12px 16px; }
.order-box, .price-lines, .address, .product-image { border-radius: 12px; }
button { width: 100%; border-radius: 22px; }
select { width: 100%; }
h1 { font-size: 22px; }""",
    "ledger": """.shell { max-width: 1000px; }
h1 { border-bottom: 3px solid #ff8f00; padding-bottom: 6px; }
.content { display: grid; grid-template-columns: 2fr 3fr; gap: 24px; align-items: start; }
.content > * { margin: 0; }
.content > .order-box { grid-column: 1; grid-row: 1 / span 8; border: 2px solid #212121; }
.content > :not(.order-box) { grid-column: 2; }
.line.total { border-top: 2px solid #212121; padding-top: 8px; }
.product { display: grid; grid-template-columns: 2fr 3fr; gap: 24px; }""",
}


def style_css(s):
    c = s["colours"]
    return CSS.substitute(font=c["font"], page=c["page"], header=c["header"], header_text=c["header_text"],
                          accent=c["accent"], layout=LAYOUT_CSS[s["layout"]] + EXTRA_CSS)


# ---------- answer key ----------

def build_key(s):
    e = s["extras"]
    d = s["delivery"]
    chosen_opt = next(o for o in d["options"] if o["id"] == s["task_choice"]["delivery"])
    upfront = list(s["fixed_charges"])
    chosen = []
    if d["shown_upfront"]:
        upfront.append({"label": "Delivery", "amount": chosen_opt["amount"]})
    else:
        chosen.append({"label": chosen_opt["line"], "amount": chosen_opt["amount"]})
    pm = e.get("payment_methods")
    pay_choice = s["task_choice"].get("payment")
    if pm and pay_choice:
        pay_opt = next(o for o in pm["options"] if o["id"] == pay_choice)
        chosen.append({"label": pay_opt["text"], "amount": 0})
    traps = []
    if "price_update" in e:
        x = e["price_update"]
        traps.append({"type": "price_change", "label": s["product"]["name"], "amount": x["amount"],
                      "scored": True, "pattern": "bait and switch"})
    if "cart_offer" in e:
        x = e["cart_offer"]
        traps.append({"type": "vanished_discount", "label": x["label"], "amount": -x["amount"],
                      "scored": True, "pattern": "bait and switch", "in_total": False})
    if "gift_page" in e:
        x = e["gift_page"]
        traps.append({"type": "pre_ticked_addon", "label": x["label"], "amount": x["amount"],
                      "scored": True, "pattern": "basket sneaking"})
    if "preticked" in e:
        x = e["preticked"]
        traps.append({"type": "pre_ticked_addon", "label": x["label"], "amount": x["amount"],
                      "scored": True, "pattern": "basket sneaking"})
    if "delivery_upgrade" in e and e["delivery_upgrade"]["to"] != chosen_opt["id"]:
        up = next(o for o in d["options"] if o["id"] == e["delivery_upgrade"]["to"])
        traps.append({"type": "delivery_switched", "label": up["line"], "amount": up["amount"] - chosen_opt["amount"],
                      "scored": True, "pattern": "interface interference"})
    if "details" in e:
        x = e["details"]["charge"]
        traps.append({"type": "collapsed_fee", "label": x["label"], "amount": x["amount"],
                      "scored": True, "pattern": "drip pricing"})
    if pm and pm.get("cod_charge") and pay_choice == pm.get("cod_option"):
        x = pm["cod_charge"]
        traps.append({"type": "cod_surcharge", "label": x["label"], "amount": x["amount"],
                      "scored": True, "pattern": "drip pricing"})
    expected = (s["product"]["price"] + sum(c["amount"] for c in upfront) + sum(c["amount"] for c in chosen)
                + sum(t["amount"] for t in traps if t["scored"] and t.get("in_total", True)))
    return {
        "store_id": s["id"], "level": s["level"], "name": s["name"], "url": f"{BASE_URL}/{s['id']}/",
        "task": s["task"],
        "first_price": s["product"]["price"],
        "upfront_charges": upfront,
        "chosen_options": chosen,
        "traps": traps,
        "expected_final_total": expected,
        "stop_point": "summary",
    }


def folded_scored_traps(s, key):
    """Scored traps whose review-page line sits inside the details panel."""
    dt = s["extras"].get("details")
    if not dt:
        return []
    scored = [t for t in key["traps"] if t["scored"] and t.get("in_total", True)]
    if dt.get("panel", "all") == "charge":
        return [t for t in scored if t["type"] == "collapsed_fee"]
    return scored


# ---------- main ----------

def check_neutral(folder):
    pattern = re.compile("|".join(re.escape(w) for w in FORBIDDEN_WORDS2), re.IGNORECASE)
    for f in folder.rglob("*"):
        if f.is_file():
            hit = pattern.search(f.read_text(encoding="utf-8")) or pattern.search(f.name)
            if hit:
                raise SystemExit(f"non-neutral word {hit.group(0)!r} in {f}")


def check_earlier_untouched():
    paths = [f"stores/www/{i}" for i in EARLIER_STORES] + [f"stores/keys/{i}.json" for i in EARLIER_STORES]
    try:
        out = subprocess.run(["git", "diff", "--stat", "--"] + paths, cwd=ROOT.parent,
                             capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as e:
        print(f"could not run git diff to confirm l1-l8 are untouched: {e}")
        return
    if out:
        raise SystemExit("l1-l8 changed, which gen2.py must never do:\n" + out)
    print("l1-l8 untouched (git diff is empty)")


def main():
    KEYS.mkdir(parents=True, exist_ok=True)
    for s in STORES:
        assert s["id"] not in EARLIER_STORES, s["id"]
        if "details" in s["extras"]:
            assert s["extras"]["details"].get("panel", "all") in ("all", "charge"), s["id"]
        out = WWW / s["id"]
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True)
        (out / "index.html").write_text(product_page(s), encoding="utf-8")
        (out / "cart.html").write_text(cart_page(s), encoding="utf-8")
        if "gift_page" in s["extras"]:
            (out / "gift.html").write_text(gift_page(s), encoding="utf-8")
        (out / "options.html").write_text(options_page(s), encoding="utf-8")
        (out / "summary.html").write_text(summary_page(s), encoding="utf-8")
        (out / "pay.html").write_text(pay_page(s), encoding="utf-8")
        (out / "app.js").write_text(app_js(s), encoding="utf-8")
        (out / "style.css").write_text(style_css(s), encoding="utf-8")
        check_neutral(out)
        key = build_key(s)
        folded = folded_scored_traps(s, key)
        if len(folded) > 1:
            raise SystemExit(f"{s['id']}: {len(folded)} scored charges behind one fold "
                             f"({', '.join(t['label'] for t in folded)}); keep at most one")
        (KEYS / f"{s['id']}.json").write_text(json.dumps(key, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{s['id']} {s['name']}: expected_final_total={key['expected_final_total']} -> {out}")
    check_earlier_untouched()
    print(f"wrote {len(STORES)} stores under {WWW} and their keys under {KEYS}")


if __name__ == "__main__":
    main()
