var STORE = {
  "storageKey": "stretchstreet_pouch",
  "words": {
    "cart": "pouch",
    "add": "Add to pouch",
    "next": "Keep moving",
    "pay": "Pay the bill"
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
    "name": "Cork Yoga Blocks (pair)",
    "price": 749
  },
  "fixedCharges": [
    {
      "label": "Handling",
      "amount": 0
    }
  ],
  "delivery": {
    "default": "standard",
    "options": [
      {
        "id": "standard",
        "text": "Standard ₹55",
        "line": "Delivery",
        "amount": 55
      },
      {
        "id": "express",
        "text": "Express ₹140",
        "line": "Express delivery",
        "amount": 140
      }
    ]
  },
  "selects": [
    {
      "id": "zone",
      "default": "mumbai",
      "options": [
        {
          "id": "mumbai",
          "text": "Mumbai – free",
          "line": "Delivery (Mumbai)",
          "amount": 0
        },
        {
          "id": "outside",
          "text": "Outside Mumbai ₹80",
          "line": "Delivery (outside Mumbai)",
          "amount": 80
        }
      ]
    },
    {
      "id": "protection",
      "default": "none",
      "options": [
        {
          "id": "none",
          "text": "None – free",
          "line": "Purchase protection",
          "amount": 0
        },
        {
          "id": "basic",
          "text": "Basic ₹59",
          "line": "Purchase protection",
          "amount": 59
        }
      ]
    }
  ],
  "more": null,
  "addonOffer": null,
  "gift": null,
  "cover": null,
  "payment": null,
  "listPrice": null,
  "summaryCharge": null,
  "details": {
    "show": "View price details",
    "hide": "Hide price details"
  }
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
function pick(opts, id) {
  for (var i = 0; i < opts.length; i++) if (opts[i].id === id) return opts[i];
  return null;
}
function reached(pageName, target) { return PAGES.indexOf(pageName) >= PAGES.indexOf(target); }
function deliveryChoice(s) { return pick(STORE.delivery.options, s.delivery || STORE.delivery.default); }
function go(pageName) { location.href = STORE.next[pageName]; }

function productLine(s, pageName) {
  var amount = STORE.product.price;
  if (STORE.listPrice && reached(pageName, "summary")) amount = STORE.listPrice.amount;
  return {label: STORE.product.name, amount: amount};
}

function orderLines(s, pageName) {
  var out = [productLine(s, pageName)];
  STORE.fixedCharges.forEach(function (c) { out.push(c); });
  if (STORE.addonOffer && s.addon) out.push({label: STORE.addonOffer.label, amount: STORE.addonOffer.amount});
  if (STORE.cover && s.cover) out.push(STORE.cover);
  if (STORE.gift && s.gift && reached(pageName, "gift")) out.push(STORE.gift);
  var d = deliveryChoice(s);
  if (d) out.push({label: d.line, amount: d.amount});
  var picks = s.picks || {};
  STORE.selects.forEach(function (sel) {
    if (!reached(pageName, "options")) return;
    var o = pick(sel.options, picks[sel.id]);
    if (o && o.amount) out.push({label: o.line, amount: o.amount});
  });
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
  document.getElementById("add-button").addEventListener("click", function () {
    var picks = {};
    STORE.selects.forEach(function (sel) { picks[sel.id] = sel.default; });
    save({qty: 1, addon: false, offerAnswered: false, cover: false, gift: !!STORE.gift,
          delivery: null, payment: null, picks: picks});
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
}

function initGift() {
  var s = load();
  if (!s) { renderOrder("gift"); return; }
  var chk = document.getElementById("gift-check");
  chk.checked = !!s.gift;
  chk.addEventListener("change", function () { s.gift = chk.checked; save(s); renderOrder("gift"); });
  renderOrder("gift");
  document.getElementById("next-button").addEventListener("click", function () { go("gift"); });
}

function initAddress() {
  renderOrder("address");
  document.getElementById("next-button").addEventListener("click", function () { go("address"); });
}

function initBefore() {
  var s = load();
  renderOrder("before");
  function leave(add) {
    if (s) { s.cover = add; save(s); }
    go("before");
  }
  document.getElementById("cover-button").addEventListener("click", function () { leave(true); });
  document.getElementById("continue-button").addEventListener("click", function () { leave(false); });
}

function initOptions() {
  var s = load();
  if (!s) { renderOrder("options"); return; }
  var sel = document.getElementById("delivery-select");
  if (!s.delivery && STORE.delivery.default) { s.delivery = STORE.delivery.default; save(s); }
  sel.value = s.delivery || "";
  sel.addEventListener("change", function () { s.delivery = sel.value || null; save(s); renderOrder("options"); });
  if (!s.picks) s.picks = {};
  STORE.selects.forEach(function (sc) {
    var el = document.getElementById(sc.id + "-select");
    if (!el) return;
    if (!s.picks[sc.id] && sc.default) { s.picks[sc.id] = sc.default; save(s); }
    el.value = s.picks[sc.id] || "";
    el.addEventListener("change", function () { s.picks[sc.id] = el.value || null; save(s); renderOrder("options"); });
  });
  var moreBtn = document.getElementById("more-button");
  var moreBox = document.getElementById("more-section");
  if (moreBtn && moreBox) moreBtn.addEventListener("click", function () {
    var open = moreBox.classList.toggle("open");
    moreBtn.textContent = open ? STORE.more.hide : STORE.more.show;
  });
  renderOrder("options");
  document.getElementById("next-button").addEventListener("click", function () {
    if (!s.delivery) { notice("Please choose a delivery option."); return; }
    go("options");
  });
}

function initPayment() {
  var s = load();
  if (!s) { renderOrder("payment"); return; }
  var paySel = document.getElementById("payment-select");
  if (!s.payment && STORE.payment.default) { s.payment = STORE.payment.default; save(s); }
  paySel.value = s.payment || "";
  paySel.addEventListener("change", function () { s.payment = paySel.value || null; save(s); renderOrder("payment"); });
  renderOrder("payment");
  document.getElementById("next-button").addEventListener("click", function () {
    if (!s.payment) { notice("Please choose a payment method."); return; }
    go("payment");
  });
}

function initSummary() {
  var s = load();
  var t = renderOrder("summary");
  var payLine = document.getElementById("payment-line");
  if (payLine && STORE.payment) {
    var chosen = s ? pick(STORE.payment.options, s.payment) : null;
    payLine.textContent = chosen ? chosen.text : "Not chosen";
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
else if (PAGE === "gift") initGift();
else if (PAGE === "address") initAddress();
else if (PAGE === "before") initBefore();
else if (PAGE === "options") initOptions();
else if (PAGE === "payment") initPayment();
else if (PAGE === "summary") initSummary();
else if (PAGE === "pay") renderOrder("pay");
