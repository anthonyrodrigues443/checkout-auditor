#!/usr/bin/env python3
"""Generate the practice stores L17-L20 and their answer keys.

Usage: python stores/gen4.py
Writes stores/www/l17 .. l20 (the served root) and stores/keys/l17.json .. l20.json (outside
the served root). Only those four folders and four key files are touched; re-running overwrites
them and nothing else (checked with a hash snapshot of every other store plus git diff at the
end). Page shells, the cart, options, pay and plain product pages and the base CSS come from
stores/gen.py; the pages the new mechanics need, the script and the key builder live here.

What each store adds on top of the product -> cart -> options -> summary -> pay flow:
  l17  a "Delivery zone" select on the options page whose default is the paid "Outside Mumbai"
       option while the pre-filled address says Mumbai 400050; the product page said delivery
       is free within Mumbai. Left as found, the summary carries "Delivery (outside Mumbai)".
  l18  the product page says "₹1,000 + taxes" and no tax amount appears before the summary,
       which adds "GST (18%)" and a pre-ticked "Tip your delivery partner" box on the summary
       page itself, included in the total.
  l19  a long product page (specs, care, reviews, FAQ, a compare table of three other products
       with their own prices) with the real price block only at the end; the cart's Continue
       leads to a "Before you go" page offering an extended warranty (declining goes on to
       options); the summary adds a "Handling" line never shown before. Six pages.
  l20  "MRP" struck through next to a sale price on the product page, the cart charges the sale
       price, the summary charges the MRP with a small note; plus an un-ticked gift wrap box on
       options and a pre-filled coupon box on the cart, neither of which changes anything.

Key invariant: first_price + upfront_charges + chosen_options + amounts of scored traps whose
in_total is not false == expected_final_total.
"""
import hashlib
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
    cart_page, check_neutral, flow_page, money, options_page, page, pay_page, product_page,
)

MY_STORES = ["l17", "l18", "l19", "l20"]

STORES = [
    {
        "id": "l17", "level": 17, "name": "Tamba Home",
        "storage_key": "tambahome_tray",
        "words": {"cart": "tray", "add": "Add to tray", "next": "Proceed to delivery", "pay": "Pay securely"},
        "colours": {"header": "#b87333", "header_text": "#fff", "accent": "#8c4a1c", "page": "#fdf8f3",
                    "font": "Hoefler Text, Garamond, Georgia, serif"},
        "layout": "card",
        "product": {"name": "Copper Water Bottle 1 L", "price": 850,
                    "blurb": "Hand-beaten pure copper bottle, 1 litre, leak-proof screw cap.",
                    "note": "Delivery: free within Mumbai"},
        "sizes": None,
        "fixed_charges": [],
        "delivery": {
            "shown_upfront": False, "placeholder": None, "default": "standard",
            "options": [
                {"id": "standard", "text": "Standard – Free", "line": "Standard delivery", "amount": 0},
                {"id": "express", "text": "Express ₹90", "line": "Express delivery", "amount": 90},
            ],
        },
        "extras": {
            "zone": {
                "label": "Delivery zone", "default": "outside",
                "options": [
                    {"id": "mumbai", "text": "Mumbai – Free", "line": "Delivery (Mumbai)", "amount": 0},
                    {"id": "outside", "text": "Outside Mumbai ₹80", "line": "Delivery (outside Mumbai)", "amount": 80},
                ],
            },
        },
        "task": "Buy one 1 L copper water bottle with standard delivery.",
        "task_choice": {"size": None, "delivery": "standard"},
    },
    {
        "id": "l18", "level": 18, "name": "Bulb Street",
        "storage_key": "bulbstreet_order",
        "words": {"cart": "order", "add": "Add to order", "next": "Review order", "pay": "Confirm purchase"},
        "colours": {"header": "#0d47a1", "header_text": "#fff", "accent": "#1565c0", "page": "#f3f6fb",
                    "font": "Lucida Grande, Lucida Sans Unicode, sans-serif"},
        "layout": "tabs",
        "product": {"name": "Foldable LED Desk Lamp", "price": 1000,
                    "blurb": "Three-fold LED lamp with five brightness steps and a USB-C port.",
                    "note": None},
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
            "taxes": {"suffix": "+ taxes", "label": "GST (18%)", "amount": 180},
            "tip": {"label": "Tip your delivery partner", "amount": 20},
        },
        "task": "Buy one foldable LED desk lamp with standard delivery.",
        "task_choice": {"size": None, "delivery": "standard"},
    },
    {
        "id": "l19", "level": 19, "name": "Decibel Depot",
        "storage_key": "decibeldepot_haul",
        "words": {"cart": "haul", "add": "Add to haul", "next": "Continue", "pay": "Place order and pay"},
        "colours": {"header": "#1a237e", "header_text": "#e8eaf6", "accent": "#283593", "page": "#f5f5fa",
                    "font": "Arial Narrow, Arial, sans-serif"},
        "layout": "article",
        "product": {"name": "Portable Bluetooth Speaker 20 W", "price": 1750,
                    "blurb": "Two-driver 20 W speaker with a passive radiator, IPX5 shell and a 14 hour battery.",
                    "note": None},
        "sizes": None,
        "fixed_charges": [],
        "delivery": {
            "shown_upfront": True, "placeholder": None, "default": "standard",
            "options": [
                {"id": "standard", "text": "Standard ₹45", "line": "Delivery", "amount": 45},
                {"id": "express", "text": "Express ₹120", "line": "Express delivery", "amount": 120},
            ],
        },
        "extras": {
            "long_page": True,
            "interstitial": {"heading": "Before you go", "label": "Extended warranty", "amount": 199,
                             "text": "Two more years of cover on top of the maker's twelve months. "
                                     "Battery, charging port and driver faults are all included.",
                             "yes": "Add warranty", "no": "No, continue"},
            "summary_charge": {"label": "Handling", "amount": 25},
        },
        "task": "Buy one 20 W portable Bluetooth speaker with standard delivery.",
        "task_choice": {"size": None, "delivery": "standard"},
    },
    {
        "id": "l20", "level": 20, "name": "Linen Loft",
        "storage_key": "linenloft_picks",
        "words": {"cart": "picks", "add": "Add to picks", "next": "Go on", "pay": "Pay for order"},
        "colours": {"header": "#ad1457", "header_text": "#fff", "accent": "#c2185b", "page": "#fff5f8",
                    "font": "Seravek, Candara, Calibri, sans-serif"},
        "layout": "boxed",
        "product": {"name": "Cotton Bedsheet Set (Double)", "price": 999,
                    "blurb": "Double bedsheet with two pillow covers, 144 thread count cotton, block print.",
                    "note": None},
        "sizes": None,
        "fixed_charges": [],
        "delivery": {
            "shown_upfront": True, "placeholder": None, "default": "standard",
            "options": [
                {"id": "standard", "text": "Standard ₹40", "line": "Delivery", "amount": 40},
                {"id": "express", "text": "Express ₹110", "line": "Express delivery", "amount": 110},
            ],
        },
        "extras": {
            "mrp": {"amount": 1299, "note": "Sale price applies at payment"},
            "wrap_box": {"label": "Gift wrap", "amount": 30},
            "coupon_box": {"code": "FIRST50", "button": "Apply", "message": "Code will be checked at payment"},
        },
        "task": "Buy one double cotton bedsheet set with standard delivery.",
        "task_choice": {"size": None, "delivery": "standard"},
    },
]

# Words that would give the mechanics away, on top of gen.py's list. Checked as substrings, so
# the copy below avoids "failure" (lure), "manage" (nag), "strap" (trap) and the like.
EXTRA_FORBIDDEN = ["bait", "nag", "lure", "undisclosed", "interstitial", "preselect", "pre-select",
                   "wrong", "switch", "sneaky", "surprise"]


# ---------- page pieces ----------

def address_block():
    return f'<div class="address"><strong>Deliver to</strong><br>{ADDRESS}<br>{CONTACT}</div>'


def delivery_select(s):
    d = s["delivery"]
    opts = ""
    if d["placeholder"]:
        opts += f'<option value="">{d["placeholder"]}</option>'
    for o in d["options"]:
        sel = " selected" if o["id"] == d["default"] else ""
        opts += f'<option value="{o["id"]}"{sel}>{o["text"]}</option>'
    return f'<p><label>Delivery <select id="delivery-select">{opts}</select></label></p>'


def zone_options_page(s):
    z = s["extras"]["zone"]
    opts = ""
    for o in z["options"]:
        sel = " selected" if o["id"] == z["default"] else ""
        opts += f'<option value="{o["id"]}"{sel}>{o["text"]}</option>'
    parts = [address_block(),
             delivery_select(s),
             f'<p><label>{z["label"]} <select id="zone-select">{opts}</select></label></p>',
             "ORDER", '<p id="notice" class="notice"></p>',
             f'<p><button id="next-button" type="button">{s["words"]["next"]}</button></p>']
    return flow_page(s, "options", f"Delivery options – {s['name']}", "Delivery and address", parts)


def wrap_options_page(s):
    wb = s["extras"]["wrap_box"]
    parts = [delivery_select(s),
             f'<p class="addon-row"><label><input type="checkbox" id="wrap-check"> {wb["label"]} {money(wb["amount"])}</label></p>',
             address_block(), "ORDER", '<p id="notice" class="notice"></p>',
             f'<p><button id="next-button" type="button">{s["words"]["next"]}</button></p>']
    return flow_page(s, "options", f"Delivery options – {s['name']}", "Delivery and address", parts)


def taxes_product_page(s):
    p, t = s["product"], s["extras"]["taxes"]
    d = next(o for o in s["delivery"]["options"] if o["id"] == s["delivery"]["default"])
    body = f"""<section class="product">
  <div class="product-image">{p['name']}</div>
  <div class="product-info">
  <h1>{p['name']}</h1>
  <p class="blurb">{p['blurb']}</p>
  <p class="price">Price {money(p['price'])} {t['suffix']}</p>
  <div class="price-lines">
    <div class="line"><span>Delivery</span><span>{money(d['amount'])}</span></div>
  </div>
  <p id="notice" class="notice"></p>
  <button id="add-button" type="button">{s['words']['add']}</button>
  </div>
</section>"""
    return page(s, "index", f"{p['name']} – {s['name']}", body)


def mrp_product_page(s):
    p, m = s["product"], s["extras"]["mrp"]
    d = next(o for o in s["delivery"]["options"] if o["id"] == s["delivery"]["default"])
    body = f"""<section class="product">
  <div class="product-image">{p['name']}</div>
  <div class="product-info">
  <h1>{p['name']}</h1>
  <p class="blurb">{p['blurb']}</p>
  <p class="price"><span class="strike">MRP {money(m['amount'])}</span> <span class="sale">Sale price {money(p['price'])}</span></p>
  <div class="price-lines">
    <div class="line"><span>Price</span><span>{money(p['price'])}</span></div>
    <div class="line"><span>Delivery</span><span>{money(d['amount'])}</span></div>
    <div class="line total"><span>Total</span><span>{money(p['price'] + d['amount'])}</span></div>
  </div>
  <p id="notice" class="notice"></p>
  <button id="add-button" type="button">{s['words']['add']}</button>
  </div>
</section>"""
    return page(s, "index", f"{p['name']} – {s['name']}", body)


# ---------- the long product page (l19) ----------

SPEAKER_INTRO = [
    "The 20 W portable speaker is built for balconies, kitchens and weekend trips. Two full-range drivers and a "
    "passive radiator give it more low end than its size suggests, and the fabric front keeps the look calm enough "
    "to leave on a shelf. It pairs over Bluetooth 5.3 in a couple of seconds and remembers the last four devices, so "
    "a phone and a laptop can hand over to each other without pairing again.",
    "The battery runs for about 14 hours at half volume and recharges over USB-C in under three hours. A rubber foot "
    "stops it sliding on smooth counters, and the IPX5 rating means a splash from the sink or a light shower on a "
    "picnic is not a problem. Two units can be linked for stereo, and a 3.5 mm input is there for older players.",
    "Buttons on the top handle power, pairing, volume and play or pause. The voice prompts can be muted from the "
    "companion app, which also holds a five-band equaliser and a firmware updater. The speaker ships with a USB-C "
    "cable, a short printed guide and a cloth pouch.",
    "We tested it against six speakers in the same price band over two weeks of kitchen, balcony and beach use. "
    "It was not the loudest of the six, but it was the only one that kept its bass tight at three-quarter volume, "
    "and the only one whose port cover survived a week in a sandy bag without letting grit in. The fabric picks up "
    "less dust than the rubber shells of the others and wipes clean in seconds.",
]

SPEAKER_WHY = [
    "Bass that holds together: the passive radiator does the low end so the drivers stay clean on vocals.",
    "Real battery numbers: our 14 hour figure is at half volume with the app's flat equaliser, not a lab setting.",
    "Sturdy port cover: a proper hinge with a rubber seal, not a flap that tears off after a month.",
    "Four device memory: a phone, a laptop, a tablet and a partner's phone all reconnect without pairing again.",
]

SPEAKER_SPECS = [
    ("Drivers", "2 × 45 mm full-range plus one passive radiator"),
    ("Output", "20 W RMS"),
    ("Frequency response", "60 Hz to 20 kHz"),
    ("Bluetooth", "5.3, about 10 m of range"),
    ("Codecs", "SBC, AAC"),
    ("Inputs", "USB-C for charging, 3.5 mm aux"),
    ("Battery", "3,600 mAh lithium-ion"),
    ("Playtime", "About 14 hours at half volume"),
    ("Charge time", "2.5 hours with a 10 W adapter"),
    ("Water rating", "IPX5"),
    ("Weight", "640 g"),
    ("Size", "18 cm × 7 cm × 7 cm"),
    ("Colours", "Sand, Moss, Slate"),
    ("Microphone", "Built in, for calls"),
    ("Stereo pairing", "Yes, two units"),
    ("Maker's warranty", "12 months"),
    ("In the box", "Speaker, USB-C cable, cloth pouch, quick guide"),
    ("Made in", "Vietnam"),
]

SPEAKER_CARE = [
    "Wipe the fabric front with a dry cloth. For marks, use a cloth dampened with plain water and let it air dry "
    "before the next use.",
    "Do not submerge the speaker. IPX5 covers splashes and rain, not a dip in the pool or a run under the tap.",
    "Close the port cover after charging. The water rating only holds while the cover is shut.",
    "Charge with a 5 V adapter of 10 W or more. Fast chargers are fine, the speaker only draws what it needs.",
    "Store it between 0 °C and 40 °C. A parked car in May will shorten the battery's life noticeably.",
    "If the speaker will sit unused for a month or more, charge it to about half first and top it up every "
    "three months.",
    "Keep it away from open flames and room heaters. The shell is plastic and the radiator membrane is rubber.",
]

SPEAKER_REVIEWS = [
    ("Rhea", "Pune", 5, "Bought it for the kitchen and it lives there now. Loud enough over the exhaust fan, and the "
                        "battery has lasted a full week of cooking podcasts on one charge."),
    ("Ganesh", "Nashik", 4, "Good bass for the size. Pairing with my laptop was instant and it remembered my phone "
                            "too. Only wish it came in a brighter colour than the three on offer."),
    ("Priya", "Thane", 5, "Took it to Alibaug for the weekend, got caught in the rain on the beach, still playing. "
                          "The pouch is thin but it does the job in a backpack."),
    ("Farhan", "Bandra", 4, "Sound is clean at normal volumes. Pushed to full it gets a bit harsh on vocals. For a "
                            "balcony or a small room it is close to perfect."),
    ("Meera", "Kalyan", 3, "Works as described. The voice prompt when it turns on is loud and I had to dig through "
                           "the app to find the setting that turns it off."),
    ("Sunil", "Borivali", 5, "Second one I have bought, this time for my father. Stereo pairing with the first one "
                             "took two taps and the app labels left and right clearly."),
    ("Anjali", "Navi Mumbai", 4, "Charges quickly and the port cover feels sturdy. It is heavier than it looks in the "
                                 "photos, which I actually like, it does not tip over."),
    ("Kabir", "Dadar", 5, "Replaced a much pricier speaker that died after a year. This one is smaller and sounds "
                          "nearly as good. Calls are clear too, the person on the other end could not tell."),
]

SPEAKER_FAQ = [
    ("Can I use it while it is charging?",
     "Yes. Playback carries on while the USB-C cable is connected, and charging just takes a little longer."),
    ("Does it work with an iPhone?",
     "Yes. It pairs with any phone, tablet or laptop that has Bluetooth. The companion app is on both app stores."),
    ("How do I pair two speakers for stereo?",
     "Turn both on, hold the pairing button on the first for three seconds until it blinks blue, then press the "
     "pairing button on the second once. The app shows which one is left and which is right."),
    ("Is the battery replaceable?",
     "Not by the user. Service centres can fit a new one for a fee once the maker's warranty has ended."),
    ("Can I take calls on it?",
     "Yes. There is a microphone on the top. Press the play button once to answer and once more to hang up."),
    ("What is the range?",
     "About 10 metres with a clear line of sight. Walls and people in between reduce it."),
    ("Does it come with a charger?",
     "A USB-C cable is included. Use any phone charger with a USB port, or a laptop."),
    ("What if it arrives damaged?",
     "Photograph the box before opening it and write to us within 48 hours. We send a replacement and collect "
     "the damaged unit from you."),
    ("Can it play from a laptop and a phone at the same time?",
     "It stays connected to two devices at once and plays whichever one is sending audio. Pause on one and press "
     "play on the other to hand over."),
    ("How loud is it really?",
     "About 86 dB at one metre at full volume, which fills a 15 square metre room comfortably. Outdoors it carries "
     "across a small garden or a picnic mat but not a beach party."),
]

SPEAKER_SETUP = [
    "Charge the speaker fully before the first use. The light on the top turns green when it is done.",
    "Hold the power button for two seconds. The speaker plays a short tone and the light blinks blue.",
    "Open Bluetooth settings on your phone and pick the speaker from the list. It shows up under its model name.",
    "Play something. Use the volume buttons on the speaker or on your phone, both work.",
    "Install the companion app if you want the equaliser, the voice prompt setting or firmware updates.",
]

SPEAKER_COMPARE = [
    ("Mini Speaker 5 W", 1299, "8 h", "IPX4", "280 g"),
    ("Bass Speaker 40 W", 2499, "12 h", "IPX5", "1.2 kg"),
    ("Outdoor Speaker 30 W", 1999, "20 h", "IPX7", "900 g"),
]

SPEAKER_DELIVERY = (
    "Standard delivery reaches most Mumbai pin codes in two to three working days and the rest of Maharashtra in "
    "four to five. Express orders placed before noon go out the same day. Unopened units can be returned within "
    "ten days for a full refund; opened units within seven days if they are faulty. Pickups are arranged from the "
    "delivery address, there is nothing to post."
)


def long_product_page(s):
    p = s["product"]
    d = next(o for o in s["delivery"]["options"] if o["id"] == s["delivery"]["default"])
    intro = "".join(f"<p>{t}</p>" for t in SPEAKER_INTRO)
    specs = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in SPEAKER_SPECS)
    care = "".join(f"<li>{t}</li>" for t in SPEAKER_CARE)
    why = "".join(f"<li>{t}</li>" for t in SPEAKER_WHY)
    setup = "".join(f"<li>{t}</li>" for t in SPEAKER_SETUP)
    reviews = "".join(
        f'<div class="review"><strong>{name}, {city}</strong> · {"★" * stars}{"☆" * (5 - stars)}<p>{text}</p></div>'
        for name, city, stars, text in SPEAKER_REVIEWS)
    faq = "".join(f"<dt>{q}</dt><dd>{a}</dd>" for q, a in SPEAKER_FAQ)
    compare_head = "".join(f"<th>{name}</th>" for name, *_ in SPEAKER_COMPARE)
    compare_rows = ""
    for label, idx in (("Price", 1), ("Playtime", 2), ("Water rating", 3), ("Weight", 4)):
        cells = "".join(f"<td>{money(row[idx]) if idx == 1 else row[idx]}</td>" for row in SPEAKER_COMPARE)
        compare_rows += f"<tr><th>{label}</th>{cells}</tr>"
    body = f"""<section class="product">
  <div class="product-image">{p['name']}</div>
  <h1>{p['name']}</h1>
  <p class="blurb">{p['blurb']}</p>
  {intro}
  <h2>Why we picked it</h2>
  <ul>{why}</ul>
  <h2>Specifications</h2>
  <table class="specs">{specs}</table>
  <h2>Setting it up</h2>
  <ol>{setup}</ol>
  <h2>Care instructions</h2>
  <ul>{care}</ul>
  <h2>Customer reviews</h2>
  {reviews}
  <h2>Questions and answers</h2>
  <dl class="faq">{faq}</dl>
  <h2>Delivery and returns</h2>
  <p>{SPEAKER_DELIVERY}</p>
  <h2>Compare with similar items</h2>
  <table class="compare"><tr><th></th>{compare_head}</tr>{compare_rows}</table>
  <h2>Buy this speaker</h2>
  <div id="price-block" class="price-lines">
    <div class="line"><span>Price</span><span>{money(p['price'])}</span></div>
    <div class="line"><span>Delivery</span><span>{money(d['amount'])}</span></div>
    <div class="line total"><span>Total</span><span>{money(p['price'] + d['amount'])}</span></div>
  </div>
  <p id="notice" class="notice"></p>
  <button id="add-button" type="button">{s['words']['add']}</button>
</section>"""
    return page(s, "index", f"{p['name']} – {s['name']}", body)


def visible_text_before_price(html):
    head = html.split("<main", 1)[1].split('id="price-block"', 1)[0]
    return len(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", head)).strip())


def before_page(s):
    it = s["extras"]["interstitial"]
    parts = [f"""<div class="offer-card">
  <h2>{it['label']} {money(it['amount'])}</h2>
  <p>{it['text']}</p>
  <p><button id="warranty-button" type="button">{it['yes']}</button> <button id="continue-button" type="button">{it['no']}</button></p>
</div>""", "ORDER"]
    return flow_page(s, "before", f"{it['heading']} – {s['name']}", it["heading"], parts)


# ---------- summary pages ----------

def summary_page(s):
    e = s["extras"]
    parts = [address_block()]
    if "tip" in e:
        parts.append(f'<p class="addon-row"><label><input type="checkbox" id="tip-check" checked> '
                     f'{e["tip"]["label"]} {money(e["tip"]["amount"])}</label></p>')
    if "mrp" in e:
        parts.append(f"""<aside class="order-box">
  <h2>Order summary</h2>
  <div id="order-lines"></div>
  <p class="small">{e['mrp']['note']}</p>
  <div class="line total"><span>Total</span><span id="order-total"></span></div>
</aside>""")
    else:
        parts.append("ORDER")
    parts.append(f'<p><button id="pay-button" type="button" data-pay>{s["words"]["pay"]}</button></p>')
    return flow_page(s, "summary", f"Review your order – {s['name']}", "Review your order", parts)


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
function pick(opts, id) {
  for (var i = 0; i < opts.length; i++) if (opts[i].id === id) return opts[i];
  return null;
}
function deliveryChoice(s) { return pick(STORE.delivery.options, s.delivery || STORE.delivery.default); }
function zoneChoice(s) { return STORE.zone ? pick(STORE.zone.options, s.zone) : null; }
function reviewPage(pageName) { return pageName === "summary" || pageName === "pay"; }

function productLine(s, pageName) {
  var amount = STORE.product.price;
  if (STORE.listPrice && reviewPage(pageName)) amount = STORE.listPrice.amount;
  return {label: STORE.product.name + (s.size ? " (size " + s.size + ")" : ""), amount: amount};
}

function orderLines(s, pageName) {
  var out = [productLine(s, pageName)];
  STORE.fixedCharges.forEach(function (c) { out.push(c); });
  if (STORE.warranty && s.warranty) out.push(STORE.warranty);
  if (STORE.wrap && s.wrap && pageName !== "cart") out.push(STORE.wrap);
  var d = deliveryChoice(s);
  if (d) out.push({label: d.line, amount: d.amount});
  var z = zoneChoice(s);
  if (z && pageName !== "cart") out.push({label: z.line, amount: z.amount});
  if (reviewPage(pageName)) {
    if (STORE.taxes) out.push(STORE.taxes);
    if (STORE.summaryCharge) out.push(STORE.summaryCharge);
    if (STORE.tip && s.tip) out.push(STORE.tip);
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
  var t = lines.reduce(function (a, l) { return a + l.amount; }, 0);
  if (tot) tot.textContent = money(t);
  return t;
}

function initProduct() {
  var sizeSel = document.getElementById("size-select");
  document.getElementById("add-button").addEventListener("click", function () {
    var size = sizeSel ? sizeSel.value : null;
    if (sizeSel && !size) { notice("Please choose a size first."); return; }
    save({qty: 1, size: size || null, delivery: null, zone: STORE.zone ? STORE.zone.default : null,
          warranty: false, wrap: false, tip: !!STORE.tip});
    location.href = "cart.html";
  });
}

function initCart() {
  renderOrder("cart");
  var coupon = document.getElementById("coupon-button");
  if (coupon) coupon.addEventListener("click", function () {
    document.getElementById("coupon-note").textContent = STORE.coupon.message;
  });
  document.getElementById("next-button").addEventListener("click", function () {
    location.href = STORE.warranty ? "before.html" : "options.html";
  });
}

function initBefore() {
  var s = load();
  renderOrder("before");
  function go(add) {
    if (s) { s.warranty = add; save(s); }
    location.href = "options.html";
  }
  document.getElementById("warranty-button").addEventListener("click", function () { go(true); });
  document.getElementById("continue-button").addEventListener("click", function () { go(false); });
}

function initOptions() {
  var s = load();
  if (!s) { renderOrder("options"); return; }
  var sel = document.getElementById("delivery-select");
  if (!s.delivery && STORE.delivery.default) { s.delivery = STORE.delivery.default; save(s); }
  sel.value = s.delivery || "";
  sel.addEventListener("change", function () { s.delivery = sel.value || null; save(s); renderOrder("options"); });
  var zoneSel = document.getElementById("zone-select");
  if (zoneSel) {
    if (!s.zone && STORE.zone.default) { s.zone = STORE.zone.default; save(s); }
    zoneSel.value = s.zone || "";
    zoneSel.addEventListener("change", function () { s.zone = zoneSel.value || null; save(s); renderOrder("options"); });
  }
  var wrap = document.getElementById("wrap-check");
  if (wrap) {
    wrap.checked = !!s.wrap;
    wrap.addEventListener("change", function () { s.wrap = wrap.checked; save(s); renderOrder("options"); });
  }
  renderOrder("options");
  document.getElementById("next-button").addEventListener("click", function () {
    if (!s.delivery) { notice("Please choose a delivery option."); return; }
    location.href = "summary.html";
  });
}

function initSummary() {
  var s = load();
  var buttons = document.querySelectorAll("[data-pay]");
  var labels = Array.prototype.map.call(buttons, function (b) { return b.textContent; });
  function paint() {
    var t = renderOrder("summary");
    Array.prototype.forEach.call(buttons, function (b, i) { b.textContent = labels[i].replace("{total}", money(t)); });
  }
  var tip = document.getElementById("tip-check");
  if (tip && s) {
    tip.checked = !!s.tip;
    tip.addEventListener("change", function () { s.tip = tip.checked; save(s); paint(); });
  }
  paint();
  Array.prototype.forEach.call(buttons, function (b) {
    b.addEventListener("click", function () {
      localStorage.setItem("pay_clicked", "true");
      location.href = "pay.html";
    });
  });
}

var PAGE = document.body.getAttribute("data-page");
if (PAGE === "index") initProduct();
else if (PAGE === "cart") initCart();
else if (PAGE === "before") initBefore();
else if (PAGE === "options") initOptions();
else if (PAGE === "summary") initSummary();
else if (PAGE === "pay") renderOrder("pay");
"""


def app_js(s):
    e = s["extras"]
    cfg = {
        "storageKey": s["storage_key"],
        "words": s["words"],
        "product": {"name": s["product"]["name"], "price": s["product"]["price"]},
        "fixedCharges": s["fixed_charges"],
        "delivery": {"default": s["delivery"]["default"], "options": s["delivery"]["options"]},
        "zone": ({"default": e["zone"]["default"], "options": e["zone"]["options"]} if "zone" in e else None),
        "taxes": ({"label": e["taxes"]["label"], "amount": e["taxes"]["amount"]} if "taxes" in e else None),
        "tip": e.get("tip"),
        "warranty": ({"label": e["interstitial"]["label"], "amount": e["interstitial"]["amount"]}
                     if "interstitial" in e else None),
        "summaryCharge": e.get("summary_charge"),
        "listPrice": ({"amount": e["mrp"]["amount"]} if "mrp" in e else None),
        "wrap": e.get("wrap_box"),
        "coupon": ({"message": e["coupon_box"]["message"]} if "coupon_box" in e else None),
    }
    return "var STORE = " + json.dumps(cfg, ensure_ascii=False, indent=2) + ";\n" + JS_BODY


EXTRA_CSS = """
.small { font-size: 13px; color: #555; margin: 6px 0; }
.strike { text-decoration: line-through; color: #777; font-weight: normal; font-size: 16px; }
.sale { color: $accent; }
.offer-card { border: 2px solid $accent; background: #fff; padding: 16px 20px; margin-bottom: 16px; }
.offer-card h2 { margin-top: 0; }
"""

LAYOUT_CSS = {
    "card": """.shell { max-width: 640px; }
.site-header { justify-content: center; gap: 28px; letter-spacing: 1px; }
.content, .product, .order-box, .price-lines, .address { border: 0; border-radius: 10px; box-shadow: 0 1px 5px rgba(0,0,0,.14); background: #fff; }
.product, .content { padding: 18px; }
.product-image { border-radius: 8px; }
button { border-radius: 6px; }
select { border-radius: 4px; }""",
    "tabs": """.site-header { border-bottom: 4px solid #ffb300; }
.shell { max-width: 820px; }
h1 { font-size: 20px; text-transform: uppercase; letter-spacing: 1px; border-bottom: 1px solid #c5cae9; padding-bottom: 6px; }
.order-box { border: 2px solid #0d47a1; }
.product { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.addon-row { background: #fff8e1; border: 1px solid #ffe082; padding: 10px 14px; }""",
    "article": """.shell { max-width: 720px; line-height: 1.6; }
h2 { font-size: 18px; margin: 28px 0 8px; border-bottom: 1px solid #c5cae9; }
table { border-collapse: collapse; width: 100%; margin: 12px 0; background: #fff; }
td, th { border: 1px solid #ccc; padding: 6px 10px; text-align: left; vertical-align: top; }
.review { border-left: 4px solid #283593; background: #fff; padding: 6px 12px; margin: 10px 0; }
.review p { margin: 4px 0 0; }
.faq dt { font-weight: bold; margin-top: 10px; }
.faq dd { margin: 2px 0 0; }
.product-image { padding: 90px 10px; }""",
    "boxed": """.shell { max-width: 900px; background: #fff; border: 1px solid #f8bbd0; margin: 20px auto; padding: 24px; }
.product { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
.order-box, .price-lines { border: 1px solid #f8bbd0; background: #fff5f8; }
.line.total { color: #ad1457; }
button { border-radius: 3px; text-transform: uppercase; letter-spacing: 1px; font-size: 14px; }""",
}


def style_css(s):
    c = s["colours"]
    extra = EXTRA_CSS.replace("$accent", c["accent"])
    return CSS.substitute(font=c["font"], page=c["page"], header=c["header"], header_text=c["header_text"],
                          accent=c["accent"], layout=LAYOUT_CSS[s["layout"]] + extra)


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
    traps = []
    if "mrp" in e:
        traps.append({"type": "price_change", "label": s["product"]["name"],
                      "amount": e["mrp"]["amount"] - s["product"]["price"],
                      "scored": True, "pattern": "bait and switch"})
    if "zone" in e and not s["task_choice"].get("zone"):
        z = next(o for o in e["zone"]["options"] if o["id"] == e["zone"]["default"])
        if z["amount"]:
            traps.append({"type": "preselected_zone_fee", "label": z["line"], "amount": z["amount"],
                          "scored": True, "pattern": "interface interference"})
    if "taxes" in e:
        x = e["taxes"]
        traps.append({"type": "undisclosed_tax", "label": x["label"], "amount": x["amount"],
                      "scored": True, "pattern": "drip pricing"})
    if "summary_charge" in e:
        x = e["summary_charge"]
        traps.append({"type": "drip_fee", "label": x["label"], "amount": x["amount"],
                      "scored": True, "pattern": "drip pricing"})
    if "tip" in e:
        x = e["tip"]
        traps.append({"type": "pre_ticked_addon", "label": x["label"], "amount": x["amount"],
                      "scored": True, "pattern": "basket sneaking"})
    if "interstitial" in e:
        x = e["interstitial"]
        traps.append({"type": "upsell_interstitial", "label": x["label"], "amount": x["amount"],
                      "scored": False, "pattern": "nagging"})
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


# ---------- checks ----------

def check_neutral_extra(folder):
    pattern = re.compile("|".join(re.escape(w) for w in EXTRA_FORBIDDEN), re.IGNORECASE)
    for f in folder.rglob("*"):
        if f.is_file():
            hit = pattern.search(f.read_text(encoding="utf-8")) or pattern.search(f.name)
            if hit:
                raise SystemExit(f"non-neutral word {hit.group(0)!r} in {f}")


def other_store_paths():
    paths = [p for p in sorted(WWW.glob("l*")) if p.is_dir() and p.name not in MY_STORES]
    paths += [p for p in sorted(KEYS.glob("l*.json")) if p.stem not in MY_STORES]
    return paths


def snapshot(paths):
    out = {}
    for p in paths:
        files = sorted(p.rglob("*")) if p.is_dir() else [p]
        for f in files:
            if f.is_file():
                out[str(f)] = hashlib.sha256(f.read_bytes()).hexdigest()
    return out


def check_others_untouched(before):
    after = snapshot(other_store_paths())
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    if changed:
        raise SystemExit("other stores changed, which gen4.py must never do:\n" + "\n".join(changed))
    rel = [str(p.relative_to(ROOT.parent)) for p in other_store_paths()]
    try:
        out = subprocess.run(["git", "diff", "--stat", "--"] + rel, cwd=ROOT.parent,
                             capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as e:
        print(f"could not run git diff over the other stores: {e}")
        return
    if out:
        raise SystemExit("git diff shows changes outside l17-l20:\n" + out)
    print(f"{len(rel)} other store paths untouched (hashes equal, git diff empty)")


def write_store(s):
    e = s["extras"]
    out = WWW / s["id"]
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    if "long_page" in e:
        index = long_product_page(s)
        n = visible_text_before_price(index)
        if n < 7000:
            raise SystemExit(f"{s['id']}: only {n} characters of visible text before the price block")
        print(f"{s['id']}: {n} characters of visible text before the price block")
    elif "taxes" in e:
        index = taxes_product_page(s)
    elif "mrp" in e:
        index = mrp_product_page(s)
    else:
        index = product_page(s)
    (out / "index.html").write_text(index, encoding="utf-8")
    (out / "cart.html").write_text(cart_page(s), encoding="utf-8")
    if "interstitial" in e:
        (out / "before.html").write_text(before_page(s), encoding="utf-8")
    if "zone" in e:
        options = zone_options_page(s)
    elif "wrap_box" in e:
        options = wrap_options_page(s)
    else:
        options = options_page(s)
    (out / "options.html").write_text(options, encoding="utf-8")
    (out / "summary.html").write_text(summary_page(s), encoding="utf-8")
    (out / "pay.html").write_text(pay_page(s), encoding="utf-8")
    (out / "app.js").write_text(app_js(s), encoding="utf-8")
    (out / "style.css").write_text(style_css(s), encoding="utf-8")
    check_neutral(out)
    check_neutral_extra(out)
    key = build_key(s)
    (KEYS / f"{s['id']}.json").write_text(json.dumps(key, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    pages = len(list(out.glob("*.html")))
    print(f"{s['id']} {s['name']}: expected_final_total={key['expected_final_total']}, {pages} pages -> {out}")


def main():
    KEYS.mkdir(parents=True, exist_ok=True)
    before = snapshot(other_store_paths())
    for s in STORES:
        assert s["id"] in MY_STORES, s["id"]
        write_store(s)
    check_others_untouched(before)
    print(f"wrote {len(STORES)} stores under {WWW} and their keys under {KEYS}")


if __name__ == "__main__":
    main()
