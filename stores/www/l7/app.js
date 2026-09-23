var STORE = {
  "storageKey": "orchardlane_hamper",
  "words": {
    "cart": "hamper",
    "add": "Add to hamper",
    "next": "Go to checkout",
    "pay": "Buy now"
  },
  "product": {
    "name": "Wild Forest Honey 500 g",
    "price": 450
  },
  "fixedCharges": [
    {
      "label": "GST",
      "amount": 22
    }
  ],
  "delivery": {
    "default": "standard",
    "options": [
      {
        "id": "standard",
        "text": "Standard ₹35",
        "line": "Delivery",
        "amount": 35
      },
      {
        "id": "express",
        "text": "Express ₹110",
        "line": "Express delivery",
        "amount": 110
      }
    ]
  },
  "addonOffer": {
    "label": "Wooden honey dipper",
    "amount": 99,
    "text": "Add a wooden honey dipper for ₹99?",
    "yes": "Add dipper",
    "no": "Skip"
  },
  "protection": null,
  "deliveryCharge": null,
  "summaryCharge": null,
  "offer": null,
  "coupon": {
    "message": "Coupon applied at payment"
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
          protection: !!STORE.protection, delivery: null});
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
  var coupon = document.getElementById("coupon-button");
  if (coupon) coupon.addEventListener("click", function () {
    document.getElementById("coupon-note").textContent = STORE.coupon.message;
  });
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
  renderOrder("options");
  document.getElementById("next-button").addEventListener("click", function () {
    if (!s.delivery) { notice("Please choose a delivery option."); return; }
    location.href = "summary.html";
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
else if (PAGE === "options") initOptions();
else if (PAGE === "summary") initSummary();
else if (PAGE === "pay") renderOrder("pay");
