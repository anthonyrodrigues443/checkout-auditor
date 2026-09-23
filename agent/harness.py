"""Claude Agent SDK loop around the five browser tools. One call = one fresh conversation = one run record."""

from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.async_api import Browser, async_playwright

from agent.prompts import PROMPT_VERSION, SYSTEM_PROMPT, user_prompt
from agent.tools import SNAPSHOT_VERSION, TEXT_CAP, TOOL_NAMES, BrowserSession, RunState, build_tools

ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = ROOT / "runs"
SERVER_NAME = "shop"
MCP_TOOL_NAMES = [f"mcp__{SERVER_NAME}__{t}" for t in TOOL_NAMES]
BUILTIN_TOOLS = [
    "Bash", "Read", "Write", "Edit", "MultiEdit", "Glob", "Grep", "LS", "WebFetch", "WebSearch", "Task", "Agent",
    "TodoWrite", "NotebookEdit", "Skill", "BashOutput", "KillShell", "ExitPlanMode", "EnterPlanMode",
    "AskUserQuestion", "ToolSearch", "Monitor", "ListMcpResourcesTool", "ReadMcpResourceTool",
]
TEST_DEFAULT_MODEL = "claude-opus-5"
TEST_FALLBACK_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_MAX_TURNS = 25
DEFAULT_MAX_BUDGET_USD = 3.0
RUN_TIMEOUT_S = 600


# ---- mode / credentials ------------------------------------------------------

def get_mode() -> str:
    mode = os.environ.get("AUDITOR_MODE", "test").strip().lower()
    if mode not in ("test", "prod", "cli"):
        raise SystemExit(f"AUDITOR_MODE must be test, prod or cli, got {mode!r}")
    return mode


def load_prod_key() -> str:
    """Read ANTHROPIC_API_KEY from .env in the repo root. Only the runner calls this, only in prod."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        raise SystemExit("prod mode needs .env with ANTHROPIC_API_KEY=... in the repo root")
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line.startswith("ANTHROPIC_API_KEY="):
            key = line.split("=", 1)[1].strip().strip('"').strip("'")
            if key:
                return key
    raise SystemExit("ANTHROPIC_API_KEY missing or empty in .env")


def sdk_env_for_mode(mode: str) -> dict[str, str]:
    """Env passed to the SDK subprocess. test/cli: no key at all (Claude Code login). prod: key from .env.

    cli = comparison runs made deliberately over the Claude Code login; they enter the eval table labelled as such.
    test = debugging runs; never in the table."""
    if mode == "prod":
        return {"ANTHROPIC_API_KEY": load_prod_key()}
    os.environ.pop("ANTHROPIC_API_KEY", None)
    return {}


# ---- store server --------------------------------------------------------------

def port_open(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex((host, port)) == 0


def ensure_store_server(port: int = 8000) -> subprocess.Popen | None:
    if port_open(port):
        return None
    www = ROOT / "stores" / "www"
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--directory", str(www), "--bind", "127.0.0.1"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    for _ in range(30):
        if port_open(port):
            break
        time.sleep(0.1)
    return proc


# ---- browser -------------------------------------------------------------------

async def launch_browser(pw, headed: bool = False, position: tuple[int, int] | None = None,
                         size: tuple[int, int] | None = None) -> Browser:
    args = []
    if headed and position:
        args.append(f"--window-position={position[0]},{position[1]}")
    if headed and size:
        args.append(f"--window-size={size[0]},{size[1]}")
    return await pw.chromium.launch(headless=not headed, args=args)


# ---- one run ---------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def make_run_id(model: str, level: int | str, repeat: int) -> str:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    lvl = f"L{level}" if str(level).isdigit() else str(level)
    return f"{ts}_{model}_{lvl}_r{repeat}"


async def run_audit(
    browser: Browser,
    *,
    model: str,
    store_url: str,
    task: str,
    level: int | str,
    store_id: str,
    mode: str,
    repeat: int = 1,
    max_turns: int = DEFAULT_MAX_TURNS,
    max_budget_usd: float | None = DEFAULT_MAX_BUDGET_USD,
    effort: str | None = None,
    overlay: bool = False,
    window_title: str | None = None,
    runs_dir: Path = RUNS_DIR,
    sdk_env: dict[str, str] | None = None,
    submission: str | None = None,
    task_variant: str = "key",
    on_event=None,
) -> dict[str, Any]:
    from claude_agent_sdk import (
        AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient, HookMatcher, ResultMessage, SystemMessage, TextBlock,
        ToolUseBlock, create_sdk_mcp_server,
    )

    run_id = make_run_id(model, level, repeat)
    runs_dir.mkdir(parents=True, exist_ok=True)
    state = RunState(run_id=run_id, screenshot_dir=runs_dir / "screenshots" / run_id)
    session = BrowserSession(browser, state, overlay=overlay)
    started = time.time()
    record: dict[str, Any] = {
        "run_id": run_id, "mode": mode, "model": model, "level": level, "store_id": store_id,
        "store_url": store_url, "task": task, "task_variant": task_variant, "submission": submission,
        "started_at": _now_iso(), "ended_at": None, "wall_seconds": None,
        "steps": 0, "num_turns": 0, "completed": False, "attempted_payment": False,
        "status": "error", "error": None, "checkpoints": {"first_price": None, "cart": None, "final": None},
        "actions": [], "usage": {}, "cost_usd": None, "final_text": None,
        "settings": {
            "max_turns": max_turns, "max_budget_usd": max_budget_usd, "effort": effort, "thinking": None,
            "prompt_version": PROMPT_VERSION, "prompt_commit": git_commit(), "tools": TOOL_NAMES, "text_cap": TEXT_CAP, "snapshot_version": SNAPSHOT_VERSION,
            "sdk": sdk_version(),
        },
        "sdk_result": None,
    }

    hook_log: list[dict[str, Any]] = []

    async def pre_hook(inp, tool_use_id, ctx):
        hook_log.append({"ts": _now_iso(), "event": "pre", "tool": inp.get("tool_name"),
                         "args": inp.get("tool_input"), "tool_use_id": tool_use_id})
        return {}

    async def post_hook(inp, tool_use_id, ctx):
        resp = inp.get("tool_response")
        preview = json.dumps(resp)[:300] if not isinstance(resp, str) else resp[:300]
        hook_log.append({"ts": _now_iso(), "event": "post", "tool": inp.get("tool_name"),
                         "result_preview": preview, "tool_use_id": tool_use_id})
        if on_event:
            on_event(run_id, inp.get("tool_name"), state)
        return {}

    try:
        await session.open(store_url, model_title=window_title)
        tools = build_tools(session)
        server = create_sdk_mcp_server(SERVER_NAME, version="1.0.0", tools=tools)
        opts = make_options(
            server, model=model, max_turns=max_turns, max_budget_usd=max_budget_usd, effort=effort,
            sdk_env=sdk_env, runs_dir=runs_dir,
            hooks={
                "PreToolUse": [HookMatcher(matcher=None, hooks=[pre_hook])],
                "PostToolUse": [HookMatcher(matcher=None, hooks=[post_hook])],
            },
        )
        texts: list[str] = []
        result: ResultMessage | None = None
        tool_calls_seen: list[str] = []

        async def converse():
            nonlocal result
            async with ClaudeSDKClient(options=opts) as client:
                info = await client.get_server_info()
                record["settings"]["server_tools"] = _tool_names_from_info(info)
                await client.query(user_prompt(store_url, task))
                async for msg in client.receive_response():
                    if isinstance(msg, SystemMessage) and msg.subtype == "init":
                        record["settings"]["server_tools"] = list((msg.data or {}).get("tools", []))
                    elif isinstance(msg, AssistantMessage):
                        for b in msg.content:
                            if isinstance(b, TextBlock):
                                texts.append(b.text)
                            elif isinstance(b, ToolUseBlock):
                                tool_calls_seen.append(b.name)
                    elif isinstance(msg, ResultMessage):
                        result = msg

        await asyncio.wait_for(converse(), timeout=RUN_TIMEOUT_S)

        record["final_text"] = (texts[-1] if texts else None)
        record["tool_calls_seen"] = tool_calls_seen
        if result is not None:
            record["num_turns"] = result.num_turns
            record["cost_usd"] = result.total_cost_usd
            record["usage"] = result.usage or {}
            record["sdk_result"] = {
                "subtype": result.subtype, "is_error": result.is_error, "stop_reason": result.stop_reason,
                "duration_ms": result.duration_ms, "duration_api_ms": result.duration_api_ms,
                "model_usage": result.model_usage, "errors": getattr(result, "errors", None),
                "terminal_reason": getattr(result, "terminal_reason", None), "result": (result.result or "")[:500],
            }
            unexpected = [t for t in tool_calls_seen if t not in MCP_TOOL_NAMES]
            if unexpected:
                record["error"] = f"unexpected tool calls: {sorted(set(unexpected))}"
        if state.completed:
            record["status"] = "completed"
        elif result is not None and result.subtype in ("error_max_turns", "error_max_budget_usd") or (
            result is not None and "max" in (result.subtype or "")
        ):
            record["status"] = "incomplete"
            record["error"] = record["error"] or f"cap hit: {result.subtype}"
        elif result is not None and result.is_error:
            record["status"] = "error"
            record["error"] = record["error"] or f"{result.subtype}: {(result.result or '')[:300]}"
        else:
            record["status"] = "incomplete"
            record["error"] = record["error"] or "agent ended without stop_before_payment"
    except asyncio.TimeoutError:
        record["status"] = "incomplete"
        record["error"] = f"timeout after {RUN_TIMEOUT_S}s"
    except Exception as e:  # noqa: BLE001
        record["status"] = "error"
        record["error"] = f"{type(e).__name__}: {str(e)[:500]}"
    finally:
        await session.close()

    record["ended_at"] = _now_iso()
    record["wall_seconds"] = round(time.time() - started, 1)
    record["steps"] = state.step
    record["completed"] = state.completed
    record["attempted_payment"] = state.attempted_payment
    for name in ("first_price", "cart", "final"):
        record["checkpoints"][name] = state.checkpoints.get(name)
    record["actions"] = state.actions
    record["hook_log"] = hook_log
    path = runs_dir / f"{run_id}.json"
    path.write_text(json.dumps(record, indent=1, ensure_ascii=False))
    record["_path"] = str(path)
    return record


def make_options(server, *, model: str, max_turns: int = DEFAULT_MAX_TURNS,
                 max_budget_usd: float | None = DEFAULT_MAX_BUDGET_USD, effort: str | None = None,
                 sdk_env: dict[str, str] | None = None, runs_dir: Path = RUNS_DIR, hooks=None):
    """The one place the agent's settings are defined. Identical for every model."""
    from claude_agent_sdk import ClaudeAgentOptions

    return ClaudeAgentOptions(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[],
        disallowed_tools=BUILTIN_TOOLS,
        allowed_tools=MCP_TOOL_NAMES,
        mcp_servers={SERVER_NAME: server},
        strict_mcp_config=True,
        permission_mode="dontAsk",
        max_turns=max_turns,
        max_budget_usd=max_budget_usd,
        effort=effort,
        setting_sources=[],
        cwd=str(runs_dir),
        env=sdk_env or {},
        hooks=hooks,
    )


def _tool_names_from_info(info) -> list[str]:
    if not isinstance(info, dict):
        return []
    tools = info.get("tools") or []
    out = []
    for t in tools:
        out.append(t.get("name") if isinstance(t, dict) else str(t))
    return out


def git_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


def sdk_version() -> str | None:
    try:
        import importlib.metadata as m
        return m.version("claude-agent-sdk")
    except Exception:
        return None


# ---- debug entry point -------------------------------------------------------------

async def _debug(level: int, model: str | None, headed: bool, max_turns: int):
    mode = get_mode()
    env = sdk_env_for_mode(mode)
    model = model or (TEST_DEFAULT_MODEL if mode == "test" else "claude-fable-5-1")
    key = json.loads((ROOT / "stores" / "keys" / f"l{level}.json").read_text())
    ensure_store_server(8000)
    async with async_playwright() as pw:
        browser = await launch_browser(pw, headed=headed)
        rec = await run_audit(
            browser, model=model, store_url=f"http://localhost:8000/l{level}/", task=key["task"], level=level,
            store_id=f"l{level}", mode=mode, max_turns=max_turns, overlay=headed, sdk_env=env,
        )
        await browser.close()
    slim = {k: v for k, v in rec.items() if k not in ("actions", "hook_log", "sdk_result")}
    print(json.dumps(slim, indent=1, ensure_ascii=False))
    print("actions:")
    for a in rec["actions"]:
        print(f"  {a['step']:>2} {a['tool']:<20} {json.dumps(a['args'])[:80]:<82} -> {a['result'][:90]!r}")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--level", type=int, default=1)
    ap.add_argument("--model", default=None)
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--max-turns", type=int, default=15)
    a = ap.parse_args()
    asyncio.run(_debug(a.level, a.model, a.headed or os.environ.get("AUDITOR_HEADED") == "1", a.max_turns))
