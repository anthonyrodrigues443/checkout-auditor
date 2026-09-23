"""Proof that the agent has exactly the five shop tools and no built-ins.

Runs one tiny conversation (test mode, no key) and reads the tool list Claude Code announces at init.
    AUDITOR_MODE=test .venv/bin/python -m agent.test_surface
"""

import asyncio
import sys

from playwright.async_api import async_playwright

from agent.harness import MCP_TOOL_NAMES, TEST_FALLBACK_MODEL, get_mode, launch_browser, make_options, sdk_env_for_mode
from agent.tools import BrowserSession, RunState, build_tools
from agent.harness import RUNS_DIR


async def main(model: str) -> int:
    from claude_agent_sdk import ClaudeSDKClient, SystemMessage, ResultMessage, create_sdk_mcp_server

    env = sdk_env_for_mode(get_mode())
    async with async_playwright() as pw:
        browser = await launch_browser(pw)
        state = RunState(run_id="surface-test", screenshot_dir=RUNS_DIR / "screenshots" / "surface-test")
        session = BrowserSession(browser, state)
        await session.open("about:blank")
        server = create_sdk_mcp_server("shop", tools=build_tools(session))
        opts = make_options(server, model=model, max_turns=2, max_budget_usd=0.5, sdk_env=env)
        announced = None
        async with ClaudeSDKClient(options=opts) as client:
            await client.query("Reply with the single word OK and call no tools.")
            async for msg in client.receive_response():
                if isinstance(msg, SystemMessage) and msg.subtype == "init":
                    announced = list((msg.data or {}).get("tools", []))
                elif isinstance(msg, ResultMessage):
                    print("result:", msg.subtype, "cost:", msg.total_cost_usd, "model_usage keys:", list((msg.model_usage or {}).keys()))
        await session.close()
        await browser.close()
    print("announced tools:", announced)
    if announced is None:
        print("FAIL: no init message with a tool list")
        return 1
    extra = sorted(set(announced) - set(MCP_TOOL_NAMES))
    missing = sorted(set(MCP_TOOL_NAMES) - set(announced))
    if extra or missing:
        print(f"FAIL: extra={extra} missing={missing}")
        return 1
    print("PASS: agent has exactly the five shop tools")
    return 0


if __name__ == "__main__":
    model = sys.argv[1] if len(sys.argv) > 1 else TEST_FALLBACK_MODEL
    raise SystemExit(asyncio.run(main(model)))
