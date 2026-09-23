var STORE = {
  "storageKey": "stitchyard_rack",
  "words": {
    "cart": "rack",
    "add": "Add",
    "next": "Step ahead",
    "pay": "Make payment"
  },
  "product": {
    "name": "Crew Neck T-shirt",
    "price": 689
  },
  "variants": [
    {
      "id": "white-xs",
      "text": "White / XS",
      "price": 399
    },
    {
      "id": "white-s",
      "text": "White / S",
      "price": 423
    },
    {
      "id": "white-m",
      "text": "White / M",
      "price": 447
    },
    {
      "id": "white-l",
      "text": "White / L",
      "price": 471
    },
    {
      "id": "white-xl",
      "text": "White / XL",
      "price": 496
    },
    {
      "id": "black-xs",
      "text": "Black / XS",
      "price": 520
    },
    {
      "id": "black-s",
      "text": "Black / S",
      "price": 544
    },
    {
      "id": "black-m",
      "text": "Black / M",
      "price": 568
    },
    {
      "id": "black-l",
      "text": "Black / L",
      "price": 592
    },
    {
      "id": "black-xl",
      "text": "Black / XL",
      "price": 616
    },
    {
      "id": "blue-xs",
      "text": "Blue / XS",
      "price": 640
    },
    {
      "id": "blue-s",
      "text": "Blue / S",
      "price": 665
    },
    {
      "id": "blue-m",
      "text": "Blue / M",
      "price": 689
    },
    {
      "id": "blue-l",
      "text": "Blue / L",
      "price": 713
    },
    {
      "id": "blue-xl",
      "text": "Blue / XL",
      "price": 737
    },
    {
      "id": "green-xs",
      "text": "Green / XS",
      "price": 761
    },
    {
      "id": "green-s",
      "text": "Green / S",
      "price": 785
    },
    {
      "id": "green-m",
      "text": "Green / M",
      "price": 809
    },
    {
      "id": "green-l",
      "text": "Green / L",
      "price": 833
    },
    {
      "id": "green-xl",
      "text": "Green / XL",
      "price": 858
    },
    {
      "id": "red-xs",
      "text": "Red / XS",
      "price": 882
    },
    {
      "id": "red-s",
      "text": "Red / S",
      "price": 906
    },
    {
      "id": "red-m",
      "text": "Red / M",
      "price": 930
    },
    {
      "id": "red-l",
      "text": "Red / L",
      "price": 954
    },
    {
      "id": "red-xl",
      "text": "Red / XL",
      "price": 978
    },
    {
      "id": "grey-xs",
      "text": "Grey / XS",
      "price": 1002
    },
    {
      "id": "grey-s",
      "text": "Grey / S",
      "price": 1027
    },
    {
      "id": "grey-m",
      "text": "Grey / M",
      "price": 1051
    },
    {
      "id": "grey-l",
      "text": "Grey / L",
      "price": 1075
    },
    {
      "id": "grey-xl",
      "text": "Grey / XL",
      "price": 1099
    }
  ],
  "quantityButtons": null,
  "delivery": {
    "default": "standard",
    "options": [
      {
        "id": "standard",
        "text": "Standard ₹45",
        "line": "Delivery",
        "amount": 45
      },
      {
        "id": "express",
        "text": "Express ₹120",
        "line": "Express delivery",
        "amount": 120
      }
    ]
  },
  "slot": null,
  "summaryCharge": {
    "label": "Packing charge",
    "amount": 20
  },
  "details": null
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
function slotChoice(s) { return STORE.slot ? pick(STORE.slot.options, s.slot) : null; }
function reviewPage(pageName) { return pageName === "summary" || pageName === "pay"; }

function productLine(s) {
  var qty = s.qty || 1;
  var v = STORE.variants ? pick(STORE.variants, s.variant) : null;
  var unit = v ? v.price : STORE.product.price;
  var label = STORE.product.name + (v ? " (" + v.text + ")" : "") + (STORE.quantityButtons ? " × " + qty : "");
  return {label: label, amount: unit * qty};
}

function orderLines(s, pageName) {
  var out = [productLine(s)];
  var d = deliveryChoice(s);
  if (d) out.push({label: d.line, amount: d.amount});
  var sl = slotChoice(s);
  if (sl && sl.amount && pageName !== "cart") out.push({label: sl.line, amount: sl.amount, more: true});
  if (reviewPage(pageName)) {
    if (STORE.summaryCharge) out.push(STORE.summaryCharge);
    if (STORE.details) out.push({label: STORE.details.charge.label, amount: STORE.details.charge.amount, more: true});
  }
  return out;
}

function renderOrder(pageName) {
  var s = load();
  var box = document.getElementById("order-lines");
  var more = document.getElementById("charge-lines");
  var tot = document.getElementById("order-total");
  if (!s) {
    if (box) box.innerHTML = "<p>Your " + STORE.words.cart + " is empty.</p>";
    if (tot) tot.textContent = money(0);
    return 0;
  }
  var lines = orderLines(s, pageName);
  function row(l) { return '<div class="line"><span>' + l.label + "</span><span>" + money(l.amount) + "</span></div>"; }
  if (box) box.innerHTML = lines.filter(function (l) { return !(more && l.more); }).map(row).join("");
  if (more) more.innerHTML = lines.filter(function (l) { return l.more; }).map(row).join("");
  var t = lines.reduce(function (a, l) { return a + l.amount; }, 0);
  if (tot) tot.textContent = money(t);
  return t;
}

function initProduct() {
  var count = 1;
  var countEl = document.getElementById("quantity-count");
  var totalEl = document.getElementById("quantity-total");
  function paintCount() {
    if (countEl) countEl.textContent = String(count);
    if (totalEl) totalEl.textContent = "Total for " + count + ": " + money(STORE.product.price * count);
  }
  var up = document.getElementById("quantity-up");
  var down = document.getElementById("quantity-down");
  if (up) up.addEventListener("click", function () { if (count < STORE.quantityButtons.max) count += 1; paintCount(); });
  if (down) down.addEventListener("click", function () { if (count > 1) count -= 1; paintCount(); });
  paintCount();
  function start(variant) {
    save({qty: count, variant: variant || null, delivery: null, slot: STORE.slot ? STORE.slot.default : null});
    location.href = "cart.html";
  }
  var add = document.getElementById("add-button");
  if (add) add.addEventListener("click", function () { start(null); });
  Array.prototype.forEach.call(document.querySelectorAll("[data-variant]"), function (b) {
    b.addEventListener("click", function () { start(b.getAttribute("data-variant")); });
  });
}

function initCart() {
  renderOrder("cart");
  document.getElementById("next-button").addEventListener("click", function () {
    location.href = STORE.slot ? "slot.html" : "options.html";
  });
}

function initSlot() {
  var s = load();
  if (!s) { renderOrder("slot"); return; }
  if (!s.slot && STORE.slot.default) { s.slot = STORE.slot.default; save(s); }
  var radios = document.querySelectorAll("input[name=slot]");
  Array.prototype.forEach.call(radios, function (r) {
    r.checked = r.getAttribute("data-slot") === s.slot;
    r.addEventListener("change", function () {
      if (r.checked) { s.slot = r.getAttribute("data-slot"); save(s); renderOrder("slot"); }
    });
  });
  renderOrder("slot");
  document.getElementById("next-button").addEventListener("click", function () { location.href = "options.html"; });
}

function initOptions() {
  var s = load();
  if (!s) { renderOrder("options"); return; }
  var sel = document.getElementById("delivery-select");
  if (!s.delivery && STORE.delivery.default) { s.delivery = STORE.delivery.default; save(s); }
  sel.value = s.delivery || "";
  sel.addEventListener("change", function () { s.delivery = sel.value || null; save(s); renderOrder("options"); });
  renderOrder("options");
  document.getElementById("next-button").addEventListener("click", function () {
    if (!s.delivery) { notice("Please choose a delivery option."); return; }
    location.href = "summary.html";
  });
}

function toggle(btnId, panelId, show, hide) {
  var btn = document.getElementById(btnId);
  var panel = document.getElementById(panelId);
  if (!btn || !panel) return;
  btn.addEventListener("click", function () {
    var open = panel.classList.toggle("open");
    btn.textContent = open ? hide : show;
  });
}

function initSummary() {
  var t = renderOrder("summary");
  if (STORE.details) {
    toggle("details-button", "details-panel", STORE.details.show, STORE.details.hide);
    toggle("charges-button", "charges-panel", STORE.details.moreShow, STORE.details.moreHide);
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
else if (PAGE === "slot") initSlot();
else if (PAGE === "options") initOptions();
else if (PAGE === "summary") initSummary();
else if (PAGE === "pay") renderOrder("pay");
