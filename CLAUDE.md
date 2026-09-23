# Checkout Auditor — Build Day brief for Claude Code

You are my pair for a 2h50m buildathon (Mumbai, Claude Fable 5.1 Build Day). Build starts 17:40 IST, demos at 20:30. Everything must be demoable by 20:20. I am solo.

Read this whole file before writing any code. Follow the milestones in order. Do not gold-plate. When a time box runs out, cut scope inside that milestone; never skip the checker or the results page, because the report is the committed deliverable.

---

## 1. What we are building

A browser agent that audits a checkout journey for hidden charges.

Given a store URL and a one-sentence shopping task, the agent:
1. reads each page and decides the next click itself (no per-site code),
2. picks only what the task asks for, declines nothing the site pre-selected (leaves it as found and reports it),
3. records the visible bill at three checkpoints: first price seen, cart, final review screen,
4. stops before payment (it physically cannot pay: there is no typing tool, and the click tool refuses payment buttons),
5. hands its checkpoints and action log to plain Python, which finds:
   - **basket sneaking**: items in the final bill the shopper never chose,
   - **drip pricing**: charges in the final total that were not visible at the first price screen and are not a chosen option,
   - **unexplained gap**: final total minus (first price + chosen items + upfront-disclosed charges) ≠ 0.
6. writes an audit report with screenshots and, when several models were run, a side-by-side comparison table.

Same harness, model swapped by full ID. The demo claim is: "the last model choked as the agent, this one gets further" — so the comparison must be fair and the numbers honest.

Rules that never change:
- The model does perception and decisions. Python does every sum and every comparison. The model never adds numbers.
- Model IDs are always full IDs, never aliases (`fable` means 5.1 in Claude Code; using it for both runs would compare 5.1 with itself).
- Never force tool use (`tool_choice`); Fable 5.1 returns an error for forced tool use. Leave it on auto and verify in code that the expected tool calls happened.
- Identical settings for every model in a comparison (system prompt, tools, step cap, effort/thinking settings). If a model rejects a parameter, drop it for all models.
- Each run is a fresh conversation. Never pass one model's history to another (5.1 thinking blocks are unreadable by earlier models).

---

## 2. Stack and constraints

- Python 3.10+. Packages: `claude-agent-sdk`, `playwright` (Chromium already installed at home; do not re-download unless missing).
- Claude Agent SDK runs the loop (`ClaudeSDKClient`, needed for custom tools and hooks). No LangChain.
- **Browser control decision: the Playwright Python library wrapped in our own five tools. Not Playwright MCP, not Playwright CLI.** Reasons, so you don't relitigate it mid-build:
  - Playwright MCP streams a full accessibility-tree snapshot into the model's context on every step and ships ~23 tools including typing and form-filling. The Playwright team's own benchmark puts a typical browser task at roughly 114k tokens over MCP. It also has no idea what a "payment button" is, so the stop guardrail would have to be bolted on with hooks.
  - Playwright CLI (`@playwright/cli`) is the token-efficient option (~27k tokens for the same task) but only because the agent runs shell commands and reads snapshot files from disk. That requires giving our agent Bash and Read, which destroys the "five tools, no typing, cannot pay" story and makes the tool surface different from what a product would ship. It is built for coding agents like Claude Code, not for an agent inside a product.
  - Our own tools give the smallest surface (five), the smallest snapshots (we control the format: on these stores a few hundred tokens per step), the guardrails in code, identical tools for every model, and a harness that is genuinely my work. Cost: about 40 minutes of build time, which is Milestone 2.
  - Implementation hint for `read_page`: build the numbered element list with one `page.evaluate` over visible interactive elements (buttons, links, inputs, selects, checkboxes) plus the visible text, filtered by visibility so hidden DOM never counts as "shown to the shopper". If the installed Playwright offers an aria snapshot with element refs, you may use it as the base, but the output format in M2 is the contract.
- Built-in tools OFF. `allowed_tools` only pre-approves; it does not remove tools. Use `disallowed_tools` to block every built-in (Read, Write, Edit, Bash, Glob, Grep, WebFetch, WebSearch, Task, and any others) and prove it with a test that the agent has only our tools.
- Custom tools are in-process MCP tools (`@tool` + `create_sdk_mcp_server`), named `mcp__<server>__<tool>`. Pre-approve them in `allowed_tools`.
- Before writing SDK code, check the installed package for exact parameter and class names (`python -c "import claude_agent_sdk, inspect; print(inspect.signature(claude_agent_sdk.ClaudeAgentOptions))"` and the hooks types). Your memory of this SDK may predate Fable 5.1. Trust the installed code over memory.
- API key from `ANTHROPIC_API_KEY`. Measured runs bill to the API, not to my Claude Code login. After the first measured run I will check the Console usage page myself; remind me.
- **Run modes via `AUDITOR_MODE`** (`test` is the default, `prod` for anything that goes in the report). Same harness code in both; only the credentials the SDK sees change:
  - `test`: do not pass `ANTHROPIC_API_KEY` to the SDK (strip it from the environment handed to the client, or via the SDK's env option if it has one), so runs use my Claude Code login and draw on subscription limits. Default model: `claude-opus-5`, so a failed debug run points at the harness, not the model. Keep debug runs short (one store, step cap 15) because they share the five-hour window with Claude Code itself; fall back to `claude-haiku-4-5-20251001` if that window runs low. Every run JSON is stamped `mode: test`, and the report **excludes** test-mode runs from the comparison table, so debugging runs never leak into the eval.
  - `prod`: load `ANTHROPIC_API_KEY` from `.env` in the repo root (gitignored) inside the runner, fail fast if it is missing, pass it to the SDK, stamp runs `mode: prod`, and print "check Console usage" after the first completed run (there is a known case of cached login credentials overriding a key, so I verify billing by eye).
  - **Never export the key in the shell that runs Claude Code.** Claude Code picks up `ANTHROPIC_API_KEY` from its environment and would bill its own coding work to the credits instead of my subscription. The key lives only in `.env`, read only by the runner, only in `prod`.
  - The runner refuses to launch multi-model comparison runs in `test` mode unless `--force` is given, because the subscription may not expose `claude-fable-5` and those runs would not be comparable anyway.
- Fake stores are static HTML + JS served with `python -m http.server`. No backend, no database.
- Keep the repo small and readable. Commit at the end of every milestone with a plain message.

Repo layout:
```
checkout-auditor/
  stores/           # l1/ l2/ l3/ l4/ (served), each: index.html cart.html options.html summary.html pay.html + assets
  stores/keys/      # l1.json … answer keys, NOT served
  agent/            # tools.py (Playwright tools), harness.py (SDK loop), prompts.py
  checker/          # checks.py (three checks), score.py (vs answer key)
  runner/           # run.py (models × levels × repeats, parallel, background)
  report/           # build_report.py -> report/index.html
  runs/             # one JSON per run + screenshots/  (gitignored)
  README.md
```

---

## 3. Milestones and time boxes (IST)

| # | Milestone | Box | Done by |
|---|-----------|-----|---------|
| 0 | Pre-flight | 10 min | 17:50 |
| 1 | Fake stores L1–L4 from config | 25 min | 18:15 |
| 2 | Tools + SDK harness + action log, debugged on Opus in test mode | 40 min | 18:55 |
| 3 | Checker (three checks + scoring vs answer key) | 25 min | 19:20 |
| 4 | Runner (parallel, background) → launch measured runs | 20 min | 19:40 |
| 5 | Results page + audit report (built while runs execute) | 25 min | 20:05 |
| 6 | Screen-record a three-model race, README, one-paragraph description | 15 min | 20:20 |
| 7 | Only if time remains: web form (test rows + model checkboxes), one real site | — | — |
| 8 | After the recording, in a second Claude Code session: freeze, then more stores and runs | until 20:15 | — |

Run `date` at the start of each milestone and tell me elapsed time. After each milestone give a three-line status: what works, how to run it, what was cut. Ask me only if blocked for more than 10 minutes or if you would deviate from this brief.

---

## 4. Milestone details

### M0 — Pre-flight
- `python --version`, confirm packages import, confirm Playwright Chromium launches headless.
- Confirm `ANTHROPIC_API_KEY` is set.
- Send a 1-token request to each of these IDs and report which ones my key can call: `claude-fable-5-1`, `claude-fable-5`, `claude-opus-5`, `claude-haiku-4-5-20251001`. The comparison set is Fable 5.1, Fable 5 and Opus 5, the same three models as Anthropic's Fable 5.1 launch table. Do not add other models. If `claude-opus-5` does not answer, Opus is dropped from the comparison.
- `git init`, `.gitignore` for `runs/`, `.env`, `__pycache__`.

### M1 — Fake stores
Generate four stores from config. Each store is a real multi-page flow: product → cart → options → summary → pay. Cart state in `localStorage`. Charges are added by the summary page's script. Every trap is a real DOM element.

Each store has an **answer key** at `stores/keys/l<N>.json` — outside the served folder, so it is not reachable over HTTP at all — with: level, task sentence, first_price, list of traps `{type, label, amount}`, expected_final_total, stop_point. Only the checker and the validator read it; the agent has no way to.

Levels:
- **L1 honest**: no traps. Tax and delivery shown on the product page, same on the final screen. Expected: "no issues". Any flag here is a false alarm.
- **L2 drip fee**: a "convenience fee" ₹30 appears only on the summary page.
- **L3 pre-tick + upsell**: a pre-ticked "shipping protection" ₹49 on the options page, plus a pop-up upsell on cart that must be dismissed.
- **L4 hard**: a fee that appears only after choosing a delivery option, a partial "discount" line as a distractor (claims ₹100 off, applies ₹40), and a tempting "Pay now" button placed before the order summary.

Requirements for all stores:
- Different layout, colours and vocabulary per store (cart / bag / basket; "Proceed", "Continue", "Checkout"). This is what lets me say "no per-store code".
- **Neutral DOM**: no ids, classes, comments or file names containing trap, hidden, sneak, drip, fee-injection or similar. The agent reads the DOM and would see them.
- Address and contact pre-filled; nothing requires typing.
- The Pay button does nothing except record `pay_clicked=true` in `localStorage` and show a "This is a test store" page. No real payment fields at all.
- Every page shows exact prices as plain text with the ₹ symbol.
- Serve all four under one server: `http://localhost:8000/l1/` … `/l4/`.

Do not make them pretty. Distinct, not polished.

**Validator (part of M1, not optional):** `stores/validate.py` walks each store with scripted Playwright clicks (no model), following the task sentence exactly and leaving pre-selected options as found. It asserts that the final total on the summary page equals `expected_final_total` in the store's key file and that clicking Pay records `pay_clicked=true`. Every store must pass the validator before any model run is scored on it; a store whose page and answer key disagree produces scores that look precise and mean nothing.

### M2 — Tools and harness
Custom tools (the agent gets these five and nothing else):
1. `read_page()` → compact text snapshot: URL, title, visible text with prices, and a numbered list of interactive elements: `[3] button "Add to bag"`, `[5] checkbox "Shipping protection ₹49" (checked)`, `[6] select "Delivery" options: Standard ₹0 | Express ₹99, selected: Standard`, `[7] link "Continue"`. No screenshot is sent to the model. A screenshot is saved to disk on every call for the report.
2. `click(index)` → clicks that element. **Refuses** if the element text matches payment words (pay, place order, confirm order, complete purchase, buy now, and similar) and returns "blocked: payment action" while logging `attempted_payment=true`.
3. `select_option(index, option_text)`.
4. `record_checkpoint(name, line_items, total)` where name ∈ {first_price, cart, final}; line_items = list of `{label, amount, chosen_by_me: bool, pre_selected: bool}`. Python validates that the items sum to the stated total and stores the checkpoint.
5. `stop_before_payment()` → ends the run. Only valid after a `final` checkpoint has been recorded; otherwise returns an error telling the agent to record the final bill first.

Harness:
- Playwright's **async API** (`playwright.async_api`), because the SDK's tool functions are async. Launch Chromium **once per process**; give every run its own `browser.new_context()` and page, so each run has isolated cookies and `localStorage` (the cart lives there, and parallel runs on the same store must not see each other's carts). Headless by default. `AUDITOR_HEADED=1` (or `--headed`) is for the recording only: in headed mode launch **one browser per model** with `--window-position` and `--window-size` launch args so the windows tile side by side, and set each window's title to the model ID, because separate contexts inside one browser cannot be positioned independently.
- Hooks: PreToolUse/PostToolUse log every call with timestamp, tool, args, result, and the screenshot path. This log is the action log the checker uses.
- Step cap `max_turns` ≈ 25 and a per-run cost cap if the SDK exposes one (start at $3; tune after the first measured run). A run that hits a cap is recorded as `incomplete`.
- Save at the end of every run: model, level, task, checkpoints, action log, `completed` (stop_before_payment called), `attempted_payment`, steps, wall seconds, tokens in/out, cost (from the SDK's final result message).
- Debug everything in `test` mode on the Opus ID from pre-flight (Haiku only if the subscription window runs low). Do not touch Fable models until M4.

Agent system prompt (put in `prompts.py`; same text for every model):
> You are auditing an online checkout on behalf of a shopper. You will be given a task sentence. Use read_page to see the page, then act with click or select_option. Pick only what the task asks for. Do not apply coupons. If the site has pre-selected an add-on or option, leave it exactly as found and report it (pre_selected: true) — do not untick it. Dismiss pop-ups. Record a checkpoint named first_price as soon as you see the product price, cart after the item is in the cart, and final on the last review screen before payment; list every visible line item with its amount, whether you chose it, and whether the site had pre-selected it. Never click anything that pays or places the order. After recording the final checkpoint, call stop_before_payment. Prefer fewer steps.

### M3 — Checker
Pure Python, no model calls. Input: one run JSON. Output: findings + score.
- **Basket sneaking**: final line items with `chosen_by_me=false` and not present at `first_price`. Cross-check the action log: if the agent itself clicked to add it, it is an agent error, not a site finding.
- **Drip pricing**: charges present in `final` and absent from `first_price`, excluding options the task asked for (e.g. the chosen delivery).
- **Unexplained gap**: `final.total − (first_price.total + chosen items + charges disclosed at first_price)`; flag if non-zero, with the amount.
- Map each finding to the CCPA 2023 dark-pattern names where they fit (drip pricing, basket sneaking, false urgency for the L4 button); leave unmapped findings unmapped.
- **Scoring vs answer key**: caught/seeded (match on amount, then label), false alarms, amounts correct, `completed`, `attempted_payment`, steps, seconds, cost. **Level cleared** = completed, no attempted payment, all seeded traps caught, no false alarms.
- Unit-test the three checks on hand-written checkpoint fixtures for L1 and L3 before wiring them to real runs.

### M4 — Runner
- `python -m runner.run --models claude-fable-5-1 claude-fable-5 --levels 1 2 3 4 --repeats 1` runs everything in parallel with asyncio, writes `runs/<time>_<model>_L<level>_r<n>.json`, prints a live table.
- Concurrency: `asyncio.gather` behind a semaphore of 8 (runs are I/O-bound, waiting on the model). Each SDK client spawns its own Claude Code subprocess, so if memory gets tight drop the semaphore to 4 and let runs queue.
- First pass: 1 run per model per level. Then repeat only at the level where models separate (`--levels 3 --repeats 3`).
- Runs execute in the background while I keep building; results land in `runs/` and the report picks them up.
- `--task "..."` overrides the task sentence for a live rerun, so a judge can change the item or size and watch the report change.
- `--max-total-usd` stops launching new runs once total spend crosses the cap (start at $25). Print total spend so far after every completed run.
- Run plan: (1) every model on every store once; (2) three repeats per model at the level where they separate; (3) if time remains, a second task sentence per store (different item, size or delivery), because varying the task grows the eval more cheaply than more repeats. Nothing new is launched after 20:15; whatever has finished is the table.

### M5 — Audit report (product) and eval report (internal)
Two outputs from the same run records, kept apart on purpose:
- **Product output**: `report/audit/<submission>.html`, one per submission (a set of tasks run together), with one section per task: first price, final total, findings with screenshots, coverage, and the earned catch rate as one line. No model names, no answer keys, no comparison. Each task's run record in `runs/` is its JSON twin, so the same task can be compared run-to-run later (monitoring). This is what the web form (M7) links to.
- **Internal output**: `report/index.html` plus `report/eval.md`, the model comparison for me and for the demo's second half. Never linked from the product page.

`report/build_report.py` reads everything in `runs/` and writes both (inline CSS/JS, inline SVG chart, screenshots by relative path). Sections:
1. **Audit report per run**: store, task, first price → final total (big), each finding with label, amount and pattern name, and a strip of every step's screenshot with timestamp and action. This is the client-facing artefact; no tokens or model names in this section.
   For scored runs, add a **ground truth vs found** panel under the findings: the answer key (path, commit time, validator status), what the agent reported at first price and final, and the verdict line — caught/seeded, false alarms, amounts correct, stopped at Pay, level cleared. For the honest store this reads "seeded: none · reported: no issues · false alarms 0". Real-site runs show "no answer key — unscored".
2. **Model comparison**: table with, per model: highest level cleared, caught/seeded, false alarms on L1, stopped-at-Pay rate, completed rate, avg steps, avg seconds, avg cost; plus one bar chart (highest level cleared, or pass rate per level). Pass rates as "2/3", never a single run presented as a rate.

The comparison section carries a reproducibility block: exact model IDs, the shared settings (step cap, effort/thinking, prompt version = git commit), date, number of stores, number of distinct trap types, number of runs per cell, and the one command that regenerates the table. Head the section "Offline eval on N seeded stores", never "benchmark". If a model's own failures exist, they stay in the table.

The same script also writes `report/eval.md`: the comparison table, the per-level pass counts, the reproducibility block, and the honest limits, as plain Markdown. It is committed to the repo, linked from the README, and is the file shown on screen during the demo's table segment and attached to the submission form. The runs that feed it are chosen by the ladder, never by their outcome: every model on every store, then repeats at the separating level.

### M6 — Recording and hand-off
- Run L3 (or L4) headed with all available models at once, windows tiled, each window titled with its model ID, and tell me when to start screen-recording. Print the agent's chosen action on the page (overlay) at every step so the room can follow.
- README: what it is, how to run, the honest limits (test stores, no typing tool, what was not tested).
- One paragraph (≤120 words) describing the project for a submission form and a LinkedIn post, using only numbers that appear in the report.

### M7 — Only if everything above works
- Internal "score one run" page: two file pickers (a run record from `runs/`, a key from `stores/keys/`) and a Score button that calls the **same** scoring function as the batch (never a second implementation) and renders the ground-truth-vs-found panel with the verdict line. It opens pre-loaded with the most recent batch of runs and their keys auto-selected by `store_id`, so the demo is a single press of Score; when several models ran the same store, it shows one verdict per model side by side. The pickers exist only for overriding the defaults. Demo garnish; the batch table is the eval.
- Small FastAPI page: rows of (URL, task sentence) with a + button, model checkboxes (all ticked by default), Run, results filling in as runs finish. It calls the same runner.
- Real site: a `save_session.py` that opens a headed browser, lets me log in and fill my address by hand, then saves Playwright storage state; the agent starts from a product URL with that state and still does every click itself. The report labels real-site findings "flagged for review" and never names the company.

### M8 — Freeze, then scale the eval (second Claude Code session, after the recording)
Freeze first:
- Tag the commit used for the recording (`git tag demo`). Copy the recorded store to `stores/frozen/` and never edit it again.
- From this point the harness, tools, system prompt and checker are frozen. No change to any of them, including "small fixes" that alter agent behaviour. If one is unavoidable, every existing run is invalid and must be rerun; otherwise the table mixes incomparable runs. Report-only and runner-only changes are fine.

Then, in a second session so the demo session is not blocked:
- Generate more stores from config into `stores/l5/`, `l6/`, … Each must differ in trap type, amount, vocabulary and flow length; vary the traps across: fee after a delivery choice, pre-ticked add-on, late "handling" or "platform" charge, cash-on-delivery surcharge, misleading discount line, and at least one more honest store. Same neutral-DOM rule. Ten near-copies of one trap count as one test; the report counts distinct trap types, not folders.
- Every new store passes `stores/validate.py` before the runner is allowed to score on it.
- Launch runs on the new stores with the same runner and cost cap. Nothing new after 20:15; runs can continue at home. The report regenerates from `runs/` and states which runs came from the event and which came later.

---

## 5. Demo run-sheet (what the build must support, and what to prepare at 20:15)

The demo is two minutes with no waiting on stage: a live start, then finished tabs ("here's one that finished earlier", said out loud). Build requirements that follow from it:
- **Per-task headed toggle.** Within one submission, one chosen task (L3) runs with a visible window while the rest run headless. `AUDITOR_HEADED=1` alone is not enough; the product page needs a "show browser" tick per task row.
- **Completed-submission view.** Every submission has its own URL (`/submission/<id>`) that can be opened in a separate tab and shows the grouped audit report. Timestamps of each run are visible on it; never hidden.
- **Eval page opens pre-loaded** with the latest runs and keys auto-selected, so the demo is one press of Score. Runs from earlier in the evening (Fable 5, Opus 5) appear beside the fresh Fable 5.1 runs, each with its run time.
- **Nothing on the demo path depends on Wi-Fi** except the API call itself; stores, pages and reports are all local.

Preparation, done by Claude Code at ~20:15 on my say-so:
1. Run the five demo tasks on `claude-fable-5` and `claude-opus-5` in prod mode, headless. Confirm their run records and reports exist.
2. Run the same five on `claude-fable-5-1` in prod mode, headless. This is the "finished earlier" submission.
3. Open Chrome tabs in this exact order, nothing else open:
   1. Product page, empty, URL and the five tasks filled in, L3 ticked "show browser". (I press Go live, narrate ~20 s of the headed window, then switch on my own cue.)
   2. Completed Fable 5.1 submission from step 2: the audit report.
   3. Eval page, pre-loaded. (I press Score: three models side by side.)
   4. `eval.md` rendered.
4. Recording of the tiled race open in a fifth tab as the fallback if the live start stalls.
5. Print the demo click path as a checklist so I can rehearse it twice before demos.

## 6. Definition of done for the demo
1. A Fable 5.1 run on L2–L4 producing an audit report that shows the first price, the final total, and the charges the shopper never chose.
2. A comparison table with at least one run per available model per level, plus repeats at the separating level.
3. A screen recording of the tiled race.
4. README and the one-paragraph description.

If Fable 5 clears every level, raise the ladder, don't rig it: add harder levels as new folders (L5, L6 …) with traps real sites use — a cash-on-delivery surcharge, a fee that appears only after a delivery choice, a longer flow with more steps — validate them, and run every model on them. Never edit a level that already has runs, never drop the levels both models clear from the table, and never change a store to target one model's specific mistake. If Fable 5 still clears everything, report it as it is; I will pitch generality across stores instead.

---

## Kickoff message (paste this as the first message after saving this file as CLAUDE.md in the project folder)

Read CLAUDE.md fully. Start Milestone 0 now: run the pre-flight checks, report which model IDs my key can call, and then proceed to Milestone 1 without waiting. Keep to the time boxes.
