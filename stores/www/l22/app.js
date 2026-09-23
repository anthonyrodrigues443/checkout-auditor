var STORE = {
  "storageKey": "yarnyard_stash",
  "words": {
    "cart": "stash",
    "add": "Add to stash",
    "next": "Next up",
    "pay": "Pay for my order"
  },
  "pages": [
    "index",
    "cart",
    "options",
    "summary",
    "pay"
  ],
  "next": {
    "index": "cart.html",
    "cart": "options.html",
    "options": "summary.html",
    "summary": "pay.html"
  },
  "product": {
    "name": "Merino Wool Yarn 100 g",
    "price": 390
  },
  "fixedCharges": [],
  "delivery": {
    "default": "standard",
    "options": [
      {
        "id": "standard",
        "text": "Standard ₹40 (estimated)",
        "line": "Delivery (estimated)",
        "amount": 40,
        "reviewAmount": 60,
        "reviewLine": "Delivery"
      },
      {
        "id": "express",
        "text": "Express ₹120",
        "line": "Express delivery",
        "amount": 120
      }
    ]
  },
  "estimates": [
    {
      "label": "Packaging",
      "amount": 0,
      "reviewAmount": 20,
      "suffix": "(free)"
    }
  ],
  "addonOffer": null,
  "cover": null,
  "gift": null,
  "protection": null,
  "wrap": null,
  "coupon": null,
  "details": null,
  "cartOffer": null,
  "payment": null,
  "payRule": null
};

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
function appliedPayment(s) {
  if (STORE.payRule && s.payment === STORE.payRule.chosen) return STORE.payRule.applied;
  return s.payment;
}

function orderLines(s, pageName) {
  var review = reached(pageName, "summary");
  var out = [{label: STORE.product.name, amount: STORE.product.price}];
  if (STORE.addonOffer && s.addon) out.push({label: STORE.addonOffer.label, amount: STORE.addonOffer.amount});
  if (STORE.cover && s.cover) out.push(STORE.cover);
  STORE.fixedCharges.forEach(function (c) { out.push(c); });
  if (STORE.gift && s.gift && reached(pageName, "gift")) out.push(STORE.gift);
  if (STORE.protection && s.protection && reached(pageName, "protection")) out.push(STORE.protection);
  if (STORE.wrap && s.wrap && reached(pageName, "wrap")) out.push({label: STORE.wrap.label, amount: STORE.wrap.amount});
  var d = deliveryChoice(s);
  if (d) {
    var settled = review && d.reviewAmount != null;
    out.push({label: settled && d.reviewLine ? d.reviewLine : d.line, amount: settled ? d.reviewAmount : d.amount});
  }
  STORE.estimates.forEach(function (c) {
    if (review) out.push({label: c.label, amount: c.reviewAmount});
    else out.push({label: c.label, amount: c.amount, suffix: c.suffix});
  });
  if (STORE.cartOffer && !review) out.push(STORE.cartOffer);
  if (review) {
    if (STORE.details && STORE.details.charge) out.push(STORE.details.charge);
    if (STORE.payRule && s.payment && appliedPayment(s) === STORE.payRule.applied) out.push(STORE.payRule.fee);
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
      var amount = money(l.amount) + (l.suffix ? " " + l.suffix : "");
      return '<div class="line"><span>' + l.label + "</span><span>" + amount + "</span></div>";
    }).join("");
  }
  var t = lines.reduce(function (a, l) { return a + l.amount; }, 0);
  if (tot) tot.textContent = money(t);
  return t;
}

function go(pageName) { location.href = STORE.next[pageName]; }

function initProduct() {
  document.getElementById("add-button").addEventListener("click", function () {
    save({qty: 1, addon: false, offerAnswered: false, cover: false, gift: !!STORE.gift,
          protection: !!STORE.protection, wrap: false, delivery: null, payment: null});
    go("index");
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
  document.getElementById("next-button").addEventListener("click", function () { go("cart"); });
  if (s && STORE.addonOffer && !s.offerAnswered) showOffer(s);
  var coupon = document.getElementById("coupon-button");
  if (coupon) coupon.addEventListener("click", function () {
    document.getElementById("coupon-note").textContent = STORE.coupon.message;
  });
}

function initCover() {
  var s = load();
  renderOrder("warranty");
  if (!s) return;
  document.getElementById("cover-yes").addEventListener("click", function () { s.cover = true; save(s); go("warranty"); });
  document.getElementById("next-button").addEventListener("click", function () { go("warranty"); });
}

function initCheckPage(pageName, checkId, stateKey) {
  var s = load();
  if (!s) { renderOrder(pageName); return; }
  var chk = document.getElementById(checkId);
  var btn = document.getElementById("next-button");
  function label() { if (STORE.wrap && pageName === "wrap") btn.textContent = s.wrap ? STORE.wrap.go : STORE.wrap.skip; }
  chk.checked = !!s[stateKey];
  chk.addEventListener("change", function () { s[stateKey] = chk.checked; save(s); renderOrder(pageName); label(); });
  renderOrder(pageName);
  label();
  btn.addEventListener("click", function () { go(pageName); });
}

function initAddress() {
  renderOrder("address");
  document.getElementById("next-button").addEventListener("click", function () { go("address"); });
}

function initOptions() {
  var s = load();
  if (!s) { renderOrder("options"); return; }
  var sel = document.getElementById("delivery-select");
  if (!s.delivery && STORE.delivery.default) { s.delivery = STORE.delivery.default; save(s); }
  sel.value = s.delivery || "";
  sel.addEventListener("change", function () { s.delivery = sel.value || null; save(s); renderOrder("options"); });
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
    go("options");
  });
}

function initSummary() {
  var s = load();
  var t = renderOrder("summary");
  var payLine = document.getElementById("payment-line");
  if (payLine && STORE.payment) {
    var chosen = null;
    if (s) STORE.payment.options.forEach(function (o) { if (o.id === s.payment) chosen = o; });
    var text = chosen ? chosen.text : "Not chosen";
    if (s && STORE.payRule && s.payment === STORE.payRule.chosen) text = STORE.payRule.shown;
    payLine.textContent = text;
  }
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
else if (PAGE === "warranty") initCover();
else if (PAGE === "gift") initCheckPage("gift", "gift-check", "gift");
else if (PAGE === "protection") initCheckPage("protection", "protection-check", "protection");
else if (PAGE === "wrap") initCheckPage("wrap", "wrap-check", "wrap");
else if (PAGE === "address") initAddress();
else if (PAGE === "options") initOptions();
else if (PAGE === "summary") initSummary();
else if (PAGE === "pay") renderOrder("pay");
