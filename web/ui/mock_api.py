"""Mock of the web.app JSON API, stdlib only, for building the UI without the SDK or Playwright.

    python web/ui/mock_api.py            # http://127.0.0.1:8080

Serves the static UI from this folder and fake but correctly shaped answers for every endpoint
web/app.py exposes. Run records are synthesised from the real answer keys in stores/keys/, so the
numbers on screen are the numbers the real backend would produce for a run that catches everything.
Submissions progress queued -> running -> done on a timer so the polling UI can be exercised.

This file is a development aid. It is never imported by the real app; point the UI at the real
backend (which serves the same paths on the same port) and nothing in the pages changes.
"""

from __future__ import annotations

import json
import random
import threading
import time
from datetime import datetime, timedelta
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

UI_DIR = Path(__file__).resolve().parent
ROOT = UI_DIR.parent.parent
KEYS_DIR = ROOT / "stores" / "keys"

MODELS = ["claude-fable-5-1", "claude-fable-5", "claude-opus-5"]
HOST, PORT = "127.0.0.1", 8080
JOB_SECONDS = 4.0  # how long a fake run "takes"; keeps the progress UI honest to look at

SUBMISSIONS: dict[str, dict] = {}
RUNS: list[dict] = []
LOCK = threading.Lock()


# ---- fixtures ---------------------------------------------------------------------------------

def load_keys() -> dict[str, dict]:
    out = {}
    for p in sorted(KEYS_DIR.glob("l*.json")):
        try:
            k = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if k.get("store_id"):
            out[k["store_id"]] = k
    return out


KEYS = load_keys()
CHECK_FOR_TRAP = {
    "pre_ticked_addon": "basket_sneaking",
    "drip_fee": "drip_pricing",
    "delivery_triggered_fee": "drip_pricing",
    "cod_surcharge": "drip_pricing",
    "platform_fee": "drip_pricing",
    "misleading_discount": "misleading_discount",
    "price_change": "price_change",
    "vanished_discount": "vanished_discount",
}


def iso(dt: datetime) -> str:
    return dt.astimezone().isoformat(timespec="seconds")


def store_for_url(url: str) -> tuple[str | None, int | str | None]:
    """Same job as identify_store in web/app.py: map a store URL onto a seeded store id."""
    path = urlparse(url).path.strip("/").split("/")
    for seg in path:
        if seg in KEYS:
            return seg, KEYS[seg].get("level")
    return None, None


def synth_run(model: str, url: str, task: str, submission: str | None, started: datetime,
              mode: str = "prod", catches_all: bool = True) -> dict:
    """A run record shaped like the real harness writes, derived from the store's answer key."""
    store_id, level = store_for_url(url)
    key = KEYS.get(store_id or "", {})
    rid = f"{started.strftime('%Y%m%d-%H%M%S')}_{model}_{store_id or 'live'}_r1_{random.randint(100, 999)}"
    first = key.get("first_price")
    final = key.get("expected_final_total")
    scored_traps = [t for t in (key.get("traps") or []) if t.get("scored")]

    findings = []
    for t in scored_traps if catches_all else scored_traps[:-1]:
        findings.append({
            "check": CHECK_FOR_TRAP.get(t.get("type"), "drip_pricing"),
            "label": t.get("label"),
            "amount": t.get("amount"),
            "pattern": t.get("pattern"),
            "attribution": "site",
            "evidence": f"absent at first price, {t.get('amount')} on the final screen",
        })

    caught = len(findings)
    seeded = len(scored_traps)
    missed = [t.get("label") for t in scored_traps[caught:]] if caught < seeded else []
    cleared = caught == seeded and not missed
    verdict = (f"level cleared: {caught}/{seeded} traps caught, 0 false alarms, amounts correct, stopped at Pay"
               if cleared else
               f"level not cleared: {caught}/{seeded} traps caught, missed {', '.join(missed)}")

    steps = random.randint(10, 16)
    return {
        "run_id": rid,
        "file": rid + ".json",
        "model": model,
        "level": level,
        "store_id": store_id,
        "store_url": url,
        "task": task,
        "mode": mode,
        "submission": submission,
        "status": "ok",
        "error": None,
        "completed": True,
        "attempted_payment": False,
        "steps": steps,
        "wall_seconds": round(random.uniform(26, 42), 1),
        "cost_usd": round(random.uniform(0.06, 0.21), 3),
        "started_at": iso(started),
        "ended_at": iso(started + timedelta(seconds=35)),
        "first_price_total": first,
        "final_total": final,
        "findings": findings,
        "gap": "final total is fully explained by the lines above" if cleared else None,
        "scored": bool(key),
        "verdict_line": verdict if key else None,
        "level_cleared": cleared if key else None,
        "caught": caught if key else None,
        "seeded": seeded if key else None,
        "false_alarms": 0 if key else None,
        "amounts_correct": True if key else None,
    }


def seed_history() -> None:
    """A handful of finished runs from 'earlier in the evening' so the eval page has something."""
    base = datetime.now() - timedelta(hours=2)
    for i, (store_id, key) in enumerate(sorted(KEYS.items())):
        for j, model in enumerate(MODELS):
            started = base + timedelta(minutes=i * 6 + j * 2)
            RUNS.append(synth_run(model, key["url"], key["task"], f"{base.strftime('%Y%m%d-%H%M%S')}_ladder",
                                  started, mode="prod", catches_all=True))


seed_history()


# ---- submission lifecycle ---------------------------------------------------------------------

def advance(sub_id: str) -> None:
    """Walk one submission's jobs through running -> done on a timer, in a background thread."""
    sub = SUBMISSIONS[sub_id]
    for job in sub["jobs"]:
        with LOCK:
            job["status"] = "running"
            job["started_at"] = iso(datetime.now())
        time.sleep(JOB_SECONDS)
        row = sub["rows"][job["row"]]
        rec = synth_run(job["model"], row["url"], row["task"], sub_id, datetime.now(), mode=sub["mode"])
        with LOCK:
            RUNS.append(rec)
            job["run_id"] = rec["run_id"]
            job["status"] = "done"
            job["run"] = rec


def submission_payload(sub: dict) -> dict:
    jobs = sub["jobs"]
    return {
        "submission_id": sub["id"], "started_at": sub["started_at"], "mode": sub["mode"],
        "finished": sum(1 for j in jobs if j["status"] == "done"), "total": len(jobs),
        "rows": [{k: r.get(k) for k in ("url", "task", "headed", "store_id", "level")} for r in sub["rows"]],
        "jobs": [{k: j.get(k) for k in ("row", "model", "status", "run_id", "started_at", "error", "run")}
                 for j in jobs],
    }


# ---- scoring ----------------------------------------------------------------------------------

def score_pair(run_file: str, key_file: str | None) -> dict:
    run = next((r for r in RUNS if r["file"] == run_file), None)
    if not run:
        return {"run_file": run_file, "key_file": key_file, "unscored": True, "reason": "no such run file"}
    out = {k: run.get(k) for k in ("run_id", "model", "mode", "started_at", "store_id", "level", "status", "error")}
    out.update({"run_file": run_file, "key_file": key_file})
    if not key_file:
        out.update({"unscored": True, "reason": "no answer key"})
        return out
    key = KEYS.get(Path(key_file).stem)
    if not key:
        out.update({"unscored": True, "reason": f"no such key file: {key_file}"})
        return out
    seeded = [{"label": t.get("label"), "amount": t.get("amount"), "type": t.get("type")}
              for t in (key.get("traps") or []) if t.get("scored")]
    out["findings"] = run["findings"]
    out["gap"] = {"summary": run.get("gap"), "amount": 0}
    out["score"] = {
        "seeded": len(seeded), "caught": run.get("caught") or 0,
        "missed_traps": [], "false_alarms": 0, "false_alarm_labels": [],
        "amounts_correct": True,
        "first_price_total": run.get("first_price_total"), "expected_first_price_total": key.get("first_price"),
        "final_total": run.get("final_total"), "expected_final_total": key.get("expected_final_total"),
        "completed": run.get("completed"), "attempted_payment": run.get("attempted_payment"),
        "level_cleared": run.get("level_cleared"), "reason": None,
        "verdict_line": run.get("verdict_line"),
        "steps": run.get("steps"), "wall_seconds": run.get("wall_seconds"), "cost_usd": run.get("cost_usd"),
    }
    out["key"] = {"name": key.get("name"), "level": key.get("level"), "first_price": key.get("first_price"),
                  "upfront_charges": key.get("upfront_charges") or [], "seeded": seeded,
                  "expected_final_total": key.get("expected_final_total")}
    return out


def eval_table() -> dict:
    prod = [r for r in RUNS if r.get("mode") in ("prod", "cli")]
    levels = sorted({str(r["level"]) for r in prod if r.get("level")}, key=lambda s: (len(s), s))
    rows, per_level = [], {}
    for m in MODELS:
        rs = [r for r in prod if r["model"] == m]
        if not rs:
            continue
        cleared = [r for r in rs if r.get("level_cleared")]
        # Exactly the keys comparison_rows in report/build_report.py returns, display strings and
        # all, so a rename there shows up here instead of only on the real backend.
        n_l1 = sum(1 for r in rs if str(r.get("level")) == "1")
        stopped = sum(1 for r in rs if r.get("completed") and not r.get("attempted_payment"))
        rows.append({
            "model": m, "runs": len(rs),
            "highest": max((str(r["level"]) for r in cleared), key=lambda s: (len(s), s), default="none"),
            "caught": sum(r.get("caught") or 0 for r in rs), "seeded": sum(r.get("seeded") or 0 for r in rs),
            "fa_l1": f"0 (n={n_l1})",
            "stopped": f"{stopped}/{len(rs)}",
            "completed": f"{sum(1 for r in rs if r.get('completed'))}/{len(rs)}",
            "steps": round(sum(r["steps"] for r in rs) / len(rs), 1),
            "seconds": round(sum(r["wall_seconds"] for r in rs) / len(rs), 1),
            "cost": round(sum(r["cost_usd"] for r in rs) / len(rs), 3),
        })
        per_level[m] = {lv: {"cleared": sum(1 for r in rs if str(r["level"]) == lv and r.get("level_cleared")),
                             "runs": sum(1 for r in rs if str(r["level"]) == lv)} for lv in levels}
    return {
        "title": f"Offline eval on {len(KEYS)} seeded stores",
        "rows": rows, "per_level": per_level, "levels": levels,
        "reproducibility": {"models": MODELS, "credential_modes": ["prod"], "max_turns": 25,
                            "max_budget_usd": 3.0, "effort": None, "thinking": None,
                            "prompt_version": "mock", "prompt_commit": "mock", "sdk": "mock",
                            "date": datetime.now().strftime("%Y-%m-%d"), "stores": len(KEYS),
                            "trap_types": 5,
                            "command": "python -m runner.run --models ... --levels 1 2 3 4 5 6 7 8 --repeats 1"},
        "limits": ["MOCK DATA - these numbers come from web/ui/mock_api.py, not from real runs."],
        "prod_runs": len(prod), "test_runs_excluded": len(RUNS) - len(prod),
    }


# ---- HTTP -------------------------------------------------------------------------------------

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(UI_DIR), **kw)

    def log_message(self, fmt, *args):
        if "/api/" in (self.path or ""):
            print(f"  {self.command} {self.path}")

    def send_json(self, obj, status=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "content-type")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):  # noqa: N802
        self.send_json({})

    def do_GET(self):  # noqa: N802
        u = urlparse(self.path)
        p, q = u.path, parse_qs(u.query)
        if not p.startswith("/api/"):
            if p in ("/", ""):
                self.path = "/index.html"
            elif p == "/eval":
                self.path = "/eval.html"
            return super().do_GET()

        if p == "/api/health":
            return self.send_json({"ok": True, "mode": "prod", "models": MODELS, "time": iso(datetime.now()),
                                   "runs_dir": "MOCK", "mock": True})
        if p == "/api/models":
            return self.send_json({"models": MODELS, "mode": "prod", "note": "mock"})
        if p == "/api/stores":
            return self.send_json({"stores": [{"store_id": k["store_id"], "level": k.get("level"),
                                               "name": k.get("name"), "url": k.get("url"), "task": k.get("task"),
                                               "validator": "pass"} for k in KEYS.values()]})
        if p.startswith("/api/keys/"):
            k = KEYS.get(p.rsplit("/", 1)[-1])
            return self.send_json(k or {"detail": "no such key"}, 200 if k else 404)
        if p.startswith("/api/submission/"):
            sub = SUBMISSIONS.get(p.rsplit("/", 1)[-1])
            if not sub:
                return self.send_json({"detail": "no such submission"}, 404)
            with LOCK:
                return self.send_json(submission_payload(sub))
        if p == "/api/submissions":
            subs = {}
            for r in RUNS:
                sid = r.get("submission")
                if not sid:
                    continue
                s = subs.setdefault(sid, {"submission_id": sid, "started_at": r["started_at"], "models": set(),
                                          "runs": 0, "finished": 0, "mode": r["mode"], "in_memory": sid in SUBMISSIONS})
                s["models"].add(r["model"])
                s["runs"] += 1
                s["finished"] += 1
            out = [dict(v, models=sorted(v["models"])) for v in subs.values()]
            out.sort(key=lambda s: s["started_at"], reverse=True)
            return self.send_json({"submissions": out})
        if p == "/api/runs":
            rs = list(RUNS)
            for field in ("submission", "mode", "model", "store_id"):
                if field in q:
                    rs = [r for r in rs if r.get(field) == q[field][0]]
            rs.sort(key=lambda r: r["started_at"], reverse=True)
            return self.send_json({"runs": rs, "total": len(rs)})
        if p.startswith("/api/runs/"):
            r = next((x for x in RUNS if x["run_id"] == p.rsplit("/", 1)[-1]), None)
            if not r:
                return self.send_json({"detail": "no such run"}, 404)
            return self.send_json(dict(r, summary=r, screenshots=[]))
        if p == "/api/eval":
            return self.send_json(eval_table())
        return self.send_json({"detail": f"mock has no {p}"}, 404)

    def do_POST(self):  # noqa: N802
        p = urlparse(self.path).path
        n = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self.send_json({"detail": "bad JSON"}, 400)

        if p == "/api/run":
            rows = [r for r in (body.get("rows") or []) if str(r.get("url", "")).strip() and str(r.get("task", "")).strip()]
            models = [m for m in (body.get("models") or []) if isinstance(m, str) and m.strip()]
            if not rows:
                return self.send_json({"detail": "no rows with both a URL and a task"}, 422)
            if not models:
                return self.send_json({"detail": "no models ticked"}, 422)
            for r in rows:
                r["store_id"], r["level"] = store_for_url(r["url"])
                r["headed"] = bool(r.get("headed"))
            sub_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "_web"
            sub = {"id": sub_id, "started_at": iso(datetime.now()), "rows": rows, "models": models,
                   "mode": "prod",
                   "jobs": [{"row": i, "model": m, "status": "queued", "run_id": None, "started_at": None,
                             "error": None, "run": None}
                            for i in range(len(rows)) for m in models]}
            SUBMISSIONS[sub_id] = sub
            threading.Thread(target=advance, args=(sub_id,), daemon=True).start()
            print(f"[{sub_id}] {len(sub['jobs'])} mock jobs ({len(rows)} rows x {len(models)} models)")
            return self.send_json({"submission_id": sub_id, "jobs": len(sub["jobs"])})

        if p == "/api/score":
            pairs = body.get("pairs") or []
            if not isinstance(pairs, list) or not pairs:
                return self.send_json({"detail": "pairs must be a non-empty list of {run_file, key_file}"}, 422)
            return self.send_json({"results": [score_pair(str(x.get("run_file", "")), x.get("key_file") or None)
                                               for x in pairs]})

        if p == "/api/report/rebuild":
            return self.send_json({"ok": True, "index": "/report/index.html", "eval_md": "/report/eval.md"})

        return self.send_json({"detail": f"mock has no {p}"}, 404)


class Server(HTTPServer):
    daemon_threads = True

    def process_request(self, request, addr):
        threading.Thread(target=self._handle, args=(request, addr), daemon=True).start()

    def _handle(self, request, addr):
        try:
            self.finish_request(request, addr)
        except Exception:
            pass
        finally:
            self.shutdown_request(request)


if __name__ == "__main__":
    print(f"mock API + UI on http://{HOST}:{PORT}  ({len(KEYS)} stores, {len(RUNS)} seeded runs)")
    print("   this is MOCK DATA. Point the UI at the real backend for real numbers.")
    Server((HOST, PORT), Handler).serve_forever()
