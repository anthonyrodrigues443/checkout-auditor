# Checkout Auditor: submission text and demo notes

All figures below come from `report/eval.md` as generated at **2026-09-23T19:26:04** from **351 runs**. Runs were still landing when this was written, so re-read that file before you say any of it out loud.

## One paragraph

Checkout Auditor is a browser agent that walks an online checkout for a one-line shopping task and reports the charges the shopper never chose. Five tools, read page, click, select option, record checkpoint, stop before payment, and no typing tool, so it cannot pay. The model reads pages and picks the next click. Python does every sum: basket sneaking, drip pricing, vanished discounts, unexplained gap. The eval covers 36 seeded stores, 16 trap types and 351 runs across four Claude models. The honest headline: models agree on neutral wordings and split when the shopper's sentence pulls against a site default. On the 13 cells where they differ, Fable 5.1 went 23/27, Fable 5 18/27, Opus 5 6/28.

## LinkedIn version

I built Checkout Auditor, a browser agent that walks a checkout and tells you which charges you never chose. Five tools, no typing tool, so it cannot pay. The model reads the page and picks the next click. Python does every sum, so no number comes from a model. The eval covers 36 seeded stores, 16 trap types and 351 runs across four Claude models. The part I did not expect: models agree on plain wordings and split when the shopper's sentence pulls against a site default. On those 13 cells, Fable 5.1 got 23/27, Opus 5 got 6/28.

## Demo talk track

- Checkout Auditor takes a store URL and one sentence, walks the checkout like a shopper, and reports the charges that were never chosen.
- The agent has five tools, read page, click, select option, record checkpoint and stop before payment, with every built-in tool blocked and no typing tool, so it cannot pay even if it tries.
- Here is a live run on a seeded store: watch it read, click, and record the bill at first price, cart and final.
- The audit report shows first price against final total, each finding with its label, amount and dark-pattern name, and a screenshot of every step.
- The eval ladder is fixed before the runs: every model on every store, then repeats only where the models separate, then a second task wording, so runs go in by the ladder and never by how they turned out.
- The Divergence suite is the 13 cells where at least one model cleared and at least one failed, and I want to be straight about it: those cells were picked after the fact, so no model can score 100% there and it says nothing about the stores everyone gets right.
- What it shows is one real split: the models agree on neutral wordings and come apart when the shopper's sentence pushes against a site default, because the audit rule is to leave a pre-selection as found and report it, not to tidy it away.
- Limits: these are seeded local stores, not live shops, there is no typing tool so anything needing a login or an address is out of scope, one run in a cell is one observation and not a rate, and the eval covers 36 of the 40 stores in the repo.

## Numbers to quote

| Figure | Value | Where it comes from |
|---|---|---|
| Generated at | 2026-09-23T19:26:04 | `report/eval.md`, header line |
| Runs in the table | 351 (test-mode debug runs excluded) | `report/eval.md`, header line |
| Stores in the eval | 36 | `report/eval.md`, Reproducibility block, `"stores"` |
| Distinct trap types | 16 | `report/eval.md`, Reproducibility block, `"trap_types"` |
| Models compared | 4 (fable-5, fable-5-1, haiku-4-5, opus-5) | `report/eval.md`, comparison table |
| Stopped at Pay | every run, every model | `report/eval.md`, comparison table, "stopped at Pay" |
| False alarms on the honest store | 0 for every model | `report/eval.md`, comparison table, "false alarms on L1" |
| Caught/seeded, Fable 5.1 | 111/119 | `report/eval.md`, comparison table |
| Caught/seeded, Fable 5 | 111/127 | `report/eval.md`, comparison table |
| Caught/seeded, Opus 5 | 219/253 | `report/eval.md`, comparison table |
| Avg cost per run | $0.187 Fable 5.1, $0.206 Fable 5, $0.102 Opus 5 | `report/eval.md`, comparison table |
| Divergence cells | 13 | `report/eval.md`, "Divergence suite" heading |
| Divergence suite scores | Fable 5.1 23/27, Fable 5 18/27, Opus 5 6/28, Haiku 0/0 | `report/eval.md`, Divergence suite table |
| Stores in the repo | 40, all passing the validator | `stores/keys/l*.json`, `stores/keys/validation.json` |
| Step cap and per-run budget | 25 turns, $3 | `report/eval.md`, Reproducibility block |
