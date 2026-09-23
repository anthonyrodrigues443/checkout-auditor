var STORE = {
  "storageKey": "ankletalley_carton",
  "words": {
    "cart": "carton",
    "add": "Add to carton",
    "next": "Take me to checkout",
    "pay": "Pay and place order"
  },
  "product": {
    "name": "Silver Anklet Pair",
    "price": 1180
  },
  "delivery": {
    "default": "standard",
    "options": [
      {
        "id": "standard",
        "text": "Standard – Free",
        "line": "Standard delivery",
        "amount": 0
      },
      {
        "id": "express",
        "text": "Express ₹110",
        "line": "Express delivery",
        "amount": 110
      }
    ]
  },
  "protection": null,
  "packaging": {
    "default": "gift",
    "options": [
      {
        "id": "standard",
        "text": "Standard – free",
        "line": "Standard packaging",
        "amount": 0
      },
      {
        "id": "gift",
        "text": "Gift box ₹40",
        "line": "Gift box",
        "amount": 40
      }
    ]
  },
  "coupon": {
    "code": "WELCOME150",
    "amount": 150,
    "line": "Coupon applied",
    "message": "WELCOME150 applied",
    "invalid": "This code is not valid"
  },
  "deliveryUpgrade": null
};

var KEY = STORE.storageKey;
var REVIEW_FLAG = KEY + "_reviewed";

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

function orderLines(s, pageName) {
  var out = [{label: STORE.product.name, amount: STORE.product.price}];
  if (STORE.protection && pageName !== "cart") {
    var pr = pick(STORE.protection.options, s.protection);
    if (pr && pr.amount) out.push({label: pr.line, amount: pr.amount});
  }
  if (STORE.packaging && pageName !== "cart") {
    var pk = pick(STORE.packaging.options, s.packaging);
    if (pk && pk.amount) out.push({label: pk.line, amount: pk.amount});
  }
  var d = deliveryChoice(s);
  if (d) out.push({label: d.line, amount: d.amount});
  if (STORE.coupon && s.coupon) out.push({label: STORE.coupon.line, amount: -STORE.coupon.amount});
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
  document.getElementById("add-button").addEventListener("click", function () {
    localStorage.removeItem(REVIEW_FLAG);
    save({qty: 1, delivery: null, coupon: false,
          protection: STORE.protection ? STORE.protection.default : null,
          packaging: STORE.packaging ? STORE.packaging.default : null});
    location.href = "cart.html";
  });
}

function initCart() {
  renderOrder("cart");
  var coupon = document.getElementById("coupon-button");
  if (coupon) coupon.addEventListener("click", function () {
    var s = load();
    if (!s) return;
    var code = document.getElementById("coupon-input").value.trim().toUpperCase();
    var note = document.getElementById("coupon-note");
    if (code === STORE.coupon.code) { s.coupon = true; save(s); note.textContent = STORE.coupon.message; }
    else note.textContent = STORE.coupon.invalid;
    renderOrder("cart");
  });
  document.getElementById("next-button").addEventListener("click", function () { location.href = "options.html"; });
}

function initOptions() {
  var s = load();
  if (!s) { renderOrder("options"); return; }
  var sel = document.getElementById("delivery-select");
  if (!s.delivery && STORE.delivery.default) { s.delivery = STORE.delivery.default; save(s); }
  sel.value = s.delivery || "";
  sel.addEventListener("change", function () { s.delivery = sel.value || null; save(s); renderOrder("options"); });
  var radios = document.querySelectorAll("input[name=protection]");
  Array.prototype.forEach.call(radios, function (r) {
    r.checked = r.getAttribute("data-choice") === s.protection;
    r.addEventListener("change", function () {
      if (r.checked) { s.protection = r.getAttribute("data-choice"); save(s); renderOrder("options"); }
    });
  });
  var pack = document.getElementById("packaging-select");
  if (pack) {
    if (!s.packaging && STORE.packaging.default) { s.packaging = STORE.packaging.default; save(s); }
    pack.value = s.packaging || "";
    pack.addEventListener("change", function () { s.packaging = pack.value || null; save(s); renderOrder("options"); });
  }
  renderOrder("options");
  document.getElementById("next-button").addEventListener("click", function () {
    if (!s.delivery) { notice("Please choose a delivery option."); return; }
    location.href = "summary.html";
  });
}

function initSummary() {
  var s = load();
  if (s && STORE.deliveryUpgrade && !localStorage.getItem(REVIEW_FLAG)) {
    localStorage.setItem(REVIEW_FLAG, "1");
    s.delivery = STORE.deliveryUpgrade.to;
    save(s);
  }
  var t = renderOrder("summary");
  var note = document.getElementById("delivery-note");
  if (note && !(s && STORE.deliveryUpgrade && s.delivery === STORE.deliveryUpgrade.to)) note.style.display = "none";
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
