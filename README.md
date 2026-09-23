# Checkout Auditor

A browser agent that walks an online checkout for a given shopping task, records the visible bill at three checkpoints (first price, cart, final), stops before payment, and hands the checkpoints to plain Python that finds basket sneaking, drip pricing, misleading discounts, price changes between first price and final, discounts that vanish between cart and final, and any unexplained gap left over. Same harness for every Claude model, swapped by full model ID, so models can be compared fairly. There are 40 seeded stores in the repo, all generated from config and all validated before anything is scored on them.

## How it works

The agent gets five tools and nothing else:

- `read_page()` returns the URL, title, visible text with prices, and a numbered list of interactive elements. No screenshot goes to the model; one is saved to disk per call for the report.
- `click(index)` clicks a numbered element. It refuses anything whose text matches payment words (pay, place order, buy now and so on), returns `blocked: payment action` and logs `attempted_payment=true`.
- `select_option(index, option_text)` picks an option in a select.
- `record_checkpoint(name, line_items, total)` with name in `first_price`, `cart`, `final`. Python checks that the line items add up to the stated total before storing it.
- `stop_before_payment()` ends the run. Only valid after a `final` checkpoint exists.

There is no typing tool. Every built-in Claude Code tool (Bash, Read, Write, Edit, Glob, Grep, WebFetch, WebSearch, Task and the rest) is blocked with `disallowed_tools`, and `agent/test_surface.py` proves it by reading the tool list the SDK announces at init and failing if anything but the five is there.

The model does perception and decisions. Python does every sum and every comparison. Step cap 25, per-run budget cap $3, one Chromium per process with a fresh browser context per run so carts in `localStorage` never leak between runs.

## Quickstart

```sh
uv venv --python 3.13 .venv && uv pip install --python .venv/bin/python claude-agent-sdk playwright python-dotenv && .venv/bin/playwright install chromium

# generate the stores (gen.py writes l1-l8, gen2.py .. gen9.py four each)
for g in stores/gen*.py; do .venv/bin/python "$g"; done

# validate every store (scripted Playwright walk, no model) -> stores/keys/validation.json
.venv/bin/python stores/validate.py

# serve them (the runner also starts one if none is running)
python -m http.server 8000 --directory stores/www

# one debug run in test mode
AUDITOR_MODE=test .venv/bin/python -m agent.harness --level 3

# measured runs, needs .env with ANTHROPIC_API_KEY
AUDITOR_MODE=prod .venv/bin/python -m runner.run --models claude-fable-5-1 claude-fable-5 claude-opus-5 --levels 1 2 3 4 --repeats 1

# the same stores with another task wording (see Task wordings below)
AUDITOR_MODE=prod .venv/bin/python -m runner.run --models claude-fable-5-1 claude-opus-5 --levels 3 6 13 --task-set conflict --repeats 2

# report -> report/index.html, report/eval.md, report/audit/<submission>.html
.venv/bin/python -m report.build_report

# checker tests
.venv/bin/python -m pytest checker/tests -q
```

Two run modes, picked by `AUDITOR_MODE`:

- `test` (default): no API key reaches the SDK, so runs use the Claude Code login. Default model is `claude-opus-5`. Every run is stamped `mode: test` and the report leaves it out of the comparison.
- `prod`: the runner reads `ANTHROPIC_API_KEY` from `.env` in the repo root, fails fast if it is missing, stamps runs `mode: prod`, and prints a reminder to check Console usage after the first run.
- Never export the key in the shell. It lives only in `.env`, read only by the runner, only in prod. The runner refuses a multi-model comparison in test mode unless `--force` is given.

## The seeded stores

40 static stores, each a real product -> cart -> options -> summary -> pay flow with its own layout, colours and vocabulary (cart, bag, basket). Prices are plain text in rupees. The DOM is neutral: no ids, classes or comments that name a trap, so nothing in the markup tells the agent where to look.

Every store is generated from config by `stores/gen.py` (l1-l8) and `stores/gen2.py` .. `stores/gen9.py` (four stores each), and every store passes `stores/validate.py` before any model run is scored on it. The validator walks the flow with scripted Playwright clicks and no model, follows the task sentence exactly, leaves pre-selected options as found, then asserts that the final total matches `expected_final_total` in the store's key and that Pay records `pay_clicked=true`. Its verdict per store lands in `stores/keys/validation.json`. A store whose pages and key disagree would produce scores that look precise and mean nothing, so it never gets run.

The traps come in families, not one-offs: drip fees that only show up on the summary, pre-ticked add-ons, paid options pre-selected in a select or a radio group, delivery silently switched to a paid one, prices that change between screens, discounts that vanish between cart and final, price breakdowns collapsed behind a "view details" toggle, cash-on-delivery surcharges, misleading discount lines that take off less than they claim, subscription trials, quantity and unit-price confusion, and honest stores with no traps at all, where any flag is a false alarm. Ten near-copies of one trap count as one test, so the eval counts distinct trap types, not folders.

Answer keys live in `stores/keys/*.json`, outside the served folder, so the agent cannot reach them over HTTP. Each one has the exact type, label and amount of every seeded trap, the task sentence, the first price and the expected final total. Only the checker and the validator read them.

## Task wordings

The same store is run with more than one sentence, picked with `--task-set`:

| Set | Where it comes from | What it is |
|---|---|---|
| `key` | the store's own answer key | the store's own sentence |
| `alt` | `runner/alt_tasks.json` | the same choices, reworded |
| `hard` | `runner/tasks_hard.json` | indirect wording: "cheapest delivery you have", "the fastest delivery you offer", "I will pay at the door" |
| `conflict` | `runner/tasks_conflict.json` | the shopper asks for something that pulls against an audit rule: "remove any add-ons the site put in", "apply the discount code if there is one" |
| `strict` | `runner/tasks_strict.json` | a stated intent that clashes with a pre-selected paid option: "no add-ons", "nothing extra", "the cheapest delivery there is" |

This matters because the audit rule is to leave whatever the site pre-selected exactly as found and report it, not to fix it. So a sentence that invites the agent to tidy the cart is where models split: untick the pre-selected add-on and the charge is gone from the final bill, the seeded trap is never caught, and the shopper never learns the site put it there.

## Eval

See [report/eval.md](report/eval.md). It is an offline eval on seeded stores, not a benchmark. The run ladder is every model on every store once, then repeats at the level where models separate. Runs go into the table by the ladder, never by their outcome, and the reproducibility block lists the exact model IDs, shared settings, prompt hash and the one command that regenerates it.

## Honest limits

- Seeded test stores served locally, not live shops. Results say how the agent behaves on these traps, not on the open web.
- No typing tool, so any flow that needs a login or an address typed in is out of scope. Addresses are pre-filled.
- A single run per cell is one observation, not a rate. Repeats show as k/n and only mean something where n > 1.
- Findings depend on what the model reports at each checkpoint. Python does the sums, the model does the reading.
- Test-mode runs are excluded from the comparison.
- Not tested: real sites, coupons, multi-item carts, mobile layouts.

## Layout

```
checkout-auditor/
  agent/     tools.py (five Playwright tools), harness.py (SDK loop + run record), prompts.py (shared system prompt), test_surface.py
  checker/   checks.py (basket sneaking, drip pricing, misleading discount, price change, vanished discount, unexplained gap), score.py (score vs answer key), tests/
  runner/    run.py (models x levels x repeats, parallel, spend cap)
  report/    build_report.py -> index.html, eval.md, audit/<submission>.html
  stores/    gen.py, validate.py, www/ (served l1..l4), keys/ (answer keys, not served)
  runs/      one JSON per run + screenshots/ (gitignored)
  web/       app.py (JSON API + reference pages), ui/ (the two pages people actually use)
```

## The UI

Two static pages in `web/ui/`, no build step and no framework, mounted by `web.app` at `/ui`:

| Page | URL | What it does |
|---|---|---|
| Audit | `/ui/` | One store URL with any number of task sentences under it, `+ Add another store` for more, plus model tick-boxes. The URL is asked for once per store and multiplied across its tasks into the flat `rows` the API wants. **Run audit** POSTs `/api/run`, then polls `/api/submission/{id}` every 3 s and renders one section per task: first price → final total, the charges the shopper never chose with their pattern names, and the verdict line. `show browser` is per task, so one task can run headed while the rest stay headless. **Load seeded stores** fills it from `/api/stores`. |
| Eval | `/ui/eval.html` | Pre-loads the runs from the last audit started on the Audit page, pairs each with its store's answer key, and scores them via `/api/score` — so the demo is one press of **Score**, or none at all. Each panel shows seeded vs found and `expected − reported` for the first price and the final total. Below it, the model comparison table from `/api/eval`. |

The pages are plain HTML/CSS/JS on purpose: nothing on the demo path needs a bundler or the network. They call the API on their own origin by default; `?api=http://host:port` points them at a backend somewhere else and is remembered.

### Developing the UI without the backend

`python web/ui/mock_api.py` serves the same endpoints and the pages on the same port, with runs synthesised from the real answer keys. It needs nothing but the standard library — no SDK, no Playwright, no API key — so the front end can be worked on while runs are happening elsewhere. Every page shows a banner when it is talking to the mock. It is a development aid only; `web/app.py` never imports it.

## Backend API (for the UI)

`AUDITOR_MODE=prod .venv/bin/python -m web.app` serves a JSON API on http://127.0.0.1:8080 with CORS open. The HTML pages in `web/app.py` are a reference only; the real UI is `web/ui/` (see above) and calls these:

| Endpoint | What it returns |
|---|---|
| `GET /api/health` | mode, model list, server time |
| `GET /api/stores` | seeded stores (id, level, name, url, task, validator status), no traps |
| `GET /api/keys/{store_id}` | the full answer key (internal eval page only) |
| `POST /api/run` `{rows:[{url,task,headed}], models:[...]}` | `{submission_id}`; one run per row x model, scheduled in the background |
| `GET /api/submission/{id}` | rows, jobs (queued/running/done) with a run summary once finished; poll every 3 s |
| `GET /api/submissions` | every submission seen in `runs/` plus in-memory ones |
| `GET /api/runs?submission=&mode=&model=&store_id=` | run summaries: totals, findings, verdict line |
| `GET /api/runs/{run_id}` | full run record, checks, score, key, screenshot URLs |
| `POST /api/score` `{pairs:[{run_file,key_file}]}` | scores with the same `score_run` the batch uses |
| `GET /api/eval` | the model comparison table (prod runs only) plus reproducibility block |
| `POST /api/report/rebuild` | regenerates `report/index.html`, `report/eval.md`, `report/audit/*.html` |
| `/runs/...`, `/report/...` | static screenshots and built reports |

Run records are one JSON per run in `runs/`; the same file feeds the audit page, the eval table and the API.
