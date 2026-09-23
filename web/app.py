"""Checkout Auditor demo web app: product page, grouped submission report, internal score page.

    AUDITOR_MODE=prod .venv/bin/python -m web.app      # http://127.0.0.1:8080

The app owns one Playwright instance for its lifetime, one shared headless browser, and one headed
browser per model (launched lazily, tiled) for rows with "show browser" ticked. Scoring is always
checker.score.score_run; rendering of finished runs is report.build_report.run_section.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent.harness import (  # noqa: E402
    ROOT as HARNESS_ROOT, RUNS_DIR, ensure_store_server, get_mode, launch_browser, run_audit, sdk_env_for_mode,
)
from checker.score import score_run  # noqa: E402
from report.build_report import CSS, enrich, esc, load_runs, rupees, run_section  # noqa: E402

KEYS_DIR = HARNESS_ROOT / "stores" / "keys"
REPORT_DIR = HARNESS_ROOT / "report"
MODELS = ["claude-fable-5-1", "claude-fable-5", "claude-opus-5"]
CONCURRENCY = 6
SCREEN_WIDTH, WINDOW_HEIGHT = 1440, 820
HOST, PORT = "127.0.0.1", 8080

MODE = "test"
SDK_ENV: dict[str, str] = {}
SUBMISSIONS: dict[str, dict[str, Any]] = {}
STATE: dict[str, Any] = {"pw": None, "headless": None, "headed": {}, "store_proc": None, "sem": None, "lock": None}


# ---- keys / stores -----------------------------------------------------------------------

def load_keys() -> list[dict]:
    keys = []
    for p in sorted(KEYS_DIR.glob("*.json")):
        try:
            k = json.loads(p.read_text())
        except Exception:
            continue
        if isinstance(k, dict) and k.get("store_id"):
            k["_file"] = p.name
            keys.append(k)
    keys.sort(key=lambda k: (str(k.get("level", "")).zfill(3), k["store_id"]))
    return keys


def identify_store(url: str) -> tuple[str, int | str]:
    """(store_id, level) for a URL: exact key match, then /l<N>/ in the path, then a slug of the URL."""
    u = url.strip().rstrip("/")
    for k in load_keys():
        if (k.get("url") or "").rstrip("/") == u:
            return k["store_id"], k.get("level", k["store_id"])
    m = re.search(r"/l(\d+)(?:/|$)", url)
    if m:
        return f"l{m.group(1)}", int(m.group(1))
    parsed = urlparse(url)
    slug = re.sub(r"[^a-z0-9]+", "-", (parsed.netloc + parsed.path).lower()).strip("-")[:40] or "store"
    return slug, "web"


# ---- submissions ------------------------------------------------------------------------

def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def runs_for_submission(sub_id: str) -> list[dict]:
    return [r for r in load_runs() if r.get("submission") == sub_id]


def submission_view(sub_id: str) -> dict | None:
    """In-memory submission, or one rebuilt from runs/*.json after a restart. None when unknown."""
    sub = SUBMISSIONS.get(sub_id)
    if sub:
        return sub
    runs = runs_for_submission(sub_id)
    if not runs:
        return None
    rows, index = [], {}
    for r in sorted(runs, key=lambda r: r.get("started_at", "")):
        k = (r.get("store_url"), r.get("task"))
        if k not in index:
            index[k] = len(rows)
            rows.append({"url": r.get("store_url"), "task": r.get("task"), "headed": False,
                         "store_id": r.get("store_id"), "level": r.get("level")})
    jobs = [{"row": index[(r.get("store_url"), r.get("task"))], "model": r.get("model"), "status": "done",
             "run_id": r["run_id"], "started_at": r.get("started_at"), "error": None} for r in runs]
    return {"id": sub_id, "started_at": min(r.get("started_at", "") for r in runs), "rows": rows,
            "models": sorted({r.get("model") for r in runs}), "jobs": jobs, "restored": True}


def api_submission(sub: dict) -> dict:
    jobs = sub["jobs"]
    return {"submission_id": sub["id"], "started_at": sub["started_at"], "mode": MODE,
            "finished": sum(1 for j in jobs if j["status"] == "done"), "total": len(jobs),
            "jobs": [{k: j.get(k) for k in ("row", "model", "status", "run_id", "started_at", "error")} for j in jobs]}


async def get_headed_browser(model: str, models: list[str]):
    async with STATE["lock"]:
        b = STATE["headed"].get(model)
        if b is not None:
            return b
        n = max(1, len(models))
        w = min(700, SCREEN_WIDTH // n)
        i = models.index(model) if model in models else len(STATE["headed"])
        b = await launch_browser(STATE["pw"], headed=True, position=(i * w, 0), size=(w, WINDOW_HEIGHT))
        STATE["headed"][model] = b
        return b


async def run_job(sub: dict, job: dict) -> None:
    row = sub["rows"][job["row"]]
    async with STATE["sem"]:
        job["status"] = "running"
        job["started_at"] = now_iso()
        try:
            browser = await get_headed_browser(job["model"], sub["models"]) if row["headed"] else STATE["headless"]
            rec = await run_audit(
                browser, model=job["model"], store_url=row["url"], task=row["task"], level=row["level"],
                store_id=row["store_id"], mode=MODE, repeat=job["repeat"], overlay=bool(row["headed"]),
                window_title=job["model"] if row["headed"] else None, sdk_env=SDK_ENV, submission=sub["id"],
            )
            job["run_id"] = rec["run_id"]
            job["error"] = rec.get("error")
        except Exception as e:  # noqa: BLE001
            job["error"] = f"{type(e).__name__}: {str(e)[:300]}"
        job["status"] = "done"
        print(f"[{sub['id']}] {job['model']} row {job['row'] + 1} done: {job.get('run_id')} {job.get('error') or ''}")


# ---- HTML -------------------------------------------------------------------------------

EXTRA_CSS = """
.nav{display:flex;gap:16px;align-items:center;margin-bottom:14px;font-size:14px}.nav a{color:#2b6cb0}
.banner{background:#fff3c4;border:1px solid #e0b400;color:#5b4a00;padding:8px 12px;border-radius:6px;margin:10px 0;font-size:14px}
input[type=text]{width:100%;box-sizing:border-box;padding:6px 8px;font:inherit;border:1px solid #ccc;border-radius:4px}
button{font:inherit;padding:8px 16px;border-radius:6px;border:1px solid #2b6cb0;background:#2b6cb0;color:#fff;cursor:pointer}
button.secondary{background:#fff;color:#2b6cb0}button.small{padding:3px 10px;font-size:13px}
.models label{margin-right:18px;font-size:14px}
.placeholder{border:1px dashed #bbb;border-radius:8px;padding:14px 18px;margin:14px 0;color:#666;background:#fff}
.spin{display:inline-block;width:12px;height:12px;border:2px solid #999;border-top-color:transparent;border-radius:50%;animation:s 1s linear infinite;vertical-align:middle;margin-right:6px}
@keyframes s{to{transform:rotate(360deg)}}
.row-label{font-size:12px;color:#888;margin:14px 0 -10px}
.grid{display:flex;gap:12px;overflow-x:auto;align-items:stretch}.grid .panel{flex:1 1 300px;min-width:300px;margin-top:0}
.kv{margin:3px 0}.kv b{display:inline-block;min-width:130px;color:#444;font-weight:600}
select{font:inherit;padding:5px;max-width:420px}
"""


def page(title: str, body: str, extra_head: str = "") -> str:
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>{esc(title)}</title>"
            f"<style>{CSS}{EXTRA_CSS}</style>{extra_head}</head><body>{nav()}{body}</body></html>")


def nav() -> str:
    return ("<div class='nav'><a href='/'>Checkout Auditor</a><a href='/eval'>eval</a>"
            "<a href='/report/index.html'>report</a><a href='/report/eval.md'>eval.md</a>"
            f"<span class='muted'>mode: {esc(MODE)}</span></div>")


def test_banner() -> str:
    if MODE != "test":
        return ""
    return "<div class='banner'>test mode: runs bill to the Claude Code login and are excluded from the eval</div>"


PRODUCT_JS = """
const MODELS = __MODELS__;
const PREFILL = __PREFILL__;
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function addRow(url='', task='', headed=false){
  const tb=document.querySelector('#rows tbody');
  const tr=document.createElement('tr');
  tr.innerHTML=`<td class='n'></td><td><input type='text' class='url' value='${esc(url)}' placeholder='http://localhost:8000/l3/'></td>
    <td><input type='text' class='task' value='${esc(task)}' placeholder='Buy one ... with standard delivery.'></td>
    <td style='text-align:center'><input type='checkbox' class='headed' ${headed?'checked':''}></td>
    <td><button type='button' class='secondary small' onclick='this.closest("tr").remove();renumber()'>x</button></td>`;
  tb.appendChild(tr); renumber();
}
function renumber(){document.querySelectorAll('#rows tbody tr').forEach((tr,i)=>tr.querySelector('.n').textContent=i+1);}
async function go(){
  const rows=[...document.querySelectorAll('#rows tbody tr')].map(tr=>({
    url:tr.querySelector('.url').value.trim(), task:tr.querySelector('.task').value.trim(), headed:tr.querySelector('.headed').checked
  })).filter(r=>r.url && r.task);
  const models=[...document.querySelectorAll('.models input:checked')].map(c=>c.value);
  const msg=document.getElementById('msg');
  if(!rows.length){msg.textContent='add at least one row with a URL and a task';return;}
  if(!models.length){msg.textContent='tick at least one model';return;}
  const btn=document.getElementById('go'); btn.disabled=true; msg.textContent='starting '+(rows.length*models.length)+' runs...';
  try{
    const r=await fetch('/api/run',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({rows,models})});
    const j=await r.json();
    if(!r.ok){throw new Error(j.detail||r.statusText);}
    location.href='/submission/'+j.submission_id;
  }catch(e){msg.textContent='error: '+e.message; btn.disabled=false;}
}
PREFILL.forEach(r=>addRow(r.url,r.task,r.headed));
"""


def product_page() -> str:
    keys = load_keys()
    prefill = [{"url": k.get("url") or f"http://localhost:8000/{k['store_id']}/", "task": k.get("task", ""),
                "headed": str(k.get("level")) == "3"} for k in keys]
    models_html = "".join(f"<label><input type='checkbox' value='{esc(m)}' checked> {esc(m)}</label>" for m in MODELS)
    body = f"""
<h1>Checkout Auditor</h1>
<div class='muted'>Give it a store and a shopping task. The agent shops up to the Pay button, never past it, and reports every charge the shopper did not choose.</div>
{test_banner()}
<div class='card'>
<div class='models'><b>Models</b> &nbsp; {models_html}</div>
<table id='rows'><thead><tr><th style='width:30px'>#</th><th style='width:34%'>store URL</th><th>task</th><th style='width:90px'>show browser</th><th style='width:40px'></th></tr></thead><tbody></tbody></table>
<div style='display:flex;gap:12px;align-items:center;margin-top:10px'>
<button type='button' class='secondary' onclick='addRow()'>+ row</button>
<button type='button' id='go' onclick='go()'>Go live</button>
<span id='msg' class='muted'></span></div>
</div>
<script>{PRODUCT_JS.replace('__MODELS__', json.dumps(MODELS)).replace('__PREFILL__', json.dumps(prefill))}</script>"""
    return page("Checkout Auditor", body)


SUBMISSION_JS = """
const SUB='__SUB__'; const RENDERED=__FINISHED__;
async function poll(){
  try{const r=await fetch('/api/submission/'+SUB); if(!r.ok) return; const j=await r.json();
    if(j.finished!==RENDERED){location.reload();return;}
    if(j.finished>=j.total) return;
  }catch(e){}
  setTimeout(poll,3000);
}
if(RENDERED<__TOTAL__) setTimeout(poll,3000);
"""


def submission_page(sub: dict) -> str:
    runs_by_id = {r["run_id"]: r for r in runs_for_submission(sub["id"])}
    jobs = sub["jobs"]
    finished = sum(1 for j in jobs if j["status"] == "done")
    parts = [f"<h1>Checkout audit · {esc(sub['id'])}</h1>",
             f"<div class='muted'>started {esc(sub['started_at'])} · {len(sub['rows'])} task(s) · {finished}/{len(jobs)} runs finished"
             + (" · restored from runs/" if sub.get("restored") else "") + "</div>", test_banner()]
    for i, row in enumerate(sub["rows"]):
        parts.append(f"<h2>Task {i + 1}: {esc(row['task'])}</h2><div class='muted'>{esc(row['url'])}</div>")
        row_jobs = [j for j in jobs if j["row"] == i]
        done = [(runs_by_id.get(j.get("run_id")), j) for j in row_jobs if j["status"] == "done"]
        done.sort(key=lambda t: ((t[0] or {}).get("started_at") or t[1].get("started_at") or ""))
        for n, (run, job) in enumerate(done, 1):
            parts.append(f"<div class='row-label'>run {n}</div>")
            if run is None:
                parts.append(f"<div class='placeholder'>run failed before a record was written · started {esc(job.get('started_at'))}"
                             f"<div class='finding'>{esc(job.get('error'))}</div></div>")
                continue
            parts.append(run_section(enrich(run), rel_runs="/runs"))
        pending = [j for j in row_jobs if j["status"] != "done"]
        for n, job in enumerate(pending, len(done) + 1):
            label = "running…" if job["status"] == "running" else "queued"
            when = f" · started {esc(job['started_at'])}" if job.get("started_at") else ""
            parts.append(f"<div class='row-label'>run {n}</div><div class='placeholder'><span class='spin'></span>{label}{when}</div>")
    js = SUBMISSION_JS.replace("__SUB__", sub["id"]).replace("__FINISHED__", str(finished)).replace("__TOTAL__", str(len(jobs)))
    return page(f"Checkout audit {sub['id']}", "".join(parts) + f"<script>{js}</script>")


# ---- eval page --------------------------------------------------------------------------

def default_pairs() -> list[dict]:
    """Per store_id in runs/: the latest prod run per model; test runs only when the store has no prod run."""
    runs = load_runs()
    by_store: dict[str, list[dict]] = defaultdict(list)
    for r in runs:
        if r.get("store_id"):
            by_store[r["store_id"]].append(r)
    pairs = []
    for store in sorted(by_store, key=lambda s: (len(s), s)):
        rs = by_store[store]
        prod = [r for r in rs if r.get("mode") == "prod"]
        pool = prod or rs
        latest: dict[str, dict] = {}
        for r in sorted(pool, key=lambda r: r.get("started_at", "")):
            latest[r["model"]] = r
        key_file = f"{store}.json" if (KEYS_DIR / f"{store}.json").is_file() else None
        for m in sorted(latest):
            pairs.append({"run_file": latest[m]["_file"], "key_file": key_file})
    return pairs


def safe_name(name: str, folder: Path, suffix: str = ".json") -> Path:
    n = Path(str(name)).name
    if not n or n != name or not n.endswith(suffix):
        raise HTTPException(400, f"bad file name: {name!r}")
    p = folder / n
    if not p.is_file():
        raise HTTPException(404, f"no such file: {n}")
    return p


def score_pair(run_file: str, key_file: str | None) -> dict:
    run = json.loads(safe_name(run_file, RUNS_DIR).read_text())
    out = {"run_file": run_file, "key_file": key_file, "run_id": run.get("run_id"), "model": run.get("model"),
           "mode": run.get("mode"), "started_at": run.get("started_at"), "store_id": run.get("store_id"),
           "level": run.get("level"), "status": run.get("status"), "error": run.get("error")}
    if not key_file:
        out.update({"unscored": True, "reason": "no answer key"})
        return out
    key = json.loads(safe_name(key_file, KEYS_DIR).read_text())
    s = score_run(run, key)
    findings = s.pop("findings")
    out["findings"] = [{k: f.get(k) for k in ("check", "label", "amount", "pattern", "attribution", "evidence")} for f in findings]
    out["gap"] = s.pop("gap")
    s.pop("notes", None)
    out["score"] = s
    out["key"] = {"name": key.get("name"), "level": key.get("level"), "first_price": key.get("first_price"),
                  "upfront_charges": key.get("upfront_charges") or [],
                  "seeded": [{"label": t.get("label"), "amount": t.get("amount"), "type": t.get("type")}
                             for t in (key.get("traps") or []) if t.get("scored")],
                  "expected_final_total": key.get("expected_final_total")}
    return out


EVAL_JS = """
const PRELOAD=__PRELOAD__; let pairs=PRELOAD.slice();
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function rs(x){if(x===null||x===undefined)return '-';x=Number(x);const a=Math.abs(x);const s='₹'+(Math.abs(a-Math.round(a))<0.005?Math.round(a).toLocaleString('en-IN'):a.toFixed(2));return x<0?'−'+s:s;}
function yn(b){return b?"<span class='pass'>yes</span>":"<span class='fail'>no</span>";}
function panel(r){
  if(r.unscored) return `<div class='panel'><b>${esc(r.model)}</b> <span class='tag'>${esc(r.mode)}</span><div class='muted'>${esc(r.started_at)}</div><div>unscored: ${esc(r.reason)}</div></div>`;
  const s=r.score,k=r.key;
  const seeded=k.seeded.map(t=>`${esc(t.label)} ${rs(t.amount)}`).join(', ')||'none';
  const found=r.findings.filter(f=>f.attribution==='site').map(f=>`${esc(f.label)} ${rs(f.amount)}`).join(', ')||'none';
  const agent=r.findings.filter(f=>f.attribution==='agent').map(f=>`${esc(f.label)} ${rs(f.amount)}`).join(', ');
  const stopped=s.completed&&!s.attempted_payment;
  return `<div class='panel'><b>${esc(r.model)}</b> <span class='tag'>${esc(r.mode)}</span> <span class='tag'>${esc(r.status)}</span>
  <div class='muted'>run ${esc(r.started_at)} · ${esc(r.run_file)}</div>
  <div class='kv'><b>seeded</b> ${s.seeded}: ${seeded}</div>
  <div class='kv'><b>found</b> ${found}${agent?` <span class='muted'>(agent errors: ${agent})</span>`:''}</div>
  <div class='kv'><b>caught / seeded</b> ${s.caught}/${s.seeded}${s.missed_traps.length?` <span class='fail'>missed: ${esc(s.missed_traps.join(', '))}</span>`:''}</div>
  <div class='kv'><b>false alarms</b> ${s.false_alarms}${s.false_alarm_labels.length?` (${esc(s.false_alarm_labels.join(', '))})`:''}</div>
  <div class='kv'><b>amounts correct</b> ${yn(s.amounts_correct)} <span class='muted'>first ${rs(s.first_price_total)} vs ${rs(s.expected_first_price_total)} · final ${rs(s.final_total)} vs ${rs(s.expected_final_total)}</span></div>
  <div class='kv'><b>stopped at Pay</b> ${yn(stopped)}${s.attempted_payment?" <span class='fail'>attempted payment</span>":''}</div>
  <div class='kv'><b>level cleared</b> ${yn(s.level_cleared)}${s.reason?` <span class='muted'>${esc(s.reason)}</span>`:''}</div>
  <div class='verdict ${s.level_cleared?'pass':'fail'}'>${esc(s.verdict_line)}</div></div>`;
}
async function score(){
  const out=document.getElementById('out'); out.innerHTML="<div class='muted'><span class='spin'></span>scoring "+pairs.length+" run(s)...</div>";
  const r=await fetch('/api/score',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({pairs})});
  const j=await r.json(); if(!r.ok){out.innerHTML="<div class='finding'>"+esc(j.detail||r.statusText)+"</div>";return;}
  const groups={}; const order=[];
  j.results.forEach(x=>{const g=x.store_id||'?'; if(!groups[g]){groups[g]=[];order.push(g);} groups[g].push(x);});
  order.sort((a,b)=>a.length-b.length||a.localeCompare(b));
  out.innerHTML=order.map(g=>{const rs_=groups[g]; const name=(rs_.find(x=>x.key)||{}).key?.name||g;
    return `<h2>${esc(name)} <span class='tag'>${esc(g)}</span> <span class='tag'>L${esc(rs_[0].level)}</span></h2><div class='grid'>${rs_.map(panel).join('')}</div>`;}).join('');
}
function addOverride(){
  const run_file=document.getElementById('runsel').value, key_file=document.getElementById('keysel').value||null;
  pairs=pairs.filter(p=>p.run_file!==run_file); pairs.push({run_file,key_file}); score();
}
function reset(){pairs=PRELOAD.slice();score();}
"""


def eval_page() -> str:
    pairs = default_pairs()
    run_files = sorted((p.name for p in RUNS_DIR.glob("*.json")), reverse=True)
    key_files = sorted(p.name for p in KEYS_DIR.glob("*.json"))
    runsel = "".join(f"<option value='{esc(f)}'>{esc(f)}</option>" for f in run_files)
    keysel = "<option value=''>(no key)</option>" + "".join(f"<option value='{esc(f)}'>{esc(f)}</option>" for f in key_files)
    n_models = len({p['run_file'].split('_')[1] for p in pairs}) if pairs else 0
    body = f"""
<h1>Checkout Auditor · score one run</h1>
<div class='muted'>internal · pre-loaded with the latest batch: {len(pairs)} run(s) across {n_models} model(s), keys auto-selected by store_id ·
<a href='/report/index.html'>batch table</a> · <a href='/report/eval.md'>eval.md</a></div>
{test_banner()}
<div class='card'>
<div style='display:flex;gap:10px;align-items:center;flex-wrap:wrap'>
<button type='button' onclick='score()'>Score</button><span class='muted'>scores the pre-loaded batch with checker.score.score_run</span></div>
<details style='margin-top:10px'><summary>override: pick a run file and a key file</summary>
<div style='display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:8px'>
<select id='runsel'>{runsel}</select><select id='keysel'>{keysel}</select>
<button type='button' class='secondary' onclick='addOverride()'>Score this pair</button>
<button type='button' class='secondary small' onclick='reset()'>reset to latest batch</button></div></details>
</div>
<div id='out'></div>
<script>{EVAL_JS.replace('__PRELOAD__', json.dumps(pairs))}</script>"""
    return page("Checkout Auditor eval", body)


# ---- app --------------------------------------------------------------------------------

CHECKLIST = f"""
Checkout Auditor demo click path (mode={{mode}}):
  1. http://{HOST}:{PORT}/            product page, four stores pre-filled, L3 "show browser" ticked. Press "Go live".
  2. narrate the headed L3 window (~20 s), then switch tabs on your own cue.
  3. http://{HOST}:{PORT}/submission/<id>   opens automatically; the "finished earlier" submission lives at its own URL.
  4. http://{HOST}:{PORT}/eval        pre-loaded; press "Score" for one verdict panel per model side by side.
  5. http://{HOST}:{PORT}/report/eval.md   the batch table.
  fallback: the recording of the tiled race in a fifth tab.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    global MODE, SDK_ENV
    MODE = get_mode()
    SDK_ENV = sdk_env_for_mode(MODE)
    STATE["store_proc"] = ensure_store_server(8000)
    STATE["sem"] = asyncio.Semaphore(CONCURRENCY)
    STATE["lock"] = asyncio.Lock()
    STATE["pw"] = await async_playwright().start()
    STATE["headless"] = await launch_browser(STATE["pw"], headed=False)
    print(CHECKLIST.replace("{mode}", MODE), flush=True)
    try:
        yield
    finally:
        for b in list(STATE["headed"].values()) + [STATE["headless"]]:
            try:
                await b.close()
            except Exception:
                pass
        try:
            await STATE["pw"].stop()
        except Exception:
            pass
        if STATE["store_proc"]:
            STATE["store_proc"].terminate()


app = FastAPI(title="Checkout Auditor", lifespan=lifespan)


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
    body = f"<h1>{exc.status_code}</h1><div class='card'>{esc(exc.detail)}</div><p><a href='/'>back to the product page</a></p>"
    return HTMLResponse(page(f"{exc.status_code}", body), status_code=exc.status_code)


@app.get("/", response_class=HTMLResponse)
async def index():
    return product_page()


@app.post("/api/run")
async def api_run(body: dict):
    rows_in = body.get("rows") or []
    models = [m for m in (body.get("models") or []) if isinstance(m, str) and m.strip()]
    rows = []
    for r in rows_in:
        url, task = str(r.get("url", "")).strip(), str(r.get("task", "")).strip()
        if not url or not task:
            continue
        store_id, level = identify_store(url)
        rows.append({"url": url, "task": task, "headed": bool(r.get("headed")), "store_id": store_id, "level": level})
    if not rows:
        raise HTTPException(422, "no rows with both a URL and a task")
    if not models:
        raise HTTPException(422, "no models ticked")
    sub_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "_web"
    if sub_id in SUBMISSIONS:
        raise HTTPException(409, "a submission started this second; press Go live again")
    sub = {"id": sub_id, "started_at": now_iso(), "rows": rows, "models": models, "jobs": [], "mode": MODE}
    seen: dict[tuple[str, str], int] = defaultdict(int)
    for i, row in enumerate(rows):
        for m in models:
            seen[(row["store_id"], m)] += 1
            sub["jobs"].append({"row": i, "model": m, "status": "queued", "run_id": None, "started_at": None,
                                "error": None, "repeat": seen[(row["store_id"], m)]})
    SUBMISSIONS[sub_id] = sub
    for job in sub["jobs"]:
        asyncio.create_task(run_job(sub, job))
    print(f"[{sub_id}] {len(sub['jobs'])} jobs scheduled ({len(rows)} rows x {len(models)} models), mode={MODE}", flush=True)
    return {"submission_id": sub_id, "jobs": len(sub["jobs"])}


@app.get("/api/submission/{sub_id}")
async def api_get_submission(sub_id: str):
    sub = submission_view(sub_id)
    if not sub:
        raise HTTPException(404, f"no submission {sub_id}")
    return api_submission(sub)


@app.get("/submission/{sub_id}", response_class=HTMLResponse)
async def submission(sub_id: str):
    sub = submission_view(sub_id)
    if not sub:
        raise HTTPException(404, f"no submission {sub_id!r}: nothing in memory and no run in runs/ carries that submission id")
    return submission_page(sub)


@app.get("/eval", response_class=HTMLResponse)
async def eval_view():
    return eval_page()


@app.post("/api/score")
async def api_score(body: dict):
    pairs = body.get("pairs") or []
    if not isinstance(pairs, list) or not pairs:
        raise HTTPException(422, "pairs must be a non-empty list of {run_file, key_file}")
    results = [score_pair(str(p.get("run_file", "")), p.get("key_file") or None) for p in pairs]
    return {"results": results}


@app.get("/report/eval.md")
async def eval_md():
    p = REPORT_DIR / "eval.md"
    if not p.is_file():
        raise HTTPException(404, "report/eval.md not built yet; run .venv/bin/python -m report.build_report")
    return PlainTextResponse(p.read_text(), media_type="text/plain; charset=utf-8")


RUNS_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/runs", StaticFiles(directory=str(RUNS_DIR)), name="runs")
app.mount("/report", StaticFiles(directory=str(REPORT_DIR)), name="report")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
