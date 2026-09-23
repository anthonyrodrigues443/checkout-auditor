var STORE = {
  "storageKey": "beancounter_sack",
  "words": {
    "cart": "sack",
    "add": "Add to sack",
    "next": "Keep going",
    "pay": "Pay {total} now"
  },
  "pages": [
    "index",
    "cart",
    "options",
    "summary",
    "pay"
  ],
  "next": {
    "cart": "options.html",
    "options": "summary.html",
    "summary": "pay.html"
  },
  "product": {
    "name": "Roasted Arabica Beans 250 g",
    "price": 520
  },
  "quantity": false,
  "delivery": {
    "default": "standard",
    "options": [
      {
        "id": "standard",
        "text": "Standard ₹49",
        "line": "Delivery",
        "amount": 49
      },
      {
        "id": "express",
        "text": "Express ₹130",
        "line": "Express delivery",
        "amount": 130
      }
    ]
  },
  "addonOffer": null,
  "gift": null,
  "protection": null,
  "membership": {
    "label": "Plus membership trial (₹0 today, ₹199/month after 30 days)",
    "amount": 0
  },
  "coupon": {
    "code": "SAVE200",
    "label": "Coupon SAVE200",
    "amount": -200,
    "message": "Coupon SAVE200 applied: ₹200 off"
  },
  "summaryCharge": null
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
