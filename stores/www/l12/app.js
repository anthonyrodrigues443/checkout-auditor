var STORE = {
  "storageKey": "crumbcorner_box",
  "words": {
    "cart": "box",
    "add": "Add to box",
    "next": "Move ahead",
    "pay": "Order and pay"
  },
  "product": {
    "name": "Dry Fruit Cake 500 g",
    "price": 720
  },
  "fixedCharges": [],
  "delivery": {
    "default": null,
    "options": [
      {
        "id": "standard",
        "text": "Standard – Free",
        "line": "Standard delivery",
        "amount": 0
      },
      {
        "id": "express",
        "text": "Express ₹89",
        "line": "Express delivery",
        "amount": 89
      }
    ]
  },
  "protection": null,
  "gift": {
    "label": "Greeting card",
    "amount": 35
  },
  "deliveryUpgrade": {
    "to": "express"
  },
  "details": {
    "show": "View price details",
    "hide": "Hide price details",
    "charge": {
      "label": "Service fee",
      "amount": 39
    }
  },
  "priceUpdate": null,
  "cartOffer": null,
  "payment": {
    "default": null,
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
      "amount": 45
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
  var t = lines.reduce(function (a, l) { return a + l.amount; }, 0);
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
