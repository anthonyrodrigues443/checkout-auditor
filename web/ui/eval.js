/* Page 2 — eval.

   Pre-loads the runs from the last audit started on page 1, pairs each with its store's answer
   key, and POSTs the pairs to /api/score. The backend scores them with the same score_run the
   batch uses — this page never scores anything itself, it only lays the answer out: what the
   store seeded, what the agent reported, and expected − reported for both totals.

   A run with no answer key (a real site) comes back unscored and is shown as such. */

let allRuns = [];
let storesWithKeys = new Set();
let defaultPairs = [];
let overrides = new Map(); // run_file -> key_file|null

/* ---- choosing what to score ---- */

/** Latest run per model for each store in a set of runs, paired with that store's key. */
function pairsFor(runs) {
  const byStore = new Map();
  runs.forEach((r) => {
    if (!r.store_id) return;
    if (!byStore.has(r.store_id)) byStore.set(r.store_id, []);
    byStore.get(r.store_id).push(r);
  });
  const pairs = [];
  [...byStore.keys()].sort((a, b) => a.length - b.length || a.localeCompare(b)).forEach((store) => {
    const latest = new Map();
    byStore.get(store)
      .slice()
      .sort((a, b) => String(a.started_at).localeCompare(String(b.started_at)))
      .forEach((r) => latest.set(r.model, r));
    [...latest.keys()].sort().forEach((m) => {
      pairs.push({ run_file: latest.get(m).file, key_file: storesWithKeys.has(store) ? `${store}.json` : null });
    });
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
  $('#pair-note').textContent = n ? `${n} run${n === 1 ? '' : 's'} queued for scoring` : 'nothing selected';
  $('#override-list').innerHTML = overrides.size
    ? [...overrides].map(([r, k]) => `<div class="mono">${esc(r)} → ${esc(k || 'no key')}
        <button class="ghost small drop" data-run="${esc(r)}" type="button">remove</button></div>`).join('')
    : '<span class="muted">no overrides — using the batch above</span>';
}

/* ---- rendering ---- */

/** One model's verdict on one store: seeded vs found, then expected − reported for both totals. */
function panel(r) {
  if (r.unscored) {
    return `<div class="panel">
      <h3>${esc(r.model || r.run_file)}</h3>
      <div class="muted">${esc(shortTime(r.started_at))} · ${esc(r.run_file)}</div>
      <div class="verdict none" style="margin-top:10px">unscored — ${esc(r.reason || 'no answer key')}</div>
    </div>`;
  }
  const s = r.score, k = r.key;
  const seeded = (k.seeded || []).map((t) => `${esc(t.label)} ${rs(t.amount)}`).join(', ') || 'none';
  const site = (r.findings || []).filter((f) => f.attribution === 'site');
  const agent = (r.findings || []).filter((f) => f.attribution === 'agent');
  const found = site.map((f) => `${esc(f.label)} ${rs(f.amount)}`).join(', ') || 'none';
  const stopped = s.completed && !s.attempted_payment;

  const firstDelta = deltaRow('First price', s.expected_first_price_total, s.first_price_total);
  const finalDelta = deltaRow('Final total', s.expected_final_total, s.final_total);

  return `<div class="panel">
    <h3>${esc(r.model)}</h3>
    <div class="muted" style="margin-bottom:10px">
      <span class="tag">${esc(r.mode)}</span> ${esc(shortTime(r.started_at))} · <span class="mono">${esc(r.run_file)}</span>
    </div>

    <div class="kv"><b>seeded</b><span>${s.seeded}: ${seeded}</span></div>
    <div class="kv"><b>found</b><span>${found}${agent.length ? ` <span class="agent-err">(agent's own: ${agent.map((f) => esc(f.label)).join(', ')})</span>` : ''}</span></div>
    <div class="kv"><b>caught</b><span>${s.caught}/${s.seeded}${(s.missed_traps || []).length ? ` <span class="fail">missed ${esc(s.missed_traps.join(', '))}</span>` : ''}</span></div>
    <div class="kv"><b>false alarms</b><span>${s.false_alarms}${(s.false_alarm_labels || []).length ? ` (${esc(s.false_alarm_labels.join(', '))})` : ''}</span></div>

    ${firstDelta}
    ${finalDelta}

    <div class="kv"><b>stopped at Pay</b><span>${yesno(stopped)}${s.attempted_payment ? ' <span class="fail">attempted payment</span>' : ''}</span></div>
    <div class="kv"><b>steps · time · cost</b><span class="muted">${s.steps ?? '—'} · ${s.wall_seconds ?? '—'}s · $${(s.cost_usd ?? 0).toFixed(3)}</span></div>

    <div class="verdict ${s.level_cleared ? '' : 'fail'}" style="margin-top:12px">${esc(s.verdict_line || '')}</div>
  </div>`;
}

/** expected − reported, the "error" line. Zero is the pass case and is shown as such. */
function deltaRow(label, expected, reported) {
  const e = Number(expected), a = Number(reported);
  const known = Number.isFinite(e) && Number.isFinite(a);
  const d = known ? e - a : null;
  const zero = known && Math.abs(d) < 0.005;
  return `<div class="kv"><b>${esc(label)}</b><span class="delta">
    expected ${rs(expected)} · reported ${rs(reported)} ·
    <span class="${known ? (zero ? 'delta zero' : 'delta nonzero') : 'muted'}">error ${known ? rsDelta(d) : '—'}</span>
  </span></div>`;
}

const yesno = (b) => (b ? '<span class="pass">yes</span>' : '<span class="fail">no</span>');

function renderResults(results) {
  const groups = new Map();
  results.forEach((r) => {
    const g = r.store_id || '—';
    if (!groups.has(g)) groups.set(g, []);
    groups.get(g).push(r);
  });
  const order = [...groups.keys()].sort((a, b) => a.length - b.length || a.localeCompare(b));
  $('#results-heading').hidden = false;
  $('#results').innerHTML = order.map((g) => {
    const rs_ = groups.get(g);
    const name = (rs_.find((x) => x.key) || {}).key?.name || g;
    const lvl = rs_[0].level;
    return `<h3 style="margin:22px 0 10px;font-size:15px">${esc(name)}
      ${lvl ? `<span class="tag">L${esc(lvl)}</span>` : `<span class="tag">${esc(g)}</span>`}</h3>
      <div class="grid">${rs_.map(panel).join('')}</div>`;
  }).join('');
}

/* ---- the comparison table (how each model did overall) ---- */

function renderComparison(ev) {
  $('#cmp-card').hidden = false;
  $('#cmp-title').textContent = ev.title || 'Model comparison';
  if (!ev.rows || !ev.rows.length) {
    $('#cmp').innerHTML = '<div class="muted">No prod runs yet — the table only counts measured runs.</div>';
    return;
  }
  const levels = ev.levels || [];
  const head = `<tr><th>model</th><th>runs</th><th>highest cleared</th><th>caught/seeded</th>
    <th>false alarms L1</th><th>stopped at Pay</th><th>completed</th><th>avg steps</th><th>avg s</th><th>avg $</th>
    ${levels.map((l) => `<th>L${esc(l)}</th>`).join('')}</tr>`;
  // Key names come straight from comparison_rows in report/build_report.py: highest, fa_l1,
  // stopped and completed already arrive as display strings ("8/8", "0 (n=1)").
  const body = ev.rows.map((r) => {
    const per = (ev.per_level || {})[r.model] || {};
    return `<tr>
      <td>${esc(r.model)}</td>
      <td>${esc(r.runs)}</td>
      <td>${esc(r.highest)}</td>
      <td>${esc(r.caught)}/${esc(r.seeded)}</td>
      <td>${esc(r.fa_l1)}</td>
      <td>${esc(r.stopped)}</td>
      <td>${esc(r.completed)}</td>
      <td>${esc(r.steps)}</td>
      <td>${esc(r.seconds)}</td>
      <td>${esc(r.cost)}</td>
      ${levels.map((l) => {
        const c = per[String(l)] || per[l] || { cleared: 0, runs: 0 };
        const cls = !c.runs ? 'muted' : c.cleared === c.runs ? 'pass' : 'fail';
        return `<td class="${cls}">${c.runs ? `${c.cleared}/${c.runs}` : '—'}</td>`;
      }).join('')}
    </tr>`;
  }).join('');

  const limits = (ev.limits || []).map((l) => `<li>${esc(l)}</li>`).join('');
  $('#cmp').innerHTML = `
    <div style="overflow-x:auto"><table class="cmp"><thead>${head}</thead><tbody>${body}</tbody></table></div>
    <p class="muted" style="margin-top:10px">${ev.prod_runs} measured runs counted;
      ${ev.test_runs_excluded} debug run${ev.test_runs_excluded === 1 ? '' : 's'} excluded.
      Pass rates are shown as cleared/runs, never a single run as a rate.</p>
    ${limits ? `<details class="repro"><summary>Honest limits</summary><ul class="muted">${limits}</ul></details>` : ''}
    <details class="repro"><summary>Reproducibility block</summary>
      <pre>${esc(JSON.stringify(ev.reproducibility || {}, null, 1))}</pre></details>`;
}

/* ---- actions ---- */

async function score() {
  const pairs = activePairs();
  banner($('#error'), '');
  if (!pairs.length) return banner($('#error'), 'Nothing to score — pick a batch with at least one run.');

  $('#go').disabled = true;
  $('#results-heading').hidden = false;
  $('#results').innerHTML = `<div class="muted"><span class="spin"></span>scoring ${pairs.length} run(s)…</div>`;
  try {
    const { results } = await apiPost('/api/score', { pairs });
    renderResults(results);
  } catch (e) {
    banner($('#error'), e.message);
    $('#results').innerHTML = '<div class="placeholder">Scoring failed.</div>';
  }
  $('#go').disabled = false;

  try {
    renderComparison(await apiGet('/api/eval'));
  } catch {
    $('#cmp-card').hidden = true; // the comparison is a bonus; a failure here must not hide the scores
  }
}

async function loadSources() {
  const [{ runs }, { stores }] = await Promise.all([apiGet('/api/runs'), apiGet('/api/stores')]);
  allRuns = runs;
  storesWithKeys = new Set(stores.map((s) => s.store_id));

  const subs = [...new Set(runs.map((r) => r.submission).filter(Boolean))].sort().reverse();
  const preferred = new URLSearchParams(location.search).get('submission')
    || localStorage.getItem('auditor.lastSubmission');
  const chosen = subs.includes(preferred) ? preferred : (subs[0] || '__all__');

  $('#batch').innerHTML = [
    `<option value="__all__">Every store — latest run per model</option>`,
    ...subs.map((s) => {
      const n = runs.filter((r) => r.submission === s).length;
      const mine = s === preferred ? ' (from the Audit page)' : '';
      return `<option value="${esc(s)}"${s === chosen ? ' selected' : ''}>${esc(s)} — ${n} run${n === 1 ? '' : 's'}${mine}</option>`;
    }),
  ].join('');
  if (chosen === '__all__') $('#batch').value = '__all__';

  $('#runsel').innerHTML = runs
    .map((r) => `<option value="${esc(r.file)}">${esc(r.file)}</option>`).join('');
  $('#keysel').innerHTML = ['<option value="">— no key (unscored) —</option>',
    ...stores.map((s) => `<option value="${esc(s.store_id)}.json">${esc(s.store_id)}.json — ${esc(s.name)}</option>`)].join('');

  rebuildDefault();
}

function rebuildDefault() {
  const sel = $('#batch').value;
  const pool = sel === '__all__' ? allRuns : allRuns.filter((r) => r.submission === sel);
  defaultPairs = pairsFor(pool);
  $('#batch-note').textContent = `${defaultPairs.length} run${defaultPairs.length === 1 ? '' : 's'}`;
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
  await checkHealth($('#health'));
  try {
    await loadSources();
    if (defaultPairs.length) score();  // pre-loaded: the demo is one press of Score, or none at all
  } catch (e) {
    banner($('#error'), e.message);
  }
})();
