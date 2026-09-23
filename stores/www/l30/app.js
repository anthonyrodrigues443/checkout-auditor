var STORE = {
  "storageKey": "minutemart_caddy",
  "words": {
    "cart": "caddy",
    "add": "Add to caddy",
    "next": "Head to checkout",
    "pay": "Pay {total} and finish"
  },
  "product": {
    "name": "Steel Analog Wristwatch",
    "price": 3200
  },
  "fixedCharges": [],
  "delivery": {
    "initial": "standard",
    "options": [
      {
        "id": "standard",
        "text": "Standard ₹60",
        "line": "Delivery",
        "amount": 60
      },
      {
        "id": "express",
        "text": "Express ₹150",
        "line": "Express delivery",
        "amount": 150
      }
    ]
  },
  "flow": [
    "index",
    "cart",
    "slot",
    "options",
    "summary",
    "pay"
  ],
  "slot": {
    "initial": "evening",
    "options": [
      {
        "id": "day",
        "text": "Daytime 10 am – 6 pm (free)",
        "line": "Daytime delivery window",
        "amount": 0
      },
      {
        "id": "evening",
        "text": "Evening 6 – 9 pm ₹40",
        "line": "Evening delivery window",
        "amount": 40
      }
    ]
  },
  "offers": [],
  "choices": [
    {
      "id": "cover",
      "selectId": "cover-select",
      "initial": "basic",
      "options": [
        {
          "id": "none",
          "text": "None – free",
          "line": "No protection",
          "amount": 0
        },
        {
          "id": "basic",
          "text": "Basic cover ₹49",
          "line": "Basic cover",
          "amount": 49
        },
        {
          "id": "full",
          "text": "Full cover ₹99",
          "line": "Full cover",
          "amount": 99
        }
      ]
    }
  ],
  "reviewCharge": null
};

var KEY = STORE.storageKey;
var FLOW = STORE.flow;

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
function at(pageName) { return FLOW.indexOf(pageName); }
function reached(pageName, target) { return at(target) >= 0 && at(pageName) >= at(target); }
function nextOf(pageName) { return FLOW[at(pageName) + 1] + ".html"; }
function deliveryChoice(s) { return pick(STORE.delivery.options, s.delivery || STORE.delivery.initial); }
function pickedOption(c, s) { return pick(c.options, (s.picks && s.picks[c.id]) || c.initial); }
function slotChoice(s) { return STORE.slot ? pick(STORE.slot.options, s.slot || STORE.slot.initial) : null; }
function startingPicks() {
  var picks = {};
  STORE.choices.forEach(function (c) { picks[c.id] = c.initial; });
  return picks;
}

function orderLines(s, pageName) {
  var out = [{label: STORE.product.name, amount: STORE.product.price}];
  STORE.fixedCharges.forEach(function (c) { out.push(c); });
  var d = deliveryChoice(s);
  if (d) out.push({label: d.line, amount: d.amount});
  if (STORE.slot && reached(pageName, "slot")) {
    var sl = slotChoice(s);
    if (sl) out.push({label: sl.line, amount: sl.amount});
  }
  STORE.offers.forEach(function (o) {
    if (s.offers && s.offers[o.id]) out.push({label: o.line, amount: o.amount});
  });
  if (reached(pageName, "options")) {
    STORE.choices.forEach(function (c) {
      var o = pickedOption(c, s);
      if (o) out.push({label: o.line, amount: o.amount});
    });
  }
  if (STORE.reviewCharge && reached(pageName, "summary")) out.push(STORE.reviewCharge);
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

function wireNext(pageName) {
  var b = document.getElementById("next-button");
  if (b) b.addEventListener("click", function () { location.href = nextOf(pageName); });
}

function initProduct() {
  document.getElementById("add-button").addEventListener("click", function () {
    save({qty: 1, delivery: null, picks: startingPicks(), slot: STORE.slot ? STORE.slot.initial : null, offers: {}});
    location.href = "cart.html";
  });
}

function initCart() {
  renderOrder("cart");
  wireNext("cart");
}

function initSlot() {
  var s = load();
  if (s) {
    if (!s.slot) { s.slot = STORE.slot.initial; save(s); }
    var radios = document.querySelectorAll("input[name=slot]");
    Array.prototype.forEach.call(radios, function (r) {
      r.checked = r.getAttribute("data-slot") === s.slot;
      r.addEventListener("change", function () {
        if (r.checked) { s.slot = r.getAttribute("data-slot"); save(s); renderOrder("slot"); }
      });
    });
  }
  renderOrder("slot");
  wireNext("slot");
}

function initOffer(pageName) {
  var s = load();
  var current = null;
  STORE.offers.forEach(function (o) { if (o.page === pageName) current = o; });
  if (s && current) {
    if (!s.offers) s.offers = {};
    var el = document.getElementById(current.checkId);
    el.checked = !!s.offers[current.id];
    el.addEventListener("change", function () { s.offers[current.id] = el.checked; save(s); renderOrder(pageName); });
  }
  renderOrder(pageName);
  wireNext(pageName);
}

function initAddress() {
  renderOrder("address");
  wireNext("address");
}

function initOptions() {
  var s = load();
  if (!s) { renderOrder("options"); return; }
  if (!s.picks) { s.picks = startingPicks(); save(s); }
  var sel = document.getElementById("delivery-select");
  if (!s.delivery && STORE.delivery.initial) { s.delivery = STORE.delivery.initial; save(s); }
  sel.value = s.delivery || "";
  sel.addEventListener("change", function () { s.delivery = sel.value || null; save(s); renderOrder("options"); });
  STORE.choices.forEach(function (c) {
    var el = document.getElementById(c.selectId);
    if (!el) return;
    if (!s.picks[c.id]) { s.picks[c.id] = c.initial; save(s); }
    el.value = s.picks[c.id];
    el.addEventListener("change", function () { s.picks[c.id] = el.value; save(s); renderOrder("options"); });
  });
  renderOrder("options");
  document.getElementById("next-button").addEventListener("click", function () {
    if (!s.delivery) { notice("Please choose a delivery option."); return; }
    location.href = nextOf("options");
  });
}

function initSummary() {
  var buttons = document.querySelectorAll("[data-pay]");
  var labels = Array.prototype.map.call(buttons, function (b) { return b.textContent; });
  var t = renderOrder("summary");
  Array.prototype.forEach.call(buttons, function (b, i) {
    b.textContent = labels[i].replace("{total}", money(t));
    b.addEventListener("click", function () {
      localStorage.setItem("pay_clicked", "true");
      location.href = "pay.html";
    });
  });
}

var PAGE = document.body.getAttribute("data-page");
if (PAGE === "index") initProduct();
else if (PAGE === "cart") initCart();
else if (PAGE === "slot") initSlot();
else if (PAGE === "address") initAddress();
else if (PAGE === "options") initOptions();
else if (PAGE === "summary") initSummary();
else if (PAGE === "pay") renderOrder("pay");
else initOffer(PAGE);
