/* Page 2 — eval.

   Pre-loads the runs from the last audit started on page 1, pairs each with its store's answer
   key, and POSTs the pairs to /api/score. The backend scores them with the same score_run the
   batch uses — this page never scores anything itself, it only lays the answer out: what the
   store seeded, what the agent reported, and expected − reported for both totals.

   A run with no answer key (a real site) comes back unscored and is shown as such. */

let allRuns = [];
let storesWithKeys = new Set();
/** run file -> task sentence. /api/score does not return the task, but two runs of the same
    store and model now differ only by it, so the panels look up their own. */
const taskByFile = new Map();
const taskLine = (f) => (taskByFile.get(f)
  ? `<div class="task-line" title="${esc(taskByFile.get(f))}">${esc(taskByFile.get(f))}</div>` : '');
let defaultPairs = [];
let overrides = new Map(); // run_file -> key_file|null

/* ---- choosing what to score ---- */

/** Pair runs with their store's answer key, grouped by store.

    collapse=true keeps only the latest run per model per store — what the whole-history view
    wants, and what default_pairs() in web/app.py does. For a single submission it is wrong:
    several tasks on one store share a (store, model) key, so collapsing would silently drop
    every task but the last. A chosen batch is scored run for run. */
function pairsFor(runs, collapse) {
  const byStore = new Map();
  runs.forEach((r) => {
    if (!r.store_id) return;
    if (!byStore.has(r.store_id)) byStore.set(r.store_id, []);
    byStore.get(r.store_id).push(r);
  });
  const pairs = [];
  [...byStore.keys()].sort((a, b) => a.length - b.length || a.localeCompare(b)).forEach((store) => {
    const key_file = storesWithKeys.has(store) ? `${store}.json` : null;
    const inStore = byStore.get(store).slice()
      .sort((a, b) => String(a.started_at).localeCompare(String(b.started_at)));
    if (collapse) {
      const latest = new Map();
      inStore.forEach((r) => latest.set(r.model, r));
      [...latest.keys()].sort().forEach((m) => pairs.push({ run_file: latest.get(m).file, key_file }));
    } else {
      inStore.forEach((r) => pairs.push({ run_file: r.file, key_file }));
    }
  });
  return pairs;
}

function activePairs() {
  const pairs = defaultPairs.filter((p) => !overrides.has(p.run_file));
  overrides.forEach((key_file, run_file) => pairs.push({ run_file, key_file }));
  return pairs;
}

function updateNotes() {
  const n = activePairs().length;
  $('#pair-note').textContent = n ? `${n} run${n === 1 ? '' : 's'} selected` : 'nothing selected';
  $('#override-list').innerHTML = overrides.size
    ? [...overrides].map(([r, k]) => `<div class="jobrow">
        ${badge('accent', '⇄', 'override')}
        <span class="what mono" style="font-size:12px">${esc(r)} → ${esc(k || 'no key')}</span>
        <button class="ghost sm drop" data-run="${esc(r)}" type="button">remove</button></div>`).join('')
    : '<span class="muted" style="font-size:13px">No overrides — scoring the batch above.</span>';
}

/* ---- rendering ---- */

/** One model's verdict on one store: seeded vs found, then expected − reported for both totals. */
function panel(r) {
  if (r.unscored) {
    return `<div class="panel">
      <header><span class="model">${esc(r.model || r.run_file)}</span>
        ${badge('neutral', 'ⓘ', 'unscored')}</header>
      <div class="panel-body">
        <div class="muted" style="font-size:12.5px">${esc(shortTime(r.started_at))} · ${esc(r.run_file)}</div>
        ${taskLine(r.run_file)}
        <div class="verdict none" style="margin-top:10px"><span class="g" aria-hidden="true">ⓘ</span>
          <span>${esc(r.reason || 'no answer key')}</span></div>
      </div></div>`;
  }
  const s = r.score, k = r.key;
  const site = (r.findings || []).filter((f) => f.attribution === 'site');
  const agent = (r.findings || []).filter((f) => f.attribution === 'agent');
  const seeded = (k.seeded || []).map((t) => `${esc(t.label)} <span class="num">${rs(t.amount)}</span>`).join(', ') || '<span class="muted">none</span>';
  const found = site.map((f) => `${esc(f.label)} <span class="num">${rs(f.amount)}</span>`).join(', ') || '<span class="muted">none</span>';
  const stopped = s.completed && !s.attempted_payment;

  // caught/seeded is one ratio against a limit, so a meter rather than a chart.
  const ratio = s.seeded ? s.caught / s.seeded : 1;
  const meterKind = !s.seeded ? 'empty' : ratio >= 1 ? 'full' : ratio > 0 ? 'short' : 'short';

  return `<div class="panel">
    <header>
      <span class="model">${esc(r.model)}</span>
      ${badge('outline', '', r.mode)}
      ${s.level_cleared ? badge('good', '✓', 'cleared') : badge('critical', '✕', 'not cleared')}
    </header>
    <div class="panel-body">
      <div class="muted" style="font-size:12px;margin-bottom:12px">
        ${esc(shortTime(r.started_at))} · <span class="mono">${esc(r.run_file)}</span>
      </div>
      ${taskLine(r.run_file)}

      <div style="margin-bottom:12px">
        <div style="display:flex;justify-content:space-between;font-size:12.5px;margin-bottom:5px">
          <span class="muted">Traps caught</span>
          <span class="num"><b>${s.caught}</b> of ${s.seeded}</span>
        </div>
        <div class="meter ${meterKind}"><i style="width:${s.seeded ? Math.round(ratio * 100) : 100}%"></i></div>
      </div>

      <dl style="margin:0">
        <div class="kv"><dt>Seeded</dt><dd>${seeded}</dd></div>
        <div class="kv"><dt>Found</dt><dd>${found}${agent.length
          ? `<div class="muted" style="font-size:12px;margin-top:2px">agent's own: ${agent.map((f) => esc(f.label)).join(', ')}</div>` : ''}</dd></div>
        ${(s.missed_traps || []).length
          ? `<div class="kv"><dt>Missed</dt><dd class="no">${esc(s.missed_traps.join(', '))}</dd></div>` : ''}
        <div class="kv"><dt>False alarms</dt><dd>${s.false_alarms === 0 ? '<span class="ok">0</span>'
          : `<span class="no">${s.false_alarms}</span>${(s.false_alarm_labels || []).length ? ` <span class="muted">(${esc(s.false_alarm_labels.join(', '))})</span>` : ''}`}</dd></div>
        ${deltaRow('First price', s.expected_first_price_total, s.first_price_total)}
        ${deltaRow('Final total', s.expected_final_total, s.final_total)}
        <div class="kv"><dt>Stopped at Pay</dt><dd>${stopped ? '<span class="ok">✓ yes</span>' : '<span class="no">✕ no</span>'}
          ${s.attempted_payment ? '<span class="no"> — attempted payment</span>' : ''}</dd></div>
        <div class="kv"><dt>Cost</dt><dd class="muted num">${s.steps ?? '—'} steps · ${s.wall_seconds ?? '—'}s · $${(s.cost_usd ?? 0).toFixed(3)}</dd></div>
      </dl>

      <div class="verdict ${s.level_cleared ? 'good' : 'bad'}">
        <span class="g" aria-hidden="true">${s.level_cleared ? '✓' : '✕'}</span>
        <span>${esc(s.verdict_line || '')}</span></div>
    </div></div>`;
}

/** expected − reported, the "error" line. Zero is the pass case and is shown as such. */
function deltaRow(label, expected, reported) {
  const e = Number(expected), a = Number(reported);
  const known = Number.isFinite(e) && Number.isFinite(a);
  const d = known ? e - a : null;
  const zero = known && Math.abs(d) < 0.005;
  return `<div class="kv"><dt>${esc(label)}</dt><dd><div class="deltaline">
    <span class="exp">${rs(reported)} <span class="muted">vs ${rs(expected)} expected</span></span>
    <span class="err ${known ? (zero ? 'zero' : 'off') : 'muted'}">${known ? (zero ? '✓ exact' : `✕ off by ${rsDelta(d)}`) : '—'}</span>
  </div></dd></div>`;
}

function renderSummary(results) {
  const scored = results.filter((r) => !r.unscored);
  if (!scored.length) { $('#eval-summary').innerHTML = ''; return; }
  const caught = scored.reduce((a, r) => a + (r.score.caught || 0), 0);
  const seeded = scored.reduce((a, r) => a + (r.score.seeded || 0), 0);
  const fa = scored.reduce((a, r) => a + (r.score.false_alarms || 0), 0);
  const cleared = scored.filter((r) => r.score.level_cleared).length;
  const exact = scored.filter((r) => Math.abs((r.score.expected_final_total || 0) - (r.score.final_total || 0)) < 0.005).length;

  $('#eval-summary').innerHTML = `<div class="stats">
    <div class="stat"><div class="label">Runs scored</div><div class="value">${scored.length}</div>
      <div class="delta">${results.length - scored.length} unscored</div></div>
    <div class="stat"><div class="label">Traps caught</div><div class="value">${caught}/${seeded}</div>
      <div class="delta ${caught === seeded ? 'flat' : 'up'}">${caught === seeded ? 'all seeded traps found' : `${seeded - caught} missed`}</div></div>
    <div class="stat"><div class="label">False alarms</div><div class="value">${fa}</div>
      <div class="delta ${fa ? 'up' : 'flat'}">${fa ? 'charges flagged that were not traps' : 'nothing over-reported'}</div></div>
    <div class="stat"><div class="label">Totals exact</div><div class="value">${exact}/${scored.length}</div>
      <div class="delta ${exact === scored.length ? 'flat' : 'up'}">final total matched the key</div></div>
    <div class="stat primary"><div class="label">Levels cleared</div><div class="value">${cleared}/${scored.length}</div>
      <div class="delta">caught all, no false alarms, stopped at Pay</div></div>
  </div>`;
}

function renderResults(results) {
  const groups = new Map();
  results.forEach((r) => {
    const g = r.store_id || '—';
    if (!groups.has(g)) groups.set(g, []);
    groups.get(g).push(r);
  });
  const order = [...groups.keys()].sort((a, b) => a.length - b.length || a.localeCompare(b));
  $('#scored').hidden = false;
  $('#placeholder').hidden = true;
  renderSummary(results);
  $('#results').innerHTML = order.map((g) => {
    const rs_ = groups.get(g);
    const name = (rs_.find((x) => x.key) || {}).key?.name || g;
    const lvl = rs_[0].level;
    return `<div class="section-head" style="margin-top:20px">
        <h3 style="font-size:14px">${esc(name)}</h3>
        ${lvl ? badge('outline', '', `L${esc(lvl)}`) : badge('outline', '', esc(g))}
        <span class="rule"></span></div>
      <div class="grid">${rs_.map(panel).join('')}</div>`;
  }).join('');
}

/* ---- the comparison table (how each model did overall) ---- */

/** cleared/runs on the divergence cells for one model. Blank when the backend predates the field
    or nothing diverged — an empty suite is not a zero score. */
function divCell(div, model) {
  const t = div && div.totals && div.totals[model];
  if (!t || !t.runs) return '<span class="muted">—</span>';
  const pct = t.cleared / t.runs;
  const kind = pct >= 0.75 ? 'ok' : pct <= 0.25 ? 'no' : '';
  return `<span class="${kind}">${t.cleared}/${t.runs}</span>`;
}

function renderComparison(ev) {
  $('#cmp-card').hidden = false;
  $('#cmp-title').textContent = ev.title || 'Model comparison';
  if (!ev.rows || !ev.rows.length) {
    $('#cmp').innerHTML = '<div class="muted">No measured runs yet — the table only counts prod runs.</div>';
    return;
  }
  const levels = ev.levels || [];
  // Divergence comes from the same divergence_suite that writes report/eval.md, so this
  // column and the committed table cannot disagree. Absent on an older backend.
  const div = ev.divergence && ev.divergence.cells ? ev.divergence : null;
  // Sixteen levels all carry meaning, so this stays a table rather than becoming a chart.
  const head = `<tr><th>Model</th><th class="num">Runs</th><th class="num">Highest cleared</th>
    <th class="num">Caught/seeded</th><th class="num">False alarms L1</th><th class="num">Stopped at Pay</th>
    <th class="num">Completed</th>
    <th class="num" title="Cleared/runs over only the cells where the models disagreed. Selected by outcome, so not a pass rate.">Divergence${div ? ` <span class="muted">(${div.cells})</span>` : ''}</th>
    <th class="num">Avg steps</th><th class="num">Avg s</th><th class="num">Avg $</th>
    ${levels.map((l) => `<th class="num">L${esc(l)}</th>`).join('')}</tr>`;

  // Key names come straight from comparison_rows in report/build_report.py: highest, fa_l1,
  // stopped and completed already arrive as display strings ("8/8", "0 (n=1)").
  const body = ev.rows.map((r) => {
    const per = (ev.per_level || {})[r.model] || {};
    return `<tr>
      <td class="mono">${esc(r.model)}</td>
      <td class="num">${esc(r.runs)}</td>
      <td class="num strong">${esc(r.highest)}</td>
      <td class="num">${esc(r.caught)}/${esc(r.seeded)}</td>
      <td class="num">${esc(r.fa_l1)}</td>
      <td class="num">${esc(r.stopped)}</td>
      <td class="num">${esc(r.completed)}</td>
      <td class="num">${divCell(div, r.model)}</td>
      <td class="num">${esc(r.steps)}</td>
      <td class="num">${esc(r.seconds)}</td>
      <td class="num">${esc(r.cost)}</td>
      ${levels.map((l) => {
        const c = per[String(l)] || per[l] || { cleared: 0, runs: 0 };
        if (!c.runs) return '<td class="num muted">—</td>';
        const all = c.cleared === c.runs;
        return `<td class="num ${all ? 'ok' : 'no'}">${all ? '✓ ' : '✕ '}${c.cleared}/${c.runs}</td>`;
      }).join('')}
    </tr>`;
  }).join('');

  const limits = (ev.limits || []).map((l) => `<li>${esc(l)}</li>`).join('');
  $('#cmp').innerHTML = `
    <div class="table-wrap" style="border:1px solid var(--line)"><table class="data pinned">
      <thead>${head}</thead><tbody>${body}</tbody></table></div>
    <p class="muted" style="margin:10px 0 0;font-size:12.5px">
      ${ev.prod_runs} measured runs counted; ${ev.test_runs_excluded} debug run${ev.test_runs_excluded === 1 ? '' : 's'} excluded.
      Pass rates are shown as cleared/runs, never a single run presented as a rate.</p>
    ${div ? `<p class="muted" style="margin:6px 0 0;font-size:12.5px"><b>Divergence</b> covers the
      ${div.cells} cell${div.cells === 1 ? '' : 's'} (one store x one task wording) where at least one
      model cleared and at least one failed${div.hard_cells ? `, with ${div.hard_cells} further cell${div.hard_cells === 1 ? '' : 's'} no model cleared` : ''}.
      Those cells are picked by outcome, so the column shows where the models separate — it is not a
      pass rate and does not belong on a slide as one.</p>` : ''}
    ${limits ? `<details class="disclose"><summary>Honest limits</summary><ul>${limits}</ul></details>` : ''}
    <details class="disclose"><summary>Reproducibility block</summary>
      <pre>${esc(JSON.stringify(ev.reproducibility || {}, null, 1))}</pre></details>`;
}

/* ---- actions ---- */

async function score() {
  const pairs = activePairs();
  notice($('#error'), '');
  if (!pairs.length) return noticeText($('#error'), 'Nothing to score — pick a batch with at least one run.', 'bad');

  $('#go').disabled = true;
  $('#go').innerHTML = '<span class="spinner"></span> Scoring';
  $('#placeholder').hidden = true;
  $('#scored').hidden = false;
  $('#results').innerHTML = `<div class="empty"><span class="spinner"></span>
    <div class="t" style="margin-top:10px">Scoring ${pairs.length} run${pairs.length === 1 ? '' : 's'}…</div></div>`;
  try {
    const { results } = await apiPost('/api/score', { pairs });
    renderResults(results);
  } catch (e) {
    noticeText($('#error'), e.message, 'bad');
    $('#results').innerHTML = '<div class="empty"><span class="g">✕</span><div class="t">Scoring failed</div></div>';
  }
  $('#go').disabled = false;
  $('#go').textContent = 'Score';

  try {
    renderComparison(await apiGet('/api/eval'));
  } catch {
    $('#cmp-card').hidden = true; // the comparison is a bonus; a failure here must not hide the scores
  }
}

async function loadSources() {
  const [{ runs }, { stores }] = await Promise.all([apiGet('/api/runs'), apiGet('/api/stores')]);
  allRuns = runs;
  runs.forEach((r) => { if (r.file && r.task) taskByFile.set(r.file, r.task); });
  storesWithKeys = new Set(stores.map((s) => s.store_id));

  const subs = [...new Set(runs.map((r) => r.submission).filter(Boolean))].sort().reverse();
  const preferred = new URLSearchParams(location.search).get('submission')
    || localStorage.getItem('auditor.lastSubmission');
  const chosen = subs.includes(preferred) ? preferred : (subs[0] || '__all__');

  $('#batch').innerHTML = [
    `<option value="__all__">Every store — latest run per model</option>`,
    ...subs.map((s) => {
      const n = runs.filter((r) => r.submission === s).length;
      const mine = s === preferred ? ' — from your last audit' : '';
      return `<option value="${esc(s)}"${s === chosen ? ' selected' : ''}>${esc(s)} · ${n} run${n === 1 ? '' : 's'}${mine}</option>`;
    }),
  ].join('');
  if (chosen === '__all__') $('#batch').value = '__all__';

  $('#runsel').innerHTML = runs.map((r) => `<option value="${esc(r.file)}">${esc(r.file)}</option>`).join('');
  $('#keysel').innerHTML = ['<option value="">— no key (unscored) —</option>',
    ...stores.map((s) => `<option value="${esc(s.store_id)}.json">${esc(s.store_id)}.json — ${esc(s.name)}</option>`)].join('');

  rebuildDefault();
}

function rebuildDefault() {
  const sel = $('#batch').value;
  const everything = sel === '__all__';
  const pool = everything ? allRuns : allRuns.filter((r) => r.submission === sel);
  defaultPairs = pairsFor(pool, everything);
  updateNotes();
}

/* ---- wiring ---- */

$('#go').addEventListener('click', score);
$('#batch').addEventListener('change', () => { overrides.clear(); rebuildDefault(); });
$('#reset').addEventListener('click', () => { overrides.clear(); rebuildDefault(); score(); });
$('#add-override').addEventListener('click', () => {
  const run_file = $('#runsel').value;
  if (run_file) overrides.set(run_file, $('#keysel').value || null);
  updateNotes();
});
$('#override-list').addEventListener('click', (e) => {
  const b = e.target.closest('.drop');
  if (b) { overrides.delete(b.dataset.run); updateNotes(); }
});

(async function init() {
  await checkHealth($('#side-status'), $('#health'));
  try {
    await loadSources();
    if (defaultPairs.length) score();  // pre-loaded: the demo is one press of Score, or none at all
  } catch (e) {
    noticeText($('#error'), e.message, 'bad');
  }
})();
