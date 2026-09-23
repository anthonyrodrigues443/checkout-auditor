"""Build the product audit pages and the internal eval page from everything in runs/.

    .venv/bin/python -m report.build_report
Writes report/audit/<submission>.html (no model names), report/index.html and report/eval.md (model comparison).
"""

from __future__ import annotations

import html
import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = ROOT / "runs"
KEYS_DIR = ROOT / "stores" / "keys"
OUT_DIR = ROOT / "report"
AUDIT_DIR = OUT_DIR / "audit"
sys.path.insert(0, str(ROOT))

from checker.checks import check_run  # noqa: E402
from checker.score import load_key_for, score_run  # noqa: E402

CSS = """
body{font:15px/1.45 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;margin:0;padding:24px;color:#1b1b1b;background:#fafafa;max-width:1180px}
h1{font-size:26px;margin:0 0 6px}h2{font-size:20px;margin:28px 0 8px;border-bottom:2px solid #ddd;padding-bottom:4px}h3{font-size:16px;margin:16px 0 6px}
.card{background:#fff;border:1px solid #e2e2e2;border-radius:8px;padding:16px 18px;margin:14px 0}
.big{font-size:30px;font-weight:700}.arrow{color:#888;font-size:22px;margin:0 10px}.muted{color:#666;font-size:13px}
.finding{border-left:4px solid #d33;padding:6px 10px;margin:6px 0;background:#fff5f5}.finding.ok{border-color:#2a9d3a;background:#f2fbf3}
.finding.agent{border-color:#e8a100;background:#fff9e8}
.tag{display:inline-block;font-size:11px;padding:1px 7px;border-radius:10px;background:#eee;margin-left:6px;color:#333}
table{border-collapse:collapse;width:100%;margin:8px 0}th,td{border:1px solid #ddd;padding:6px 8px;text-align:left;font-size:14px}th{background:#f1f1f1}
.strip{display:flex;overflow-x:auto;gap:8px;padding:8px 0}.strip figure{margin:0;flex:0 0 220px}.strip img{width:220px;border:1px solid #ccc;border-radius:4px}
.strip figcaption{font-size:11px;color:#555;white-space:normal;line-height:1.25}
.panel{background:#f5f7fb;border:1px solid #d8deea;border-radius:6px;padding:10px 12px;margin-top:10px;font-size:14px}
.verdict{font-weight:600;margin-top:6px}.pass{color:#1d7a2b}.fail{color:#b32020}
pre{background:#f4f4f4;padding:10px;border-radius:6px;overflow-x:auto;font-size:13px}
details summary{cursor:pointer;color:#555}
"""


def esc(s) -> str:
    return html.escape("" if s is None else str(s))


def rupees(x) -> str:
    if x is None:
        return "-"
    x = float(x)
    s = f"₹{abs(x):,.0f}" if abs(x - round(x)) < 0.005 else f"₹{abs(x):,.2f}"
    return f"−{s}" if x < 0 else s


def git_time(path: Path) -> str | None:
    try:
        out = subprocess.check_output(["git", "log", "-1", "--format=%ci", "--", str(path)], cwd=ROOT, text=True,
                                      stderr=subprocess.DEVNULL).strip()
        return out or None
    except Exception:
        return None


def load_runs() -> list[dict]:
    runs = []
    for p in sorted(RUNS_DIR.glob("*.json")):
        try:
            r = json.loads(p.read_text())
        except Exception:
            continue
        if not isinstance(r, dict) or "run_id" not in r:
            continue
        r["_file"] = p.name
        runs.append(r)
    return runs


def validator_status() -> dict:
    p = KEYS_DIR / "validation.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return {}
    return {}


def enrich(run: dict) -> dict:
    run["_checks"] = check_run(run)
    key = None
    try:
        key = load_key_for(run, keys_dir=str(KEYS_DIR))
    except TypeError:
        key = load_key_for(run)
    run["_key"] = key
    run["_score"] = score_run(run, key) if key else None
    return run


# ---- per-run audit section (no model names) ---------------------------------------------

def run_section(run: dict, rel_runs: str, internal: bool = False) -> str:
    cp = run.get("checkpoints") or {}
    fp, fin = cp.get("first_price"), cp.get("final")
    checks = run["_checks"]
    findings = checks.get("findings", [])
    site = [f for f in findings if f.get("attribution", "site") == "site"]
    agent_err = [f for f in findings if f.get("attribution") == "agent"]
    store = run.get("store_id", "?")
    key = run.get("_key")
    title = (key or {}).get("name") or run.get("store_url") or store
    started = run.get("started_at", "")
    parts = [f"<div class='card' id='{esc(run['run_id'])}'>"]
    head = f"<h3>{esc(title)} <span class='tag'>{esc(store)}</span>"
    if internal:
        head += f"<span class='tag'>{esc(run.get('model'))}</span><span class='tag'>{esc(run.get('mode'))}</span>"
    if run.get("task_variant") and run.get("task_variant") != "key":
        head += f"<span class='tag'>task: {esc(run.get('task_variant'))}</span>"
    head += f"<span class='tag'>{esc(run.get('status'))}</span></h3>"
    parts.append(head)
    parts.append(f"<div class='muted'>task: {esc(run.get('task'))} · run {esc(started)} · {esc(run.get('wall_seconds'))}s · {esc(run.get('steps'))} steps</div>")
    parts.append("<div style='margin:10px 0'>"
                 f"<span class='muted'>first price</span> <span class='big'>{rupees(fp['total']) if fp else '—'}</span>"
                 f"<span class='arrow'>→</span><span class='muted'>final</span> <span class='big'>{rupees(fin['total']) if fin else '—'}</span></div>")
    if run.get("error"):
        parts.append(f"<div class='finding'>run {esc(run.get('status'))}: {esc(run['error'])}</div>")
    if not fin:
        parts.append("<div class='finding'>no final bill recorded; the audit did not reach the review screen</div>")
    elif not site and not agent_err:
        parts.append("<div class='finding ok'>no issues: every charge in the final bill was visible at the first price or chosen by the shopper</div>")
    for f in site:
        pat = f" <span class='tag'>{esc(f['pattern'])}</span>" if f.get("pattern") else " <span class='tag'>unmapped</span>"
        parts.append(f"<div class='finding'><b>{esc(f.get('label'))}</b> {rupees(f.get('amount'))} · {esc(f.get('check','').replace('_',' '))}{pat}"
                     f"<div class='muted'>{esc(f.get('evidence'))}</div></div>")
    for f in agent_err:
        parts.append(f"<div class='finding agent'><b>{esc(f.get('label'))}</b> {rupees(f.get('amount'))} · added by the agent itself (agent error, not a site finding)</div>")
    gap = checks.get("gap") or {}
    if gap:
        parts.append(f"<div class='muted'>gap first→final {rupees(gap.get('gap'))}; explained by findings {rupees(gap.get('explained'))}; "
                     f"unexplained {rupees(gap.get('unexplained'))}</div>")
    if run.get("attempted_payment"):
        parts.append("<div class='finding'>the agent tried to press a payment button and was blocked by the click tool</div>")
    # ground truth panel
    sc = run.get("_score")
    if key and sc:
        kp = KEYS_DIR / f"{store}.json"
        vs = validator_status().get(store)
        vtxt = "validator: " + (esc(vs.get("status")) + " " + esc(vs.get("at", "")) if isinstance(vs, dict) else "not recorded")
        seeded = [t for t in key.get("traps", []) if t.get("scored")]
        seeded_txt = ", ".join(f"{esc(t['label'])} {rupees(t['amount'])}" for t in seeded) or "none"
        rep_fp = ", ".join(f"{esc(i['label'])} {rupees(i['amount'])}" for i in (fp or {}).get("line_items", [])) or "—"
        rep_fin = ", ".join(f"{esc(i['label'])} {rupees(i['amount'])}" for i in (fin or {}).get("line_items", [])) or "—"
        cls = "pass" if sc.get("level_cleared") else "fail"
        parts.append("<div class='panel'><b>ground truth vs found</b>"
                     f"<div class='muted'>answer key {esc(kp.relative_to(ROOT))} · committed {esc(git_time(kp) or 'uncommitted')} · {vtxt}</div>"
                     f"<div>seeded: {seeded_txt} · expected final {rupees(key.get('expected_final_total'))}</div>"
                     f"<div>reported at first price: {rep_fp} (total {rupees((fp or {}).get('total'))})</div>"
                     f"<div>reported at final: {rep_fin} (total {rupees((fin or {}).get('total'))})</div>"
                     f"<div class='verdict {cls}'>{esc(sc.get('verdict_line'))}</div></div>")
    elif not key:
        parts.append("<div class='panel'>no answer key — unscored</div>")
    # screenshot strip
    shots = [a for a in run.get("actions", []) if a.get("screenshot")]
    if shots:
        parts.append("<div class='strip'>")
        for a in shots:
            cap = f"{a['step']}. {a['tool']}"
            if a.get("element_text"):
                cap += f" “{a['element_text'][:40]}”"
            elif a["tool"] == "record_checkpoint":
                cap += f" {a['args'].get('name')} {rupees(a['args'].get('total'))}"
            if a.get("blocked"):
                cap += " (blocked)"
            cap += f"<br>{a['ts'][11:19]}"
            parts.append(f"<figure><a href='{rel_runs}/{esc(a['screenshot'])}'><img src='{rel_runs}/{esc(a['screenshot'])}' loading='lazy'></a><figcaption>{cap}</figcaption></figure>")
        parts.append("</div>")
    parts.append("</div>")
    return "".join(parts)


# ---- product pages -----------------------------------------------------------------------

def build_audit_pages(runs: list[dict]) -> dict[str, Path]:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    by_sub = defaultdict(list)
    for r in runs:
        by_sub[r.get("submission") or "unsorted"].append(r)
    out = {}
    for sub, rs in by_sub.items():
        rs = sorted(rs, key=lambda r: (str(r.get("level")), r.get("started_at", "")))
        n = len(rs)
        flagged = sum(1 for r in rs if any(f.get("attribution", "site") == "site" for f in r["_checks"].get("findings", [])))
        reached = sum(1 for r in rs if (r.get("checkpoints") or {}).get("final"))
        scored = [r for r in rs if r.get("_score")]
        caught = sum(r["_score"].get("caught", 0) for r in scored)
        seeded = sum(r["_score"].get("seeded", 0) for r in scored)
        rate = f"earned catch rate on seeded stores: {caught}/{seeded}" if seeded else "earned catch rate: no seeded stores in this submission"
        body = [f"<h1>Checkout audit · {esc(sub)}</h1>",
                f"<div class='muted'>{n} tasks · {reached}/{n} reached the final bill · {flagged} with findings · {rate}</div>"]
        for r in rs:
            body.append(run_section(r, rel_runs="../../runs"))
        p = AUDIT_DIR / f"{sub}.html"
        p.write_text(f"<!doctype html><meta charset='utf-8'><title>Checkout audit {esc(sub)}</title><style>{CSS}</style>" + "".join(body))
        out[sub] = p
    return out


# ---- internal comparison ------------------------------------------------------------------

def comparison_rows(prod: list[dict]) -> tuple[list[dict], dict, list]:
    by_model = defaultdict(list)
    for r in prod:
        by_model[r["model"]].append(r)
    levels = sorted({str(r["level"]) for r in prod}, key=lambda s: (len(s), s))
    rows = []
    per_level = {}
    for model, rs in sorted(by_model.items()):
        scored = [r for r in rs if r.get("_score")]
        cleared_levels = [str(r["level"]) for r in scored if r["_score"].get("level_cleared")]
        highest = max(cleared_levels, key=lambda s: (len(s), s)) if cleared_levels else "none"
        caught = sum(r["_score"]["caught"] for r in scored)
        seeded = sum(r["_score"]["seeded"] for r in scored)
        l1 = [r for r in scored if str(r["level"]) == "1"]
        fa_l1 = sum(r["_score"]["false_alarms"] for r in l1)
        stopped = sum(1 for r in rs if r.get("completed") and not r.get("attempted_payment"))
        completed = sum(1 for r in rs if r.get("completed"))
        avg = lambda k: (sum((r.get(k) or 0) for r in rs) / len(rs)) if rs else 0  # noqa: E731
        cell = {}
        for lv in levels:
            lr = [r for r in scored if str(r["level"]) == lv]
            cell[lv] = (sum(1 for r in lr if r["_score"].get("level_cleared")), len(lr))
        per_level[model] = cell
        rows.append({"model": model, "runs": len(rs), "highest": highest, "caught": caught, "seeded": seeded,
                     "fa_l1": f"{fa_l1} (n={len(l1)})", "stopped": f"{stopped}/{len(rs)}", "completed": f"{completed}/{len(rs)}",
                     "steps": round(avg("steps"), 1), "seconds": round(avg("wall_seconds"), 1), "cost": round(avg("cost_usd"), 3)})
    return rows, per_level, levels


def svg_chart(per_level: dict, levels: list) -> str:
    models = list(per_level.keys())
    if not models or not levels:
        return "<div class='muted'>no prod runs yet</div>"
    colors = ["#2b6cb0", "#dd6b20", "#2f855a", "#805ad5", "#b83280"]
    W, H, pad = 720, 220, 40
    gw = (W - 2 * pad) / len(levels)
    bw = min(40, gw / (len(models) + 1))
    parts = [f"<svg viewBox='0 0 {W} {H}' width='{W}' height='{H}' style='font:12px sans-serif'>"]
    for i, lv in enumerate(levels):
        x0 = pad + i * gw
        parts.append(f"<text x='{x0 + gw/2:.0f}' y='{H-8}' text-anchor='middle'>L{esc(lv)}</text>")
        for j, m in enumerate(models):
            c, n = per_level[m].get(lv, (0, 0))
            rate = c / n if n else 0
            h = rate * (H - 2 * pad)
            x = x0 + (gw - bw * len(models)) / 2 + j * bw
            parts.append(f"<rect x='{x:.0f}' y='{H-pad-h:.0f}' width='{bw-3:.0f}' height='{h:.0f}' fill='{colors[j % len(colors)]}'><title>{esc(m)} L{esc(lv)}: {c}/{n}</title></rect>")
            parts.append(f"<text x='{x + bw/2:.0f}' y='{H-pad-h-3:.0f}' text-anchor='middle'>{c}/{n}</text>")
    for j, m in enumerate(models):
        parts.append(f"<rect x='{pad + j*230}' y='6' width='12' height='12' fill='{colors[j % len(colors)]}'/><text x='{pad + j*230 + 16}' y='17'>{esc(m)}</text>")
    parts.append(f"<text x='{pad}' y='{pad-6}' fill='#666'>levels cleared per level (cleared/runs)</text></svg>")
    return "".join(parts)


def repro_block(prod: list[dict], levels: list) -> dict:
    settings = (prod[0].get("settings") if prod else {}) or {}
    trap_types = set()
    stores = set()
    for r in prod:
        stores.add(r.get("store_id"))
        for t in (r.get("_key") or {}).get("traps", []):
            if t.get("scored"):
                trap_types.add(t.get("type"))
    cells = defaultdict(int)
    for r in prod:
        cells[(r["model"], str(r["level"]))] += 1
    return {
        "models": sorted({r["model"] for r in prod}),
        "credential_modes": sorted({r.get("mode") for r in prod}),
        "max_turns": settings.get("max_turns"), "max_budget_usd": settings.get("max_budget_usd"),
        "effort": settings.get("effort"), "thinking": settings.get("thinking"),
        "prompt_version": settings.get("prompt_version"), "prompt_commit": settings.get("prompt_commit"),
        "sdk": settings.get("sdk"), "date": datetime.now().strftime("%Y-%m-%d"),
        "stores": len(stores), "trap_types": len(trap_types), "trap_type_names": sorted(trap_types),
        "runs_per_cell": sorted(set(cells.values())) if cells else [],
        "command": f"AUDITOR_MODE={'prod' if all(r.get('mode') == 'prod' for r in prod) else 'test'} .venv/bin/python -m runner.run{'' if all(r.get('mode') == 'prod' for r in prod) else ' --eval --force'} --models " + " ".join(sorted({r['model'] for r in prod})) + " --levels " + " ".join(levels) + " --repeats 1 && .venv/bin/python -m report.build_report",
    }


EVAL_MODES = ("prod", "cli")  # prod = API key; cli = deliberate comparison runs over the Claude Code login. test = debug, excluded.

LIMITS = [
    "Stores are seeded test stores served locally, not live shops; results say how the agent behaves on these traps, not on the open web.",
    "The agent has no typing tool, so flows that need an address or login typed in are out of scope.",
    "A single run per cell is one observation, not a rate; repeats are shown as k/n and are only meaningful where n > 1.",
    "Findings depend on what the model reports at each checkpoint; Python does the sums, the model does the reading.",
    "Debug runs (mode test) are excluded from the comparison; runs stamped cli went through the Claude Code login rather than the API key and are labelled in the reproducibility block.",
]


def build_index(runs: list[dict], audit_pages: dict[str, Path]) -> None:
    prod = [r for r in runs if r.get("mode") in EVAL_MODES]
    test = [r for r in runs if r.get("mode") not in EVAL_MODES]
    rows, per_level, levels = comparison_rows(prod)
    repro = repro_block(prod, levels)
    n_stores = repro["stores"]
    parts = [f"<h1>Checkout Auditor · internal eval</h1><div class='muted'>generated {datetime.now().isoformat(timespec='seconds')} · {len(runs)} run records ({len(prod)} in the table, {len(test)} debug runs excluded)</div>"]
    parts.append(f"<h2>Offline eval on {n_stores} seeded stores</h2>")
    parts.append("<table><tr><th>model</th><th>runs</th><th>highest level cleared</th><th>caught/seeded</th><th>false alarms on L1</th><th>stopped at Pay</th><th>completed</th><th>avg steps</th><th>avg seconds</th><th>avg cost $</th></tr>")
    for r in rows:
        parts.append(f"<tr><td>{esc(r['model'])}</td><td>{r['runs']}</td><td>{esc(r['highest'])}</td><td>{r['caught']}/{r['seeded']}</td><td>{esc(r['fa_l1'])}</td><td>{r['stopped']}</td><td>{r['completed']}</td><td>{r['steps']}</td><td>{r['seconds']}</td><td>{r['cost']}</td></tr>")
    parts.append("</table>")
    parts.append("<h3>Level cleared per level (cleared/runs)</h3><table><tr><th>model</th>" + "".join(f"<th>L{esc(l)}</th>" for l in levels) + "</tr>")
    for m, cell in per_level.items():
        parts.append(f"<tr><td>{esc(m)}</td>" + "".join(f"<td>{cell[l][0]}/{cell[l][1]}</td>" for l in levels) + "</tr>")
    parts.append("</table>")
    parts.append(svg_chart(per_level, levels))
    parts.append("<h3>Reproducibility</h3><pre>" + esc(json.dumps(repro, indent=1)) + "</pre>")
    parts.append("<h3>Honest limits</h3><ul>" + "".join(f"<li>{esc(l)}</li>" for l in LIMITS) + "</ul>")
    parts.append("<h2>Audit pages (product output, no model names)</h2><ul>" + "".join(
        f"<li><a href='audit/{esc(p.name)}'>{esc(s)}</a></li>" for s, p in sorted(audit_pages.items())) + "</ul>")
    parts.append("<h2>Per-run detail (prod)</h2>")
    for r in sorted(prod, key=lambda r: (str(r["level"]), r["model"], r.get("started_at", ""))):
        parts.append(run_section(r, rel_runs="../runs", internal=True))
    if test:
        parts.append("<h2>Test-mode runs (debugging, excluded from the table)</h2><details><summary>show</summary>")
        for r in sorted(test, key=lambda r: r.get("started_at", "")):
            parts.append(run_section(r, rel_runs="../runs", internal=True))
        parts.append("</details>")
    (OUT_DIR / "index.html").write_text(f"<!doctype html><meta charset='utf-8'><title>Checkout Auditor eval</title><style>{CSS}</style>" + "".join(parts))

    md = [f"# Offline eval on {n_stores} seeded stores", "", f"Generated {datetime.now().isoformat(timespec='seconds')} from {len(prod)} prod runs (debug test-mode runs excluded; credential modes in the reproducibility block: prod = API key, cli = Claude Code login).", "",
          "| model | runs | highest level cleared | caught/seeded | false alarms on L1 | stopped at Pay | completed | avg steps | avg seconds | avg cost $ |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['model']} | {r['runs']} | {r['highest']} | {r['caught']}/{r['seeded']} | {r['fa_l1']} | {r['stopped']} | {r['completed']} | {r['steps']} | {r['seconds']} | {r['cost']} |")
    md += ["", "## Level cleared per level (cleared/runs)", "", "| model | " + " | ".join(f"L{l}" for l in levels) + " |", "|---|" + "---|" * len(levels)]
    for m, cell in per_level.items():
        md.append(f"| {m} | " + " | ".join(f"{cell[l][0]}/{cell[l][1]}" for l in levels) + " |")
    md += ["", "## Reproducibility", "", "```json", json.dumps(repro, indent=1), "```", "", "## Honest limits", ""] + [f"- {l}" for l in LIMITS] + [""]
    (OUT_DIR / "eval.md").write_text("\n".join(md))


def main() -> int:
    runs = [enrich(r) for r in load_runs()]
    pages = build_audit_pages(runs)
    build_index(runs, pages)
    prod = sum(1 for r in runs if r.get("mode") in EVAL_MODES)
    print(f"report: {len(runs)} runs ({prod} in the eval table) → report/index.html, report/eval.md, {len(pages)} audit page(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
