#!/usr/bin/env python3
"""Generate the practice stores L13-L16 and their answer keys.

Usage: python stores/gen3.py
Writes stores/www/l13 .. l16 (the served root) and stores/keys/l13.json .. l16.json (outside
the served root). Only those four folders and four key files are touched; re-running overwrites
them and nothing else. Page shells, the money helper and the base CSS come from stores/gen.py;
the page builders, the script and the key builder live here because these stores have
mechanics gen.py does not have (a longer flow with its own pages, a quantity select, a
membership box that costs nothing today, a coupon that really applies, a per-100 g headline).

What each store adds on top of the product -> cart -> ... -> summary -> pay flow:
  l13  gift page (pre-ticked card), cover page (pre-ticked cover), address page with a confirm
       button, delivery page with a placeholder select, a summary-only platform fee and an
       offer pop-up on the cart. Eight pages.
  l14  quantity select on the product page whose default is 2. Nothing else. Five pages.
  l15  pre-ticked membership box at 0 rupees today on the delivery page plus a pre-filled coupon
       box on the cart whose button really takes 200 rupees off. Five pages.
  l16  per-100 g headline price with the pack price further down, plus a summary-only cold
       chain fee. Five pages.
"""
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from gen import ADDRESS, BASE_URL, CONTACT, CSS, FORBIDDEN_WORDS, KEYS, WWW, check_neutral, money, order_box, page  # noqa: E402

EXTRA_FORBIDDEN = ["bait", "trick", "decept", "deceiv", "manipul", "nudge"]

STORES = [
    {
        "id": "l13", "level": 13, "name": "Lumen Lane",
        "storage_key": "lumenlane_crate",
        "words": {"cart": "crate", "add": "Add to crate", "next": "Carry on", "pay": "Pay and finish"},
        "colours": {"header": "#455a64", "header_text": "#eceff1", "accent": "#546e7a", "page": "#f4f6f7",
                    "font": "Baskerville, Times New Roman, serif"},
        "layout": "rail",
        "product": {"name": "Bamboo Desk Lamp", "price": 1450,
                    "blurb": "Warm-white LED desk lamp with a bamboo arm and a touch dimmer.", "note": None},
        "quantity": None,
        "unit_price": None,
        "delivery": {
            "shown_upfront": False, "placeholder": "Choose a delivery speed", "default": None,
            "options": [
                {"id": "standard", "text": "Standard ₹0", "line": "Standard delivery", "amount": 0},
                {"id": "express", "text": "Express ₹120", "line": "Express delivery", "amount": 120},
            ],
        },
        "pages": ["index", "cart", "gift", "protection", "address", "options", "summary", "pay"],
        "extras": {
            "addon_offer": {"label": "Second Bamboo Desk Lamp (20% off)", "amount": 1160,
                            "text": "Add a second one at 20% off? A second Bamboo Desk Lamp would be ₹1,160 instead of ₹1,450.",
                            "yes": "Add a second lamp", "no": "No, just one"},
            "gift_page": {"heading": "Gift options", "text": "Is this lamp a present? Pick what to include.",
                          "label": "Greeting card", "amount": 35},
            "protection_page": {"heading": "Protect your order", "text": "Lamps travel by courier. Cover breakage in transit.",
                                "label": "Damage cover", "amount": 79},
            "address_page": {"heading": "Delivery address", "text": "We will deliver to the address below.",
                             "next": "Confirm address"},
            "summary_charge": {"label": "Platform fee", "amount": 19},
        },
        "task": "Buy one bamboo desk lamp with standard delivery.",
        "task_choice": {"size": None, "delivery": "standard"},
    },
    {
        "id": "l14", "level": 14, "name": "Towel Town",
        "storage_key": "toweltown_haul",
        "words": {"cart": "haul", "add": "Add to haul", "next": "Onward", "pay": "Place your order"},
        "colours": {"header": "#c2185b", "header_text": "#fff", "accent": "#ad1457", "page": "#fff5f8",
                    "font": "Futura, Century Gothic, sans-serif"},
        "layout": "boxed",
        "product": {"name": "Cotton Bath Towel", "price": 599,
                    "blurb": "600 GSM combed cotton bath towel, 70 x 140 cm, sand colour.", "note": None},
        "quantity": {"options": ["1", "2", "3"], "default": "2", "note": "Most people buy 2"},
        "unit_price": None,
        "delivery": {
            "shown_upfront": True, "placeholder": None, "default": "standard",
            "options": [
                {"id": "standard", "text": "Standard ₹40", "line": "Delivery", "amount": 40},
                {"id": "express", "text": "Express ₹95", "line": "Express delivery", "amount": 95},
            ],
        },
        "pages": ["index", "cart", "options", "summary", "pay"],
        "extras": {},
        "task": "Buy ONE cotton bath towel with standard delivery.",
        "task_choice": {"size": None, "delivery": "standard", "quantity": "1"},
    },
    {
        "id": "l15", "level": 15, "name": "Bean Counter",
        "storage_key": "beancounter_sack",
        "words": {"cart": "sack", "add": "Add to sack", "next": "Keep going", "pay": "Pay {total} now"},
        "colours": {"header": "#0288d1", "header_text": "#fff", "accent": "#0277bd", "page": "#f2f9fd",
                    "font": "Lucida Grande, Lucida Sans Unicode, sans-serif"},
        "layout": "stacked",
        "product": {"name": "Roasted Arabica Beans 250 g", "price": 520,
                    "blurb": "Medium roast single-estate arabica from Coorg. Whole beans, 250 g bag.", "note": None},
        "quantity": None,
        "unit_price": None,
        "delivery": {
            "shown_upfront": True, "placeholder": None, "default": "standard",
            "options": [
                {"id": "standard", "text": "Standard ₹49", "line": "Delivery", "amount": 49},
                {"id": "express", "text": "Express ₹130", "line": "Express delivery", "amount": 130},
            ],
        },
        "pages": ["index", "cart", "options", "summary", "pay"],
        "extras": {
            "coupon_box": {"code": "SAVE200", "button": "Apply coupon", "label": "Coupon SAVE200", "amount": -200,
                           "message": "Coupon SAVE200 applied: ₹200 off"},
            "membership": {"label": "Plus membership trial (₹0 today, ₹199/month after 30 days)",
                           "key_label": "Plus membership trial", "amount": 0},
        },
        "task": "Buy one 250 g bag of roasted arabica beans with standard delivery.",
        "task_choice": {"size": None, "delivery": "standard"},
    },
    {
        "id": "l16", "level": 16, "name": "Curd and Cream",
        "storage_key": "curdcream_cooler",
        "words": {"cart": "cooler", "add": "Add to cooler", "next": "Move on", "pay": "Confirm purchase"},
        "colours": {"header": "#212121", "header_text": "#f1f8e9", "accent": "#558b2f", "page": "#fafdf5",
                    "font": "Menlo, Consolas, Courier New, monospace"},
        "layout": "ledger",
        "product": {"name": "Aged Gouda Cheese (500 g pack)", "price": 445,
                    "blurb": "Eighteen-month aged gouda, vacuum packed, from a Pune creamery.", "note": None},
        "quantity": None,
        "unit_price": {"headline": "₹89 per 100 g", "pack": "Pack of 500 g",
                       "text": "Sold as a single 500 g pack. Keep refrigerated at 4 °C and eat within 3 weeks of opening."},
        "delivery": {
            "shown_upfront": True, "placeholder": None, "default": "standard",
            "options": [
                {"id": "standard", "text": "Standard ₹30", "line": "Delivery", "amount": 30},
                {"id": "express", "text": "Express ₹80", "line": "Express delivery", "amount": 80},
            ],
        },
        "pages": ["index", "cart", "options", "summary", "pay"],
        "extras": {
            "summary_charge": {"label": "Cold chain fee", "amount": 15},
        },
        "task": "Buy one 500 g pack of aged gouda cheese with standard delivery.",
        "task_choice": {"size": None, "delivery": "standard"},
    },
]

RAIL_STEPS = [("cart", "Crate"), ("gift", "Gift"), ("protection", "Cover"), ("address", "Address"),
              ("options", "Delivery"), ("summary", "Review"), ("pay", "Done")]


# ---------- page templates ----------

def rail_nav(s, active):
    items = "".join(f'<li class="{"active" if k == active else ""}">{label}</li>' for k, label in RAIL_STEPS)
    return f'<nav class="rail"><ol>{items}</ol></nav>'


def with_nav(s, page_name, body):
    if s["layout"] == "rail":
        return rail_nav(s, page_name) + "\n" + body
    return body


def flow_page(s, page_name, title, h1, parts, box_heading="Order summary"):
    """parts is a list of HTML strings; "ORDER" marks where the order box goes in the rail and
    ledger layouts. Boxed puts content and box side by side inside one bordered block, stacked
    puts the box under the content."""
    box = order_box(box_heading)
    pulled = "".join(p for p in parts if p != "ORDER")
    if s["layout"] == "boxed":
        body = f"<h1>{h1}</h1>\n<div class=\"boxed-wrap\">\n<section class=\"content\">\n{pulled}\n</section>\n{box}\n</div>"
    elif s["layout"] == "stacked":
        body = f"<h1>{h1}</h1>\n<section class=\"content\">\n{pulled}\n</section>\n{box}"
    else:
        content = "".join(box if p == "ORDER" else p for p in parts)
        body = f"<h1>{h1}</h1>\n<section class=\"content\">\n{content}\n</section>"
    return page(s, page_name, title, with_nav(s, page_name, body))


def price_block(s):
    """The price lines under the headline: pack or unit price, delivery when shown upfront, total for one."""
    p = s["product"]
    d = s["delivery"]
    upfront = []
    if d["shown_upfront"]:
        opt = next(o for o in d["options"] if o["id"] == d["default"])
        upfront.append({"label": "Delivery", "amount": opt["amount"]})
    if not upfront:
        return ""
    if s["unit_price"]:
        first = f'<div class="line"><span>{s["unit_price"]["pack"]}</span><span>{money(p["price"])}</span></div>'
    elif s["quantity"]:
        first = f'<div class="line"><span>Price (each)</span><span>{money(p["price"])}</span></div>'
    else:
        first = f'<div class="line"><span>Price</span><span>{money(p["price"])}</span></div>'
    rows = "".join(f'<div class="line"><span>{c["label"]}</span><span>{money(c["amount"])}</span></div>' for c in upfront)
    total = p["price"] + sum(c["amount"] for c in upfront)
    total_label = "Total (one unit)" if s["quantity"] else "Total"
    return f"""<div class="price-lines">
    {first}
    {rows}
    <div class="line total"><span>{total_label}</span><span>{money(total)}</span></div>
  </div>"""


def product_page(s):
    p = s["product"]
    if s["unit_price"]:
        headline = f'<p class="price">{s["unit_price"]["headline"]}</p>\n  <p>{s["unit_price"]["text"]}</p>'
    elif s["quantity"]:
        headline = f'<p class="price">Price {money(p["price"])} each</p>'
    else:
        headline = f'<p class="price">Price {money(p["price"])}</p>'
    note = f'<p class="note">{p["note"]}</p>' if p["note"] else ""
    qty = ""
    if s["quantity"]:
        q = s["quantity"]
        opts = "".join(f'<option value="{v}"{" selected" if v == q["default"] else ""}>{v}</option>' for v in q["options"])
        qty = (f'<p><label>Quantity <select id="quantity-select">{opts}</select></label> '
               f'<span class="hint">{q["note"]}</span></p>')
    body = f"""<section class="product">
  <div class="product-image">{p['name']}</div>
  <div class="product-info">
  <h1>{p['name']}</h1>
  <p class="blurb">{p['blurb']}</p>
  {headline}
  {note}
  {price_block(s)}
  {qty}
  <p id="notice" class="notice"></p>
  <button id="add-button" type="button">{s['words']['add']}</button>
  </div>
</section>"""
    return page(s, "index", f"{p['name']} – {s['name']}", with_nav(s, "index", body))


def cart_page(s):
    w = s["words"]
    parts = ["ORDER"]
    if "coupon_box" in s["extras"]:
        cb = s["extras"]["coupon_box"]
        parts.append(f'<p class="coupon-row"><label>Coupon code <input type="text" id="coupon-input" value="{cb["code"]}"></label> '
                     f'<button id="coupon-button" type="button">{cb["button"]}</button> <span id="coupon-note"></span></p>')
    parts.append(f'<p><button id="next-button" type="button">{w["next"]}</button></p>')
    return flow_page(s, "cart", f"Your {w['cart']} – {s['name']}", f"Your {w['cart']}", parts,
                     box_heading=f"Items in your {w['cart']}")


def check_page(s, page_name, ext, check_id):
    parts = [f'<p>{ext["text"]}</p>',
             f'<p class="addon-row"><label><input type="checkbox" id="{check_id}" checked> {ext["label"]} {money(ext["amount"])}</label></p>',
             "ORDER",
             f'<p><button id="next-button" type="button">{s["words"]["next"]}</button></p>']
    return flow_page(s, page_name, f"{ext['heading']} – {s['name']}", ext["heading"], parts)


def address_page(s):
    a = s["extras"]["address_page"]
    parts = [f'<p>{a["text"]}</p>',
             f'<div class="address"><strong>Deliver to</strong><br>{ADDRESS}<br>{CONTACT}</div>',
             "ORDER",
             f'<p><button id="next-button" type="button">{a["next"]}</button></p>']
    return flow_page(s, "address", f"{a['heading']} – {s['name']}", a["heading"], parts)


def options_page(s):
    d = s["delivery"]
    opts = ""
    if d["placeholder"]:
        opts += f'<option value="">{d["placeholder"]}</option>'
    for o in d["options"]:
        sel = " selected" if o["id"] == d["default"] else ""
        opts += f'<option value="{o["id"]}"{sel}>{o["text"]}</option>'
    form = f'<p><label>Delivery <select id="delivery-select">{opts}</select></label></p>'
    if "membership" in s["extras"]:
        m = s["extras"]["membership"]
        form += (f'<p class="addon-row"><label><input type="checkbox" id="membership-check" checked> '
                 f'{m["label"]}</label></p>')
    address = f'<div class="address"><strong>Deliver to</strong><br>{ADDRESS}<br>{CONTACT}</div>'
    h1 = "Delivery speed" if "address_page" in s["extras"] else "Delivery and address"
    parts = [form, address, "ORDER", '<p id="notice" class="notice"></p>',
             f'<p><button id="next-button" type="button">{s["words"]["next"]}</button></p>']
    return flow_page(s, "options", f"Delivery options – {s['name']}", h1, parts)


def summary_page(s):
    parts = [f'<div class="address"><strong>Deliver to</strong><br>{ADDRESS}<br>{CONTACT}</div>',
             "ORDER",
             f'<p><button id="pay-button" type="button" data-pay>{s["words"]["pay"]}</button></p>']
    return flow_page(s, "summary", f"Review your order – {s['name']}", "Review your order", parts)


def pay_page(s):
    body = f"""<section class="content">
  <h1>Thanks for shopping with {s['name']}</h1>
  <p class="notice">This is a test store. No payment was taken.</p>
  <p>Order total <span id="order-total"></span></p>
  <p><a href="index.html">Back to the shop</a></p>
</section>"""
    return page(s, "pay", f"Order placed – {s['name']}", with_nav(s, "pay", body))


# ---------- script and styles ----------

JS_BODY = r"""
var KEY = STORE.storageKey;
var PAGES = STORE.pages;

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
function reached(pageName, target) { return PAGES.indexOf(pageName) >= PAGES.indexOf(target); }

function orderLines(s, pageName) {
  var out = [];
  var qty = s.qty || 1;
  var name = STORE.product.name + (STORE.quantity ? " × " + qty : "");
  out.push({label: name, amount: STORE.product.price * qty});
  if (STORE.addonOffer && s.addon) out.push({label: STORE.addonOffer.label, amount: STORE.addonOffer.amount});
  if (STORE.gift && s.gift && reached(pageName, "gift")) out.push(STORE.gift);
  if (STORE.protection && s.protection && reached(pageName, "protection")) out.push(STORE.protection);
  if (STORE.membership && s.membership && reached(pageName, "options")) out.push(STORE.membership);
  if (STORE.coupon && s.coupon) out.push({label: STORE.coupon.label, amount: STORE.coupon.amount});
  var d = deliveryChoice(s);
  if (d) out.push({label: d.line, amount: d.amount});
  if (STORE.summaryCharge && reached(pageName, "summary")) out.push(STORE.summaryCharge);
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
  var t = lines.reduce(function (a, l) { return a + l.amount; }, 0);
  if (tot) tot.textContent = money(t);
  return t;
}

function initProduct() {
  var qtySel = document.getElementById("quantity-select");
  document.getElementById("add-button").addEventListener("click", function () {
    var qty = qtySel ? (parseInt(qtySel.value, 10) || 1) : 1;
    save({qty: qty, addon: false, offerAnswered: false, gift: !!STORE.gift, protection: !!STORE.protection,
          membership: !!STORE.membership, coupon: false, delivery: null});
    location.href = "cart.html";
  });
}

function showOffer(s) {
  var wrap = document.createElement("div");
  wrap.className = "promo-overlay";
  wrap.innerHTML = '<div class="promo-modal" role="dialog"><p>' + STORE.addonOffer.text + '</p>' +
    '<button type="button" id="offer-yes">' + STORE.addonOffer.yes + '</button> ' +
    '<button type="button" id="offer-no">' + STORE.addonOffer.no + '</button></div>';
  document.body.appendChild(wrap);
  function close(add) { s.addon = add; s.offerAnswered = true; save(s); wrap.remove(); renderOrder("cart"); }
  document.getElementById("offer-yes").addEventListener("click", function () { close(true); });
  document.getElementById("offer-no").addEventListener("click", function () { close(false); });
}

function initCart() {
  renderOrder("cart");
  var s = load();
  document.getElementById("next-button").addEventListener("click", function () { location.href = STORE.next.cart; });
  if (s && STORE.addonOffer && !s.offerAnswered) showOffer(s);
  var coupon = document.getElementById("coupon-button");
  if (coupon) coupon.addEventListener("click", function () {
    if (!s) return;
    var code = document.getElementById("coupon-input").value.trim().toUpperCase();
    var note = document.getElementById("coupon-note");
    if (code === STORE.coupon.code) {
      s.coupon = true; save(s); renderOrder("cart");
      note.textContent = STORE.coupon.message;
    } else {
      note.textContent = "That code is not valid.";
    }
  });
}

function initCheckPage(pageName, checkId, stateKey) {
  var s = load();
  if (!s) { renderOrder(pageName); return; }
  var chk = document.getElementById(checkId);
  chk.checked = !!s[stateKey];
  chk.addEventListener("change", function () { s[stateKey] = chk.checked; save(s); renderOrder(pageName); });
  renderOrder(pageName);
  document.getElementById("next-button").addEventListener("click", function () { location.href = STORE.next[pageName]; });
}

function initAddress() {
  renderOrder("address");
  document.getElementById("next-button").addEventListener("click", function () { location.href = STORE.next.address; });
}

function initOptions() {
  var s = load();
  if (!s) { renderOrder("options"); return; }
  var sel = document.getElementById("delivery-select");
  if (!s.delivery && STORE.delivery.default) { s.delivery = STORE.delivery.default; save(s); }
  sel.value = s.delivery || "";
  sel.addEventListener("change", function () { s.delivery = sel.value || null; save(s); renderOrder("options"); });
  var mem = document.getElementById("membership-check");
  if (mem) {
    mem.checked = !!s.membership;
    mem.addEventListener("change", function () { s.membership = mem.checked; save(s); renderOrder("options"); });
  }
  renderOrder("options");
  document.getElementById("next-button").addEventListener("click", function () {
    if (!s.delivery) { notice("Please choose a delivery option."); return; }
    location.href = STORE.next.options;
  });
}

function initSummary() {
  var t = renderOrder("summary");
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
else if (PAGE === "gift") initCheckPage("gift", "gift-check", "gift");
else if (PAGE === "protection") initCheckPage("protection", "protection-check", "protection");
else if (PAGE === "address") initAddress();
else if (PAGE === "options") initOptions();
else if (PAGE === "summary") initSummary();
else if (PAGE === "pay") renderOrder("pay");
"""


def app_js(s):
    e = s["extras"]
    pages = s["pages"]
    nxt = {pages[i]: f"{pages[i + 1]}.html" for i in range(1, len(pages) - 1)}
    cfg = {
        "storageKey": s["storage_key"],
        "words": s["words"],
        "pages": pages,
        "next": nxt,
        "product": {"name": s["product"]["name"], "price": s["product"]["price"]},
        "quantity": bool(s["quantity"]),
        "delivery": {"default": s["delivery"]["default"], "options": s["delivery"]["options"]},
        "addonOffer": e.get("addon_offer"),
        "gift": ({"label": e["gift_page"]["label"], "amount": e["gift_page"]["amount"]} if "gift_page" in e else None),
        "protection": ({"label": e["protection_page"]["label"], "amount": e["protection_page"]["amount"]}
                       if "protection_page" in e else None),
        "membership": ({"label": e["membership"]["label"], "amount": e["membership"]["amount"]} if "membership" in e else None),
        "coupon": ({"code": e["coupon_box"]["code"], "label": e["coupon_box"]["label"], "amount": e["coupon_box"]["amount"],
                    "message": e["coupon_box"]["message"]} if "coupon_box" in e else None),
        "summaryCharge": e.get("summary_charge"),
    }
    return "var STORE = " + json.dumps(cfg, ensure_ascii=False, indent=2) + ";\n" + JS_BODY


COMMON_CSS = """
.hint { color: #777; font-style: italic; margin-left: 8px; }
.coupon-row input { font-size: 15px; padding: 4px; width: 120px; }
.addon-row { margin: 14px 0; }
"""

LAYOUT_CSS = {
    "rail": """.shell { max-width: 680px; }
.rail ol { display: flex; flex-wrap: wrap; gap: 6px; list-style: none; margin: 0 0 18px; padding: 0; }
.rail li { padding: 5px 12px; border: 1px solid #b0bec5; border-radius: 14px; font-size: 13px; background: #eceff1; }
.rail li.active { background: #455a64; color: #fff; border-color: #455a64; }
.order-box { border-left: 5px solid #546e7a; }""",
    "boxed": """.shell { max-width: 900px; }
.boxed-wrap { display: grid; grid-template-columns: 3fr 2fr; gap: 20px; border: 3px double #c2185b; padding: 16px; background: #fff; }
.boxed-wrap .order-box { margin: 0; border-style: dashed; }
.product { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; border: 3px double #c2185b; padding: 16px; background: #fff; }
button { border-radius: 20px; }""",
    "stacked": """.shell { max-width: 720px; }
.content { background: #fff; padding: 16px; border-radius: 8px; }
.order-box { margin-top: 24px; border: 0; border-top: 4px solid #0288d1; border-radius: 0 0 8px 8px; }
.product { display: grid; grid-template-columns: 1fr 2fr; gap: 20px; background: #fff; padding: 16px; border-radius: 8px; }""",
    "ledger": """.shell { max-width: 640px; }
.order-box, .price-lines { border: 1px dashed #333; background: #f9fbe7; }
.line { border-bottom: 1px dotted #999; }
.line.total { border-top: 2px solid #333; padding-top: 8px; }
h1 { text-transform: uppercase; letter-spacing: 1px; font-size: 20px; }
button { text-transform: uppercase; }""",
}


def style_css(s):
    c = s["colours"]
    return CSS.substitute(font=c["font"], page=c["page"], header=c["header"], header_text=c["header_text"],
                          accent=c["accent"], layout=LAYOUT_CSS[s["layout"]] + COMMON_CSS)


# ---------- answer key ----------

def build_key(s):
    e = s["extras"]
    d = s["delivery"]
    chosen_opt = next(o for o in d["options"] if o["id"] == s["task_choice"]["delivery"])
    upfront, chosen, traps = [], [], []
    if d["shown_upfront"]:
        upfront.append({"label": "Delivery", "amount": chosen_opt["amount"]})
    else:
        chosen.append({"label": chosen_opt["line"], "amount": chosen_opt["amount"]})
    if "gift_page" in e:
        x = e["gift_page"]
        traps.append({"type": "pre_ticked_addon", "label": x["label"], "amount": x["amount"], "scored": True, "pattern": "basket sneaking"})
    if "protection_page" in e:
        x = e["protection_page"]
        traps.append({"type": "pre_ticked_addon", "label": x["label"], "amount": x["amount"], "scored": True, "pattern": "basket sneaking"})
    if "summary_charge" in e:
        x = e["summary_charge"]
        traps.append({"type": "drip_fee", "label": x["label"], "amount": x["amount"], "scored": True, "pattern": "drip pricing"})
    if "membership" in e:
        x = e["membership"]
        traps.append({"type": "subscription_trap", "label": x["key_label"], "amount": x["amount"], "scored": True,
                      "pattern": "subscription trap", "in_total": False})
    if "addon_offer" in e:
        x = e["addon_offer"]
        traps.append({"type": "upsell_popup", "label": x["label"], "amount": x["amount"], "scored": False, "pattern": "nagging"})
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


# ---------- main ----------

def check_neutral_extra(folder):
    pattern = re.compile("|".join(re.escape(w) for w in FORBIDDEN_WORDS + EXTRA_FORBIDDEN), re.IGNORECASE)
    for f in folder.rglob("*"):
        if f.is_file():
            hit = pattern.search(f.read_text(encoding="utf-8")) or pattern.search(f.name)
            if hit:
                raise SystemExit(f"non-neutral word {hit.group(0)!r} in {f}")


def write_store(s):
    out = WWW / s["id"]
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    e = s["extras"]
    (out / "index.html").write_text(product_page(s), encoding="utf-8")
    (out / "cart.html").write_text(cart_page(s), encoding="utf-8")
    if "gift_page" in e:
        (out / "gift.html").write_text(check_page(s, "gift", e["gift_page"], "gift-check"), encoding="utf-8")
    if "protection_page" in e:
        (out / "protection.html").write_text(check_page(s, "protection", e["protection_page"], "protection-check"), encoding="utf-8")
    if "address_page" in e:
        (out / "address.html").write_text(address_page(s), encoding="utf-8")
    (out / "options.html").write_text(options_page(s), encoding="utf-8")
    (out / "summary.html").write_text(summary_page(s), encoding="utf-8")
    (out / "pay.html").write_text(pay_page(s), encoding="utf-8")
    (out / "app.js").write_text(app_js(s), encoding="utf-8")
    (out / "style.css").write_text(style_css(s), encoding="utf-8")
    written = sorted(f.name for f in out.glob("*.html"))
    expected_pages = sorted(f"{p}.html" for p in s["pages"])
    if written != expected_pages:
        raise SystemExit(f"{s['id']}: pages on disk {written} differ from config {expected_pages}")
    check_neutral(out)
    check_neutral_extra(out)
    return out


def main():
    KEYS.mkdir(parents=True, exist_ok=True)
    for s in STORES:
        out = write_store(s)
        key = build_key(s)
        (KEYS / f"{s['id']}.json").write_text(json.dumps(key, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{s['id']} {s['name']}: {len(s['pages'])} pages, expected_final_total={key['expected_final_total']} -> {out}")
    print(f"wrote {', '.join(s['id'] for s in STORES)} under {WWW} and {KEYS}; nothing else was touched")


if __name__ == "__main__":
    main()
