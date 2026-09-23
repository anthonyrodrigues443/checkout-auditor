"""The five browser tools the agent gets, wrapped around one Playwright page.

One BrowserSession per run. The model sees only text: URL, title, visible text,
and a numbered list of interactive elements. Screenshots go to disk for the report.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page

PAYMENT_WORDS = re.compile(
    r"\b(pay|pay now|place order|place your order|confirm order|complete purchase|complete order|"
    r"buy now|purchase|checkout now and pay|make payment|proceed to pay|pay securely|order now)\b",
    re.I,
)
CHECKPOINT_NAMES = ("first_price", "cart", "final")

SNAPSHOT_JS = r"""
() => {
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden' || s.opacity === '0') return false;
    if (r.width === 0 && r.height === 0) return false;
    let p = el;
    while (p) { const ps = getComputedStyle(p); if (ps.display === 'none' || ps.visibility === 'hidden') return false; p = p.parentElement; }
    return true;
  };
  const inModal = (el) => {
    let p = el;
    while (p) {
      const s = getComputedStyle(p);
      if ((s.position === 'fixed' || s.position === 'absolute') && parseInt(s.zIndex || '0') > 0) return true;
      p = p.parentElement;
    }
    return false;
  };
  const label = (el) => {
    const t = (el.innerText || el.value || el.getAttribute('aria-label') || el.getAttribute('title') || el.getAttribute('alt') || '').trim().replace(/\s+/g, ' ');
    if (t) return t;
    if (el.id) { const l = document.querySelector(`label[for="${el.id}"]`); if (l) return l.innerText.trim().replace(/\s+/g, ' '); }
    const wrap = el.closest('label'); if (wrap) return wrap.innerText.trim().replace(/\s+/g, ' ');
    return el.getAttribute('name') || el.tagName.toLowerCase();
  };
  const sel = 'a[href], button, input, select, textarea, [role=button], [role=link], [onclick]';
  const els = Array.from(document.querySelectorAll(sel)).filter(visible);
  const anyModal = els.some(inModal);
  const out = [];
  els.forEach((el) => {
    const tag = el.tagName.toLowerCase();
    const type = (el.getAttribute('type') || '').toLowerCase();
    let kind = tag === 'a' ? 'link' : tag === 'select' ? 'select' : (tag === 'input' && (type === 'checkbox' || type === 'radio')) ? type : (tag === 'input' && !['button','submit'].includes(type)) ? 'input' : 'button';
    if (tag === 'input' && ['hidden'].includes(type)) return;
    const item = { kind, label: label(el), modal: anyModal ? inModal(el) : false };
    if (kind === 'checkbox' || kind === 'radio') item.checked = el.checked;
    if (kind === 'select') {
      item.options = Array.from(el.options).map(o => o.text.trim().replace(/\s+/g, ' '));
      const so = el.options[el.selectedIndex];
      item.selected = so ? so.text.trim().replace(/\s+/g, ' ') : '';
    }
    if (kind === 'input') item.value = el.value;
    el.setAttribute('data-ca-idx', String(out.length + 1));
    out.push(item);
  });
  const text = (document.body.innerText || '').replace(/[ \t]+/g, ' ').replace(/\n{2,}/g, '\n').trim();
  return { url: location.href, title: window.__caOrigTitle || document.title, text, elements: out, modal: anyModal };
}
"""


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")


@dataclass
class RunState:
    run_id: str
    screenshot_dir: Path
    checkpoints: dict[str, Any] = field(default_factory=dict)
    actions: list[dict[str, Any]] = field(default_factory=list)
    attempted_payment: bool = False
    completed: bool = False
    step: int = 0
    stop_event: asyncio.Event = field(default_factory=asyncio.Event)
    last_snapshot: list[dict[str, Any]] = field(default_factory=list)
    last_screenshot: str | None = None


class BrowserSession:
    """Owns one context + page for one run and implements the five tool bodies."""

    def __init__(self, browser: Browser, state: RunState, overlay: bool = False):
        self.browser = browser
        self.state = state
        self.overlay = overlay
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    async def open(self, url: str, model_title: str | None = None, **context_kwargs):
        self.context = await self.browser.new_context(viewport={"width": 1100, "height": 800}, **context_kwargs)
        if model_title:
            await self.context.add_init_script(
                "document.addEventListener('DOMContentLoaded', () => { window.__caOrigTitle = document.title; "
                f"document.title = {model_title!r} + ' — ' + document.title; }});"
            )
        self.page = await self.context.new_page()
        await self.page.goto(url, wait_until="domcontentloaded")

    async def close(self):
        try:
            if self.context:
                await self.context.close()
        except Exception:
            pass

    async def _screenshot(self) -> str | None:
        assert self.page
        self.state.screenshot_dir.mkdir(parents=True, exist_ok=True)
        path = self.state.screenshot_dir / f"step_{self.state.step:02d}.png"
        try:
            await self.page.screenshot(path=str(path), full_page=False)
            rel = str(path.relative_to(self.state.screenshot_dir.parent.parent))
        except Exception:
            return None
        self.state.last_screenshot = rel
        return rel

    async def _show_overlay(self, text: str):
        if not self.overlay or not self.page:
            return
        try:
            await self.page.evaluate(
                """(t) => { let d = document.getElementById('ca-overlay'); if (!d) { d = document.createElement('div'); d.id = 'ca-overlay';
                d.style.cssText = 'position:fixed;left:0;right:0;bottom:0;background:#111;color:#fff;font:16px/1.4 monospace;padding:10px 14px;z-index:2147483647;opacity:.92;white-space:pre-wrap';
                document.body.appendChild(d);} d.textContent = t; }""",
                text,
            )
        except Exception:
            pass

    def _log(self, tool: str, args: dict, result: str, **extra):
        self.state.step += 1
        entry = {
            "step": self.state.step,
            "ts": _now(),
            "tool": tool,
            "args": args,
            "result": result[:2000],
            "blocked": False,
            "screenshot": None,
        }
        entry.update(extra)
        self.state.actions.append(entry)
        return entry

    # ---- tool bodies -------------------------------------------------------

    async def read_page(self) -> str:
        assert self.page
        await self.page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(0.15)
        snap = await self.page.evaluate(SNAPSHOT_JS)
        self.state.last_snapshot = snap["elements"]
        lines = [f"URL: {snap['url']}", f"Title: {snap['title']}"]
        if snap.get("modal"):
            lines.append("NOTE: a pop-up dialog is open; elements marked (in pop-up) belong to it.")
        lines.append("--- visible text ---")
        lines.append(snap["text"][:6000])
        lines.append("--- interactive elements ---")
        for i, el in enumerate(snap["elements"], 1):
            k = el["kind"]
            s = f"[{i}] {k} \"{el['label']}\""
            if k in ("checkbox", "radio"):
                s += " (checked)" if el.get("checked") else " (unchecked)"
            elif k == "select":
                s += f" options: {' | '.join(el.get('options', []))}, selected: {el.get('selected') or '(none)'}"
            elif k == "input" and el.get("value"):
                s += f" value=\"{el['value']}\""
            if el.get("modal"):
                s += " (in pop-up)"
            lines.append(s)
        out = "\n".join(lines)
        entry = self._log("read_page", {}, out)
        entry["screenshot"] = await self._screenshot()
        entry["url"] = snap["url"]
        await self._show_overlay(f"[{self.state.step}] read_page → {snap['title']}")
        return out

    def _element(self, index: int) -> dict | None:
        if 1 <= index <= len(self.state.last_snapshot):
            return self.state.last_snapshot[index - 1]
        return None

    async def click(self, index: int) -> str:
        assert self.page
        if self.state.completed:
            return "run already ended; do not call any more tools."
        el = self._element(index)
        if el is None:
            r = f"error: no element [{index}] in the last read_page; call read_page first"
            self._log("click", {"index": index}, r)
            return r
        label = el["label"]
        if PAYMENT_WORDS.search(label):
            self.state.attempted_payment = True
            r = "blocked: payment action. This tool never pays or places orders. Record the final checkpoint and call stop_before_payment."
            entry = self._log("click", {"index": index}, r, element_text=label, blocked=True)
            entry["screenshot"] = await self._screenshot()
            await self._show_overlay(f"[{self.state.step}] click [{index}] \"{label}\" → BLOCKED (payment)")
            return r
        await self._show_overlay(f"[{self.state.step + 1}] click [{index}] \"{label}\"")
        try:
            loc = self.page.locator(f"[data-ca-idx='{index}']")
            await loc.first.click(timeout=5000)
            await self.page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(0.25)
            r = f"clicked [{index}] \"{label}\". Now at {self.page.url}. Call read_page to see the result."
        except Exception as e:  # noqa: BLE001
            r = f"error clicking [{index}] \"{label}\": {type(e).__name__}: {str(e)[:200]}. Call read_page and try again."
        entry = self._log("click", {"index": index}, r, element_text=label)
        entry["screenshot"] = await self._screenshot()
        return r

    async def select_option(self, index: int, option_text: str) -> str:
        assert self.page
        if self.state.completed:
            return "run already ended; do not call any more tools."
        el = self._element(index)
        if el is None or el["kind"] != "select":
            r = f"error: [{index}] is not a select in the last read_page"
            self._log("select_option", {"index": index, "option_text": option_text}, r)
            return r
        label = el["label"]
        options = el.get("options", [])
        want = option_text.strip().lower()
        match = next((o for o in options if o.lower() == want), None) or next(
            (o for o in options if want in o.lower() or o.lower() in want), None
        )
        if match is None:
            r = f"error: no option matching \"{option_text}\" in {options}"
            self._log("select_option", {"index": index, "option_text": option_text}, r, element_text=label)
            return r
        await self._show_overlay(f"[{self.state.step + 1}] select [{index}] \"{label}\" = {match}")
        try:
            await self.page.locator(f"[data-ca-idx='{index}']").first.select_option(label=match, timeout=5000)
            await asyncio.sleep(0.25)
            r = f"selected \"{match}\" in [{index}] \"{label}\". Call read_page to see the result."
        except Exception as e:  # noqa: BLE001
            r = f"error selecting: {type(e).__name__}: {str(e)[:200]}"
        entry = self._log(
            "select_option", {"index": index, "option_text": option_text}, r, element_text=f"{label}: {match}"
        )
        entry["screenshot"] = await self._screenshot()
        return r

    async def record_checkpoint(self, name: str, line_items: list[dict], total: float) -> str:
        args = {"name": name, "line_items": line_items, "total": total}
        if name not in CHECKPOINT_NAMES:
            r = f"error: name must be one of {CHECKPOINT_NAMES}"
            self._log("record_checkpoint", args, r)
            return r
        items = []
        for it in line_items or []:
            try:
                items.append(
                    {
                        "label": str(it.get("label", "")).strip(),
                        "amount": float(it.get("amount", 0)),
                        "chosen_by_me": bool(it.get("chosen_by_me", False)),
                        "pre_selected": bool(it.get("pre_selected", False)),
                    }
                )
            except (TypeError, ValueError, AttributeError):
                r = f"error: bad line item {it!r}"
                self._log("record_checkpoint", args, r)
                return r
        s = round(sum(i["amount"] for i in items), 2)
        if abs(s - float(total)) > 0.01:
            r = f"error: line items sum to {s:g} but total given is {float(total):g}. List every visible line item so they add up to the total, then record again."
            self._log("record_checkpoint", args, r)
            return r
        self.state.checkpoints[name] = {
            "line_items": items,
            "total": float(total),
            "url": self.page.url if self.page else None,
            "step": self.state.step + 1,
            "screenshot": self.state.last_screenshot,
            "recorded_at": _now(),
        }
        r = f"recorded checkpoint {name}: {len(items)} items, total {float(total):g}"
        self._log("record_checkpoint", args, r)
        await self._show_overlay(f"[{self.state.step}] checkpoint {name} = ₹{float(total):g}")
        return r

    async def stop_before_payment(self) -> str:
        if "final" not in self.state.checkpoints:
            r = "error: record the final checkpoint (the bill on the last review screen) before stopping."
            self._log("stop_before_payment", {}, r)
            return r
        self.state.completed = True
        r = "run ended before payment. Do not call any more tools; reply with one line saying you are done."
        entry = self._log("stop_before_payment", {}, r)
        entry["screenshot"] = await self._screenshot()
        await self._show_overlay(f"[{self.state.step}] stop_before_payment ✔")
        self.state.stop_event.set()
        return r


def build_tools(session: BrowserSession):
    """Return the five SDK tool objects bound to this session."""
    from claude_agent_sdk import tool

    def text(s: str) -> dict:
        return {"content": [{"type": "text", "text": s}]}

    @tool("read_page", "Read the current page: URL, title, visible text with prices, and a numbered list of interactive elements you can act on.", {})
    async def read_page(args: dict) -> dict:
        return text(await session.read_page())

    @tool("click", "Click the interactive element with this number from the last read_page. Refuses anything that pays or places an order.", {"index": int})
    async def click(args: dict) -> dict:
        return text(await session.click(int(args["index"])))

    @tool("select_option", "Choose an option in a select element by its number from the last read_page and the option's visible text.", {"index": int, "option_text": str})
    async def select_option(args: dict) -> dict:
        return text(await session.select_option(int(args["index"]), str(args["option_text"])))

    @tool(
        "record_checkpoint",
        "Record the visible bill. name is one of first_price, cart, final. line_items is a list of {label, amount, chosen_by_me, pre_selected}; amounts are numbers in rupees (discounts negative) and must add up to total.",
        {
            "type": "object",
            "properties": {
                "name": {"type": "string", "enum": list(CHECKPOINT_NAMES)},
                "line_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {"type": "string"},
                            "amount": {"type": "number"},
                            "chosen_by_me": {"type": "boolean"},
                            "pre_selected": {"type": "boolean"},
                        },
                        "required": ["label", "amount", "chosen_by_me", "pre_selected"],
                    },
                },
                "total": {"type": "number"},
            },
            "required": ["name", "line_items", "total"],
        },
    )
    async def record_checkpoint(args: dict) -> dict:
        return text(await session.record_checkpoint(args["name"], args.get("line_items", []), args["total"]))

    @tool("stop_before_payment", "End the audit. Only valid after the final checkpoint has been recorded.", {})
    async def stop_before_payment(args: dict) -> dict:
        return text(await session.stop_before_payment())

    return [read_page, click, select_option, record_checkpoint, stop_before_payment]


TOOL_NAMES = ["read_page", "click", "select_option", "record_checkpoint", "stop_before_payment"]
