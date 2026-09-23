var STORE = {
  "storageKey": "linenloft_picks",
  "words": {
    "cart": "picks",
    "add": "Add to picks",
    "next": "Go on",
    "pay": "Pay for order"
  },
  "product": {
    "name": "Cotton Bedsheet Set (Double)",
    "price": 999
  },
  "fixedCharges": [],
  "delivery": {
    "default": "standard",
    "options": [
      {
        "id": "standard",
        "text": "Standard ₹40",
        "line": "Delivery",
        "amount": 40
      },
      {
        "id": "express",
        "text": "Express ₹110",
        "line": "Express delivery",
        "amount": 110
      }
    ]
  },
  "zone": null,
  "taxes": null,
  "tip": null,
  "warranty": null,
  "summaryCharge": null,
  "listPrice": {
    "amount": 1299
  },
  "wrap": {
    "label": "Gift wrap",
    "amount": 30
  },
  "coupon": {
    "message": "Code will be checked at payment"
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
