var STORE = {
  "storageKey": "sudsandsuch_bucket",
  "words": {
    "cart": "bucket",
    "add": "Add to bucket",
    "next": "Carry forward",
    "pay": "Finalise and pay"
  },
  "product": {
    "name": "Handmade Soap Bar Set of 3",
    "price": 465
  },
  "fixedCharges": [],
  "delivery": {
    "initial": "standard",
    "options": [
      {
        "id": "standard",
        "text": "Standard – Free",
        "line": "Delivery",
        "amount": 0
      },
      {
        "id": "express",
        "text": "Express ₹95",
        "line": "Express delivery",
        "amount": 95
      }
    ]
  },
  "choices": [
    {
      "id": "packing",
      "selectId": "packing-select",
      "initial": "box",
      "options": [
        {
          "id": "eco",
          "text": "Eco pouch – free",
          "line": "Eco pouch",
          "amount": 0
        },
        {
          "id": "box",
          "text": "Premium box ₹30",
          "line": "Premium box",
          "amount": 30
        }
      ]
    },
    {
      "id": "zone",
      "selectId": "zone-select",
      "initial": "outside",
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
    }
  ]
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
function deliveryChoice(s) { return pick(STORE.delivery.options, s.delivery || STORE.delivery.initial); }
function pickedOption(c, s) { return pick(c.options, (s.picks && s.picks[c.id]) || c.initial); }
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
  if (pageName !== "cart") {
    STORE.choices.forEach(function (c) {
      var o = pickedOption(c, s);
      if (o) out.push({label: o.line, amount: o.amount});
    });
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
  document.getElementById("add-button").addEventListener("click", function () {
    save({qty: 1, size: null, delivery: null, picks: startingPicks()});
    location.href = "cart.html";
  });
}

function initCart() {
  renderOrder("cart");
  document.getElementById("next-button").addEventListener("click", function () { location.href = "options.html"; });
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
    location.href = "summary.html";
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
else if (PAGE === "options") initOptions();
else if (PAGE === "summary") initSummary();
else if (PAGE === "pay") renderOrder("pay");
