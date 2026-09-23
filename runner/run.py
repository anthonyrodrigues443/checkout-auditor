"""Run models × levels × repeats in parallel and write one JSON per run into runs/.

    AUDITOR_MODE=prod .venv/bin/python -m runner.run --models claude-fable-5-1 claude-fable-5 --levels 1 2 3 4 --repeats 1
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from itertools import product
from pathlib import Path

from playwright.async_api import async_playwright

from agent.harness import (
    DEFAULT_MAX_BUDGET_USD, DEFAULT_MAX_TURNS, ROOT, RUNS_DIR, TEST_DEFAULT_MODEL, ensure_store_server, get_mode,
    launch_browser, run_audit, sdk_env_for_mode,
)

KEYS_DIR = ROOT / "stores" / "keys"


def load_key(level: str) -> dict:
    p = KEYS_DIR / f"l{level}.json" if str(level).isdigit() else KEYS_DIR / f"{level}.json"
    if not p.exists():
        raise SystemExit(f"no answer key for level {level} at {p}")
    return json.loads(p.read_text())


def try_score(record: dict) -> str:
    try:
        from checker.score import load_key_for, score_run
        key = load_key_for(record)
        if not key:
            return "unscored"
        s = score_run(record, key)
        return s.get("verdict_line") or f"caught {s.get('caught')}/{s.get('seeded')} fa {s.get('false_alarms')}"
    except Exception as e:  # noqa: BLE001
        return f"(checker: {type(e).__name__}: {str(e)[:60]})"


def fmt_row(r: dict) -> str:
    cost = f"${r['cost_usd']:.3f}" if r.get("cost_usd") is not None else "-"
    return (f"{r['model']:<28} L{r['level']!s:<3} {r['status']:<10} done={str(r['completed']):<5} "
            f"pay={str(r['attempted_payment']):<5} steps={r['steps']:<3} {r['wall_seconds']:>6}s {cost:>8}  {r.get('_verdict','')}")


async def main(a: argparse.Namespace) -> int:
    mode = get_mode()
    if mode == "test" and len(a.models or []) > 1 and not a.force:
        raise SystemExit("refusing a multi-model comparison in test mode (subscription runs are not comparable); use --force")
    if a.eval and mode == "test":
        mode = "cli"
        print("comparison runs over the Claude Code login: stamping mode=cli (included in the eval table, labelled)")
    sdk_env = sdk_env_for_mode(mode)
    models = a.models or [TEST_DEFAULT_MODEL if mode == "test" else "claude-fable-5-1"]
    submission = a.submission or datetime.now().strftime("%Y%m%d-%H%M%S") + "_" + "+".join(m.replace("claude-", "") for m in models)
    server_proc = ensure_store_server(8000)
    jobs = []
    alt = {}
    if a.task_set != "key":
        f = ROOT / "runner" / ("alt_tasks.json" if a.task_set == "alt" else f"tasks_{a.task_set}.json")
        if not f.exists():
            raise SystemExit(f"no task set file {f}")
        alt = json.loads(f.read_text())
    for level, model, rep in product(a.levels, models, range(1, a.repeats + 1)):
        key = load_key(level)
        task = a.task or (alt.get(key["store_id"]) if a.task_set != "key" else None) or key["task"]
        if a.task_set != "key" and key["store_id"] not in alt and not a.task:
            print(f"skip L{level}: no {a.task_set} task for {key['store_id']}")
            continue
        jobs.append({"model": model, "level": level, "repeat": rep, "task": task,
                     "store_url": key.get("url") or f"http://localhost:8000/l{level}/", "store_id": key["store_id"],
                     "task_variant": "custom" if a.task else a.task_set})
    print(f"mode={mode} submission={submission} jobs={len(jobs)} concurrency={a.concurrency} cap=${a.max_total_usd}")
    spent = 0.0
    done: list[dict] = []
    sem = asyncio.Semaphore(a.concurrency)
    stop_launching = False
    first_prod_done = False

    async with async_playwright() as pw:
        browsers: dict[str, object] = {}
        if a.headed:
            n = len(models)
            w = max(420, a.screen_width // n)
            for i, m in enumerate(models):
                browsers[m] = await launch_browser(pw, headed=True, position=(i * w, 0), size=(w, a.screen_height))
        else:
            shared = await launch_browser(pw, headed=False)
            browsers = {m: shared for m in models}

        async def one(job: dict):
            nonlocal spent, stop_launching, first_prod_done
            async with sem:
                if stop_launching:
                    print(f"skip {job['model']} L{job['level']} r{job['repeat']}: spend cap reached")
                    return None
                t0 = time.time()
                print(f"start {job['model']} L{job['level']} r{job['repeat']} ({job['task']})")
                rec = await run_audit(
                    browsers[job["model"]], model=job["model"], store_url=job["store_url"], task=job["task"],
                    level=job["level"], store_id=job["store_id"], mode=mode, repeat=job["repeat"],
                    max_turns=a.max_turns, max_budget_usd=a.max_budget_usd, effort=a.effort, overlay=a.headed,
                    window_title=job["model"] if a.headed else None, sdk_env=sdk_env, submission=submission,
                    task_variant=job["task_variant"],
                )
                rec["_verdict"] = try_score(rec)
                spent += rec.get("cost_usd") or 0.0
                done.append(rec)
                print(fmt_row(rec) + f"   total spend so far: ${spent:.2f}")
                if rec.get("error"):
                    print(f"   error: {rec['error']}")
                if mode == "prod" and not first_prod_done and rec["status"] != "error":
                    first_prod_done = True
                    print("   >>> first prod run finished: check Console usage to confirm it billed to the API key <<<")
                if spent >= a.max_total_usd:
                    stop_launching = True
                    print(f"   spend cap ${a.max_total_usd} reached; no new runs will start")
                return rec

        await asyncio.gather(*(one(j) for j in jobs))
        for b in set(id(x) for x in browsers.values()):
            pass
        for b in {id(x): x for x in browsers.values()}.values():
            await b.close()

    print("\n=== summary ===")
    for r in sorted(done, key=lambda r: (str(r["level"]), r["model"], r["run_id"])):
        print(fmt_row(r))
    print(f"runs written: {len(done)}  total spend: ${spent:.2f}  submission: {submission}")
    if server_proc:
        server_proc.terminate()
    return 0


def parse(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--models", nargs="*", default=None, help="full model IDs, never aliases")
    ap.add_argument("--levels", nargs="+", default=["1", "2", "3", "4"])
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--task", default=None, help="override the task sentence for every job")
    ap.add_argument("--submission", default=None, help="name grouping these runs in the audit report")
    ap.add_argument("--task-set", default="key", help="key = the store's task; alt = runner/alt_tasks.json; <name> = runner/tasks_<name>.json")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--max-turns", type=int, default=DEFAULT_MAX_TURNS)
    ap.add_argument("--max-budget-usd", type=float, default=DEFAULT_MAX_BUDGET_USD, help="per-run cap")
    ap.add_argument("--max-total-usd", type=float, default=25.0, help="stop launching once total spend crosses this")
    ap.add_argument("--effort", default=None, choices=[None, "low", "medium", "high", "xhigh", "max"])
    ap.add_argument("--headed", action="store_true", help="one tiled window per model (recording only)")
    ap.add_argument("--screen-width", type=int, default=1440)
    ap.add_argument("--screen-height", type=int, default=820)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--eval", action="store_true", help="comparison intent: in test mode (with --force) runs are stamped mode=cli and enter the eval table")
    a = ap.parse_args(argv)
    if os.environ.get("AUDITOR_HEADED") == "1":
        a.headed = True
    return a


if __name__ == "__main__":
    sys.exit(asyncio.run(main(parse())))
