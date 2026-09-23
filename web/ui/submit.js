/* Page 1 — submission.

   Collect stores (one URL each) with their task sentences plus a set of models, POST them to
   /api/run, then poll /api/submission/{id} every 3s and render one report section per task as
   its runs finish. Every number shown comes from the run record the backend wrote; this page
   does no arithmetic of its own beyond counting jobs. */

const POLL_MS = 3000;
let rowSeq = 0;
let poller = null;
/** store_id -> shop name, so a task reads "Kirana Direct" rather than "L1" twice. */
const storeNames = new Map();

const TRASH = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"
  stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h16M10 11v6M14 11v6M5 7l1 13h12l1-13M9 7V4h6v3"/></svg>`;

/* ---- stores and their tasks ----
   One store owns one URL and any number of task sentences. Adding a task adds a task only; the
   URL is asked for once per store. The backend still wants a flat list of {url, task, headed},
   so readRows() multiplies the store's URL across its tasks. */

function addStore(url = '', tasks = [''], headedOn = -1) {
  const div = document.createElement('div');
  div.className = 'store';
  div.dataset.store = ++rowSeq;
  div.innerHTML = `
    <div class="store-head">
      <span class="n"></span>
      <input type="text" class="url" placeholder="http://localhost:8000/l3/" value="${esc(url)}" aria-label="Store URL">
      <button class="icon remove-store" type="button" title="Remove this store" aria-label="Remove store">${TRASH}</button>
    </div>
    <div class="tasks"></div>
    <button class="ghost sm add-task" type="button">+ Add task</button>`;

  div.querySelector('.remove-store').addEventListener('click', () => { div.remove(); renumber(); updateNote(); });
  div.querySelector('.add-task').addEventListener('click', () => {
    addTask(div).querySelector('.task').focus();
    updateNote();
  });
  $('#stores').appendChild(div);
  (tasks.length ? tasks : ['']).forEach((t, i) => addTask(div, t, i === headedOn));
  renumber();
  return div;
}

function addTask(store, task = '', headed = false) {
  const div = document.createElement('div');
  div.className = 'taskrow';
  div.innerHTML = `
    <span class="n"></span>
    <input type="text" class="task" placeholder="Buy one blue ceramic mug with standard delivery." value="${esc(task)}" aria-label="Task">
    <label class="chip" title="Run this one in a visible browser window">
      <input type="checkbox" class="headed" ${headed ? 'checked' : ''}> show browser
    </label>
    <button class="icon remove-task" type="button" title="Remove this task" aria-label="Remove task">${TRASH}</button>`;
  div.querySelector('.remove-task').addEventListener('click', () => { div.remove(); renumber(); updateNote(); });
  store.querySelector('.tasks').appendChild(div);
  renumber();
  return div;
}

/** Stores are lettered, tasks numbered within a store, so "B2" names one run on screen. */
function renumber() {
  const stores = $$('#stores .store');
  stores.forEach((s, i) => {
    s.querySelector('.store-head .n').textContent = stores.length > 1 ? String.fromCharCode(65 + i) : '';
    if (!s.querySelectorAll('.taskrow').length) addTask(s);
    s.querySelectorAll('.taskrow .n').forEach((n, j) => { n.textContent = j + 1; });
  });
  if (!stores.length) addStore();
}

function readRows() {
  const out = [];
  $$('#stores .store').forEach((s) => {
    const url = s.querySelector('.url').value.trim();
    if (!url) return;
    s.querySelectorAll('.taskrow').forEach((t) => {
      const task = t.querySelector('.task').value.trim();
      if (task) out.push({ url, task, headed: t.querySelector('.headed').checked });
    });
  });
  return out;
}

/* ---- models ---- */

async function loadModels() {
  const slot = $('#models');
  try {
    const { models } = await apiGet('/api/models');
    slot.innerHTML = models
      .map((m) => `<label class="chip"><input type="checkbox" class="model" value="${esc(m)}" checked>
                   <span class="mono">${esc(m)}</span></label>`)
      .join('');
  } catch (e) {
    slot.innerHTML = `<span class="no">${esc(e.message)}</span>`;
  }
  updateNote();
}

const readModels = () => $$('#models .model:checked').map((c) => c.value);

function updateNote() {
  const rows = readRows();
  const models = readModels().length;
  const stores = new Set(rows.map((r) => r.url)).size;
  $('#go-note').innerHTML = rows.length && models
    ? `<b>${rows.length * models} run${rows.length * models > 1 ? 's' : ''}</b> queued —
       ${rows.length} task${rows.length > 1 ? 's' : ''} across ${stores} store${stores > 1 ? 's' : ''}
       × ${models} model${models > 1 ? 's' : ''}`
    : 'Nothing to run yet.';
}

/* ---- launch + poll ---- */

async function go() {
  const rows = readRows();
  const models = readModels();
  notice($('#error'), '');
  if (!rows.length) return noticeText($('#error'), 'Add at least one store URL with a task under it.', 'bad');
  if (!models.length) return noticeText($('#error'), 'Tick at least one model.', 'bad');

  $('#go').disabled = true;
  $('#go').innerHTML = '<span class="spinner"></span> Starting';
  try {
    const { submission_id } = await apiPost('/api/run', { rows, models });
    // The eval page defaults to whatever was last started here.
    localStorage.setItem('auditor.lastSubmission', submission_id);
    $('#placeholder').hidden = true;
    $('#progress').hidden = false;
    $('#report').hidden = false;
    startPolling(submission_id);
  } catch (e) {
    noticeText($('#error'), e.message, 'bad');
    resetButton();
  }
}

function resetButton() {
  $('#go').disabled = false;
  $('#go').textContent = 'Run audit';
}

function startPolling(subId) {
  clearInterval(poller);
  const tick = async () => {
    let sub;
    try {
      sub = await apiGet(`/api/submission/${encodeURIComponent(subId)}`);
    } catch (e) {
      noticeText($('#error'), e.message, 'bad');
      return;
    }
    render(sub);
    if (sub.finished >= sub.total) {
      clearInterval(poller);
      poller = null;
      resetButton();
    }
  };
  tick();
  poller = setInterval(tick, POLL_MS);
}

/* ---- rendering ---- */

const JOB_BADGE = {
  queued: () => badge('neutral', '', 'queued'),
  running: () => `<span class="badge accent"><span class="spinner" style="width:9px;height:9px;border-width:1.5px"></span>running</span>`,
  done: () => badge('good', '✓', 'done'),
  error: () => badge('critical', '✕', 'error'),
};

function renderProgress(sub) {
  const pct = sub.total ? Math.round((sub.finished / sub.total) * 100) : 0;
  const done = sub.finished >= sub.total;
  $('#progress-badge').innerHTML = done
    ? badge('good', '✓', `${sub.total} of ${sub.total} finished`)
    : `<span class="badge accent"><span class="spinner" style="width:9px;height:9px;border-width:1.5px"></span>${sub.finished} of ${sub.total}</span>`;

  $('#progress-head').innerHTML = `<div class="muted" style="font-size:13px">
      Submission <span class="mono">${esc(sub.submission_id)}</span> ·
      started ${esc(shortTime(sub.started_at))} ·
      ${esc(sub.mode)} mode ·
      <a href="${API}/submission/${encodeURIComponent(sub.submission_id)}" target="_blank" rel="noopener">full report ↗</a>
    </div>`;
  $('#progress-bar').style.width = pct + '%';

  $('#jobs').innerHTML = sub.jobs.map((j) => {
    const row = sub.rows[j.row] || {};
    const state = j.error ? 'error' : j.status;
    return `<div class="jobrow">
      ${JOB_BADGE[state] ? JOB_BADGE[state]() : badge('neutral', '', state)}
      <span class="model">${esc(j.model)}</span>
      <span class="what">${j.row + 1}. ${esc(row.task || row.url || '')}</span>
      <span class="meta">${esc(j.error || (j.run ? `${j.run.steps} steps · ${j.run.wall_seconds}s` : ''))}</span>
    </div>`;
  }).join('');
}

/** KPI row over the whole submission. Headline numbers, so stat tiles rather than a chart.

    Counted over one representative run per task — the first that finished — never over every
    run. Two models auditing the same shop find the same charge; summing across them would
    report one hidden fee twice. Charges and discounts are also kept apart: a misleading "₹100
    off" that only takes ₹40 is a finding with a negative amount, and letting it net against a
    real fee would understate what the shopper was charged. */
function renderSummary(sub) {
  const runs = sub.jobs.map((j) => j.run).filter(Boolean);
  if (!runs.length) { $('#summary').innerHTML = ''; return; }

  const perTask = sub.rows.map((_, i) => (sub.jobs.find((j) => j.row === i && j.run) || {}).run).filter(Boolean);
  const site = perTask.flatMap((r) => (r.findings || []).filter((f) => f.attribution !== 'agent'));
  const charges = site.filter((f) => Number(f.amount) > 0);
  const discounts = site.filter((f) => Number(f.amount) < 0);
  const added = charges.reduce((a, f) => a + Number(f.amount), 0);
  const affected = perTask.filter((r) => (r.findings || []).some((f) => f.attribution !== 'agent')).length;

  const stopped = runs.filter((r) => !r.attempted_payment).length;
  const scored = runs.filter((r) => r.scored);
  const cleared = scored.filter((r) => r.level_cleared).length;

  $('#summary').innerHTML = `<div class="stats">
    <div class="stat"><div class="label">Tasks audited</div><div class="value">${perTask.length}</div>
      <div class="delta">${runs.length} of ${sub.total} runs finished</div></div>

    <div class="stat"><div class="label">Tasks with findings</div><div class="value">${affected}<span class="muted" style="font-size:15px"> / ${perTask.length}</span></div>
      <div class="delta ${affected ? 'up' : 'flat'}">${affected ? 'hid something from the shopper' : 'all clean'}</div></div>

    <div class="stat primary"><div class="label">Unchosen charges</div><div class="value">${rs(added)}</div>
      <div class="delta ${added > 0 ? 'up' : 'flat'}">${charges.length
        ? `${charges.length} charge${charges.length === 1 ? '' : 's'} the shopper never picked`
        : 'nothing added to the bill'}</div></div>

    ${discounts.length ? `<div class="stat"><div class="label">Misleading discounts</div><div class="value">${discounts.length}</div>
      <div class="delta up">claimed more than they took off</div></div>` : ''}

    <div class="stat"><div class="label">Stopped before paying</div><div class="value">${stopped}<span class="muted" style="font-size:15px"> / ${runs.length}</span></div>
      <div class="delta ${stopped === runs.length ? 'flat' : 'up'}">${stopped === runs.length ? 'no payment attempted' : 'a run tried to pay'}</div></div>

    ${scored.length ? `<div class="stat"><div class="label">Levels cleared</div><div class="value">${cleared}<span class="muted" style="font-size:15px"> / ${scored.length}</span></div>
      <div class="delta">runs scored against answer keys</div></div>` : ''}
  </div>`;
}

/** One report section per task row, with every model that ran it. */
function renderResults(sub) {
  $('#results').innerHTML = sub.rows.map((row, i) => {
    const jobs = sub.jobs.filter((j) => j.row === i);
    const finished = jobs.filter((j) => j.run);
    const body = finished.length
      ? finished.map((j) => runBlock(j.run, jobs.length > 1)).join('')
      : `<div class="run"><span class="muted"><span class="spinner"></span>
         waiting for ${jobs.length} run${jobs.length > 1 ? 's' : ''}…</span></div>`;
    const name = storeNames.get(row.store_id) || (row.store_id ? row.store_id.toUpperCase() : 'Live site');
    return `<article class="task-card">
      <header>
        <span class="idx">${i + 1}</span>
        <span class="shop">${esc(name)}</span>
        ${row.level ? badge('outline', '', `L${row.level}`) : badge('outline', '', 'no answer key')}
        ${row.headed ? badge('accent', '◉', 'shown') : ''}
        <span class="sentence">${esc(row.task)}</span>
        <a class="mono muted" style="font-size:12px" href="${esc(row.url)}" target="_blank" rel="noopener">↗</a>
      </header>
      ${body}
    </article>`;
  }).join('');
}

/** First price → final total, the findings, and the one-line verdict for a single run. */
function runBlock(run, showModel) {
  const site = (run.findings || []).filter((f) => f.attribution !== 'agent');
  const agent = (run.findings || []).filter((f) => f.attribution === 'agent');
  const first = Number(run.first_price_total);
  const final = Number(run.final_total);
  const change = Number.isFinite(first) && Number.isFinite(final) ? final - first : null;

  const findings = site.length
    ? `<div class="table-wrap"><table class="data">
        <thead><tr><th>Charge the shopper never chose</th><th>Pattern</th><th class="num">Amount</th></tr></thead>
        <tbody>${site.map((f) => `<tr>
          <td class="strong">${esc(f.label)}${f.evidence ? `<span class="sub">${esc(f.evidence)}</span>` : ''}</td>
          <td>${badge('warning', '▲', f.pattern || checkLabel(f.check))}</td>
          <td class="num strong">${rs(f.amount)}</td>
        </tr>`).join('')}</tbody>
      </table></div>`
    : `<div class="notice good" style="margin:0"><span class="g" aria-hidden="true">✓</span>
       <span>No hidden charges. Every line in the final bill was visible up front or chosen by the shopper.</span></div>`;

  const cleared = run.scored && run.level_cleared;
  const verdictKind = run.scored ? (cleared ? 'good' : 'bad') : 'none';
  const verdictGlyph = run.scored ? (cleared ? '✓' : '✕') : 'ⓘ';
  const verdict = run.scored
    ? esc(run.verdict_line || '')
    : `Unscored — no answer key for this store. ${site.length} finding${site.length === 1 ? '' : 's'} flagged for review.`;

  return `<div class="run">
    <div class="run-head">
      ${showModel ? `<span class="model">${esc(run.model)}</span>` : ''}
      <span class="spacer"></span>
      <span class="run-meta">${run.steps ?? '—'} steps · ${run.wall_seconds ?? '—'}s</span>
      ${run.attempted_payment ? badge('critical', '✕', 'attempted payment') : badge('good', '✓', 'stopped before payment')}
    </div>

    <div class="pricepair" style="margin-bottom:14px">
      <span class="leg"><span class="label">First price seen</span><span class="amount">${rs(run.first_price_total)}</span></span>
      <span class="to" aria-hidden="true">→</span>
      <span class="leg"><span class="label">Final total before paying</span>
        <span class="amount ${change > 0 ? 'up' : ''}">${rs(run.final_total)}</span></span>
      ${change !== null && change !== 0
        ? `<span class="leg"><span class="label">Change</span>
             <span class="amount ${change > 0 ? 'up' : ''}" style="font-size:16px">${rsDelta(change)}</span></span>`
        : ''}
    </div>

    ${findings}
    ${agent.length ? `<div class="notice warn" style="margin:12px 0 0"><span class="g" aria-hidden="true">▲</span>
      <span>The agent added these itself, not the site: ${agent.map((f) => `${esc(f.label)} ${rs(f.amount)}`).join(', ')}.</span></div>` : ''}
    ${run.gap ? `<div class="muted" style="margin-top:10px;font-size:12.5px">${esc(run.gap)}</div>` : ''}
    <div class="verdict ${verdictKind}"><span class="g" aria-hidden="true">${verdictGlyph}</span><span>${verdict}</span></div>
  </div>`;
}

function render(sub) {
  renderProgress(sub);
  renderSummary(sub);
  renderResults(sub);
}

/* ---- wiring ---- */

$('#add-store').addEventListener('click', () => { addStore().querySelector('.url').focus(); updateNote(); });
$('#clear').addEventListener('click', () => { $('#stores').innerHTML = ''; renumber(); updateNote(); });
$('#go').addEventListener('click', go);
$('#stores').addEventListener('input', updateNote);
$('#stores').addEventListener('change', updateNote);
$('#models').addEventListener('change', updateNote);

/** Seeded stores, cached: used to fill the rows and to name them in the report. */
async function loadStores() {
  const { stores } = await apiGet('/api/stores');
  stores.forEach((s) => { if (s.name) storeNames.set(s.store_id, s.name); });
  return stores;
}

$('#load-stores').addEventListener('click', async () => {
  try {
    const stores = await loadStores();
    $('#stores').innerHTML = '';
    stores.forEach((s) => addStore(s.url, [s.task]));
    renumber();
    updateNote();
  } catch (e) {
    noticeText($('#error'), e.message, 'bad');
  }
});

(async function init() {
  addStore();
  await checkHealth($('#side-status'), $('#health'));
  await loadModels();
  await loadStores().catch(() => {});  // names are a nicety; a failure here must not block a run
  // Deep link: index.html?submission=<id> reopens a submission started earlier.
  const sub = new URLSearchParams(location.search).get('submission');
  if (sub) {
    $('#placeholder').hidden = true;
    $('#progress').hidden = false;
    $('#report').hidden = false;
    startPolling(sub);
  }
})();
