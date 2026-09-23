var STORE = {
  "storageKey": "spiceroute_trolley",
  "words": {
    "cart": "trolley",
    "add": "Add to trolley",
    "next": "Go ahead",
    "pay": "Confirm order"
  },
  "product": {
    "name": "Garam Masala Tin 200 g",
    "price": 320
  },
  "fixedCharges": [
    {
      "label": "GST",
      "amount": 16
    }
  ],
  "delivery": {
    "default": "standard",
    "options": [
      {
        "id": "standard",
        "text": "Standard ₹30",
        "line": "Delivery",
        "amount": 30
      },
      {
        "id": "express",
        "text": "Express ₹90",
        "line": "Express delivery",
        "amount": 90
      }
    ]
  },
  "addonOffer": null,
  "protection": null,
  "deliveryCharge": null,
  "summaryCharge": null,
  "offer": null,
  "payment": {
    "default": "upi",
    "options": [
      {
        "id": "upi",
        "text": "UPI"
      },
      {
        "id": "card",
        "text": "Card"
      },
      {
        "id": "cod",
        "text": "Cash on delivery"
      }
    ],
    "codOption": "cod",
    "codCharge": {
      "label": "Cash handling",
      "amount": 40
    }
  }
};

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

function orderLines(s, pageName) {
  var out = [];
  out.push({label: STORE.product.name + (s.size ? " (size " + s.size + ")" : ""), amount: STORE.product.price});
  if (STORE.addonOffer && s.addon) out.push({label: STORE.addonOffer.label, amount: STORE.addonOffer.amount});
  STORE.fixedCharges.forEach(function (c) { out.push(c); });
  if (STORE.protection && s.protection && pageName !== "cart") out.push(STORE.protection);
  var d = deliveryChoice(s);
  if (d) out.push({label: d.line, amount: d.amount});
  if (d && STORE.deliveryCharge) out.push(STORE.deliveryCharge);
  if (pageName === "summary" || pageName === "pay") {
    if (STORE.summaryCharge) out.push(STORE.summaryCharge);
    if (STORE.offer) out.push(STORE.offer);
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
  var t = lines.reduce(function (a, l) { return a + l.amount; }, 0);
  if (tot) tot.textContent = money(t);
  return t;
}

function initProduct() {
  var sizeSel = document.getElementById("size-select");
  document.getElementById("add-button").addEventListener("click", function () {
    var size = sizeSel ? sizeSel.value : null;
    if (sizeSel && !size) { notice("Please choose a size first."); return; }
    save({qty: 1, size: size || null, addon: false, offerAnswered: false,
          protection: !!STORE.protection, delivery: null, payment: null});
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
  document.getElementById("next-button").addEventListener("click", function () { location.href = "options.html"; });
  if (s && STORE.addonOffer && !s.offerAnswered) showOffer(s);
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
  var t = renderOrder("summary");
  var payLine = document.getElementById("payment-line");
  if (payLine) {
    var s = load(), chosen = null;
    if (s) STORE.payment.options.forEach(function (o) { if (o.id === s.payment) chosen = o; });
    payLine.textContent = chosen ? chosen.text : "Not chosen";
  }
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
else if (PAGE === "options") initOptions();
else if (PAGE === "summary") initSummary();
else if (PAGE === "pay") renderOrder("pay");
