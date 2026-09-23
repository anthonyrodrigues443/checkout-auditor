/* Page 1 — submission.

   Collect (store URL, task sentence, show browser) rows plus a set of models, POST them to
   /api/run, then poll /api/submission/{id} every 3s and render one report section per task as
   its runs finish. Every number shown comes from the run record the backend wrote; this page
   does no arithmetic of its own beyond counting jobs. */

const POLL_MS = 3000;
let rowSeq = 0;
let poller = null;
let currentSub = null;
/** store_id -> shop name, so a task reads "Kirana Direct" rather than "L1" twice. */
const storeNames = new Map();

/* ---- task rows ---- */

function addRow(url = '', task = '', headed = false) {
  const i = ++rowSeq;
  const div = document.createElement('div');
  div.className = 'row';
  div.dataset.row = i;
  div.innerHTML = `
    <span class="n">${$$('#rows .row').length + 1}</span>
    <input type="text" class="url" placeholder="http://localhost:8000/l3/" value="${esc(url)}" aria-label="Store URL">
    <input type="text" class="task" placeholder="Buy one blue ceramic mug with standard delivery." value="${esc(task)}" aria-label="Task">
    <label class="check"><input type="checkbox" class="headed" ${headed ? 'checked' : ''}> show browser</label>
    <button class="ghost icon remove" type="button" title="Remove this task" aria-label="Remove task">×</button>`;
  div.querySelector('.remove').addEventListener('click', () => { div.remove(); renumber(); });
  $('#rows').appendChild(div);
  return div;
}

function renumber() {
  $$('#rows .row').forEach((r, i) => { r.querySelector('.n').textContent = i + 1; });
  if (!$$('#rows .row').length) addRow();
}

function readRows() {
  return $$('#rows .row')
    .map((r) => ({
      url: r.querySelector('.url').value.trim(),
      task: r.querySelector('.task').value.trim(),
      headed: r.querySelector('.headed').checked,
    }))
    .filter((r) => r.url && r.task);
}

/* ---- models ---- */

async function loadModels() {
  const slot = $('#models');
  try {
    const { models } = await apiGet('/api/models');
    slot.innerHTML = models
      .map((m) => `<label class="check"><input type="checkbox" class="model" value="${esc(m)}" checked>
                   <span class="mono">${esc(m)}</span></label>`)
      .join('');
  } catch (e) {
    slot.innerHTML = `<span class="fail">${esc(e.message)}</span>`;
  }
  updateNote();
}

const readModels = () => $$('#models .model:checked').map((c) => c.value);

function updateNote() {
  const rows = readRows().length;
  const models = readModels().length;
  $('#go-note').textContent = rows && models
    ? `${rows} task${rows > 1 ? 's' : ''} × ${models} model${models > 1 ? 's' : ''} = ${rows * models} runs`
    : '';
}

/* ---- launch + poll ---- */

async function go() {
  const rows = readRows();
  const models = readModels();
  banner($('#error'), '');
  if (!rows.length) return banner($('#error'), 'Add at least one row with both a store URL and a task.');
  if (!models.length) return banner($('#error'), 'Tick at least one model.');

  $('#go').disabled = true;
  $('#go').textContent = 'Starting…';
  try {
    const { submission_id } = await apiPost('/api/run', { rows, models });
    currentSub = submission_id;
    // The eval page defaults to whatever was last started here.
    localStorage.setItem('auditor.lastSubmission', submission_id);
    $('#progress').hidden = false;
    $('#results-heading').hidden = false;
    startPolling(submission_id);
  } catch (e) {
    banner($('#error'), e.message);
    $('#go').disabled = false;
    $('#go').textContent = 'Run audit';
  }
}

function startPolling(subId) {
  clearInterval(poller);
  const tick = async () => {
    let sub;
    try {
      sub = await apiGet(`/api/submission/${encodeURIComponent(subId)}`);
    } catch (e) {
      banner($('#error'), e.message);
      return;
    }
    render(sub);
    if (sub.finished >= sub.total) {
      clearInterval(poller);
      poller = null;
      $('#go').disabled = false;
      $('#go').textContent = 'Run audit';
    }
  };
  tick();
  poller = setInterval(tick, POLL_MS);
}

/* ---- rendering ---- */

function renderProgress(sub) {
  const pct = sub.total ? Math.round((sub.finished / sub.total) * 100) : 0;
  const done = sub.finished >= sub.total;
  $('#progress-head').innerHTML = `
    <div class="muted">
      ${done ? '' : '<span class="spin"></span>'}
      submission <span class="mono">${esc(sub.submission_id)}</span>
      · ${sub.finished}/${sub.total} runs finished
      · started ${esc(shortTime(sub.started_at))}
      · mode <span class="tag">${esc(sub.mode)}</span>
      · <a href="${API}/submission/${encodeURIComponent(sub.submission_id)}" target="_blank" rel="noopener">open full report</a>
    </div>`;
  $('#progress-bar').style.width = pct + '%';

  $('#jobs').innerHTML = sub.jobs.map((j) => {
    const row = sub.rows[j.row] || {};
    const state = j.error ? 'error' : j.status;
    const label = j.error ? 'error' : j.status;
    return `<div class="jobline">
      <span class="tag ${state}">${esc(label)}</span>
      <span class="m">${esc(j.model)}</span>
      <span class="t">${j.row + 1}. ${esc(row.task || row.url || '')}</span>
      <span class="muted">${esc(j.error || (j.run ? `${j.run.steps} steps · ${j.run.wall_seconds}s` : ''))}</span>
    </div>`;
  }).join('');
}

/** One report section per task row, with every model that ran it. */
function renderResults(sub) {
  $('#results').innerHTML = sub.rows.map((row, i) => {
    const jobs = sub.jobs.filter((j) => j.row === i);
    const finished = jobs.filter((j) => j.run);
    const body = finished.length
      ? finished.map((j) => runBlock(j.run, jobs.length > 1)).join('')
      : `<div class="muted"><span class="spin"></span>waiting for ${jobs.length} run${jobs.length > 1 ? 's' : ''}…</div>`;
    return `<article class="task">
      <header>
        <span class="name">${i + 1}. ${esc(storeNames.get(row.store_id) || (row.store_id ? row.store_id.toUpperCase() : 'Live site'))}</span>
        ${row.level ? `<span class="tag">L${esc(row.level)}</span>` : '<span class="tag">no answer key</span>'}
        ${row.headed ? '<span class="tag">shown</span>' : ''}
        <span class="task-text">${esc(row.task)}</span>
        <a class="muted mono" href="${esc(row.url)}" target="_blank" rel="noopener">${esc(row.url)}</a>
      </header>
      <div class="body">${body}</div>
    </article>`;
  }).join('');
}

/** First price → final total, the findings, and the one-line verdict for a single run. */
function runBlock(run, showModel) {
  const site = (run.findings || []).filter((f) => f.attribution !== 'agent');
  const agent = (run.findings || []).filter((f) => f.attribution === 'agent');
  const rose = run.final_total != null && run.first_price_total != null && run.final_total > run.first_price_total;

  const findings = site.length
    ? `<table class="findings">
        <thead><tr><th>Charge the shopper never chose</th><th>Pattern</th><th style="text-align:right">Amount</th></tr></thead>
        <tbody>${site.map((f) => `<tr>
          <td>${esc(f.label)}<div class="muted">${esc(f.evidence || '')}</div></td>
          <td class="pat">${esc(f.pattern || checkLabel(f.check))}</td>
          <td class="amt ${Number(f.amount) < 0 ? 'neg' : ''}">${rs(f.amount)}</td>
        </tr>`).join('')}</tbody>
      </table>`
    : '<div class="muted">No hidden charges found. Everything in the final bill was visible up front or chosen by the shopper.</div>';

  const verdictClass = run.scored ? (run.level_cleared ? '' : 'fail') : 'none';
  const verdict = run.scored
    ? esc(run.verdict_line || '')
    : `unscored — no answer key for this store. ${site.length} finding${site.length === 1 ? '' : 's'} flagged for review.`;

  return `
    ${showModel ? `<div class="muted mono" style="margin-bottom:8px">${esc(run.model)}</div>` : ''}
    <div class="prices">
      <div class="price"><span class="lbl">First price seen</span><span class="val">${rs(run.first_price_total)}</span></div>
      <span class="arrow">→</span>
      <div class="price"><span class="lbl">Final total before paying</span><span class="val ${rose ? 'up' : ''}">${rs(run.final_total)}</span></div>
      <span class="spacer" style="flex:1"></span>
      <span class="muted">${run.steps ?? '—'} steps · ${run.wall_seconds ?? '—'}s${run.attempted_payment ? ' · <span class="fail">attempted payment</span>' : ' · stopped before payment'}</span>
    </div>
    ${findings}
    ${agent.length ? `<div class="agent-err">Agent added these itself, not the site: ${agent.map((f) => `${esc(f.label)} ${rs(f.amount)}`).join(', ')}</div>` : ''}
    ${run.gap ? `<div class="muted" style="margin-top:8px">${esc(run.gap)}</div>` : ''}
    <div class="verdict ${verdictClass}">${verdict}</div>`;
}

function render(sub) {
  renderProgress(sub);
  renderResults(sub);
}

/* ---- wiring ---- */

$('#add').addEventListener('click', () => { addRow(); renumber(); updateNote(); });
$('#clear').addEventListener('click', () => { $('#rows').innerHTML = ''; renumber(); updateNote(); });
$('#go').addEventListener('click', go);
$('#rows').addEventListener('input', updateNote);
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
    $('#rows').innerHTML = '';
    stores.forEach((s) => addRow(s.url, s.task, false));
    renumber();
    updateNote();
  } catch (e) {
    banner($('#error'), e.message);
  }
});

(async function init() {
  addRow();
  await checkHealth($('#health'));
  await loadModels();
  await loadStores().catch(() => {});  // names are a nicety; a failure here must not block a run
  // Deep link: index.html?submission=<id> reopens a submission started earlier.
  const sub = new URLSearchParams(location.search).get('submission');
  if (sub) {
    $('#progress').hidden = false;
    $('#results-heading').hidden = false;
    startPolling(sub);
  }
})();
