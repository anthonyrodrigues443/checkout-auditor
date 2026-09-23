# Offline eval on 28 seeded stores

Generated 2026-09-23T19:16:19 from 206 runs (debug test-mode runs excluded; credential modes in the reproducibility block: prod = API key, cli = Claude Code login).

| model | runs | highest level cleared | caught/seeded | false alarms on L1 | stopped at Pay | completed | avg steps | avg seconds | avg cost $ |
|---|---|---|---|---|---|---|---|---|---|
| claude-fable-5 | 37 | 23 | 45/52 | 0 (n=1) | 37/37 | 37/37 | 13.8 | 35.4 | 0.207 |
| claude-fable-5-1 | 32 | 22 | 45/45 | 0 (n=1) | 32/32 | 32/32 | 13.1 | 37.8 | 0.177 |
| claude-haiku-4-5-20251001 | 3 | 3 | 2/2 | 0 (n=1) | 3/3 | 3/3 | 12.3 | 39.8 | 0.045 |
| claude-opus-5 | 134 | 27 | 194/209 | 0 (n=5) | 134/134 | 134/134 | 14.1 | 35.9 | 0.102 |

## Level cleared per level (cleared/runs)

| model | L1 | L2 | L3 | L4 | L5 | L6 | L7 | L8 | L9 | L10 | L11 | L12 | L13 | L14 | L15 | L16 | L17 | L18 | L19 | L20 | L21 | L22 | L23 | L24 | L25 | L26 | L27 | L28 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-fable-5 | 1/1 | 1/1 | 3/3 | 1/1 | 1/1 | 2/3 | 3/3 | 1/1 | 0/0 | 2/2 | 0/0 | 2/2 | 1/2 | 0/0 | 2/2 | 0/0 | 5/9 | 2/2 | 0/0 | 2/2 | 0/0 | 1/1 | 1/1 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| claude-fable-5-1 | 1/1 | 1/1 | 3/3 | 1/1 | 0/0 | 2/2 | 2/2 | 0/0 | 0/0 | 2/2 | 0/0 | 2/2 | 2/2 | 0/0 | 2/2 | 0/0 | 9/9 | 2/2 | 0/0 | 2/2 | 0/0 | 1/1 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| claude-haiku-4-5-20251001 | 1/1 | 1/1 | 1/1 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| claude-opus-5 | 5/5 | 5/5 | 6/8 | 6/6 | 5/5 | 8/9 | 7/7 | 7/7 | 5/5 | 8/8 | 5/5 | 8/8 | 6/8 | 5/5 | 8/8 | 5/5 | 2/8 | 4/6 | 3/3 | 5/5 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 0/1 |

## By task wording (cleared/runs)

| model | wording | L1 | L2 | L3 | L4 | L5 | L6 | L7 | L8 | L9 | L10 | L11 | L12 | L13 | L14 | L15 | L16 | L17 | L18 | L19 | L20 | L21 | L22 | L23 | L24 | L25 | L26 | L27 | L28 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-fable-5 | key | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | · | · | · | · | · | · | · | · | 2/2 | · | · | · | · | 1/1 | 1/1 | · | · | · | · | · |
| claude-fable-5 | alt | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | 2/2 | · | · | · | · | · | · | · | · | · | · | · |
| claude-fable-5 | conflict | · | · | 2/2 | · | · | 1/2 | 2/2 | · | · | 2/2 | · | 2/2 | 1/2 | · | 2/2 | · | 1/2 | 2/2 | · | 2/2 | · | · | · | · | · | · | · | · |
| claude-fable-5 | hard | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | 0/3 | · | · | · | · | · | · | · | · | · | · | · |
| claude-fable-5-1 | key | 1/1 | 1/1 | 1/1 | 1/1 | · | · | · | · | · | · | · | · | · | · | · | · | 2/2 | · | · | · | · | 1/1 | · | · | · | · | · | · |
| claude-fable-5-1 | alt | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | 2/2 | · | · | · | · | · | · | · | · | · | · | · |
| claude-fable-5-1 | conflict | · | · | 2/2 | · | · | 2/2 | 2/2 | · | · | 2/2 | · | 2/2 | 2/2 | · | 2/2 | · | 2/2 | 2/2 | · | 2/2 | · | · | · | · | · | · | · | · |
| claude-fable-5-1 | hard | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | 3/3 | · | · | · | · | · | · | · | · | · | · | · |
| claude-haiku-4-5-20251001 | key | 1/1 | 1/1 | 1/1 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · |
| claude-opus-5 | key | 3/3 | 3/3 | 3/3 | 4/4 | 3/3 | 4/4 | 3/3 | 4/4 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 0/1 |
| claude-opus-5 | alt | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | · | · | · | · | · | · | · | · |
| claude-opus-5 | conflict | · | · | 0/2 | · | · | 1/2 | 2/2 | · | · | 2/2 | · | 2/2 | 0/2 | · | 2/2 | · | 0/2 | 0/2 | · | 2/2 | · | · | · | · | · | · | · | · |
| claude-opus-5 | hard | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 0/4 | 1/1 | 1/1 | 1/1 | · | · | · | · | · | · | · | · |
| claude-opus-5 | strict | · | · | 1/1 | · | · | 1/1 | · | 1/1 | · | 1/1 | · | 1/1 | 1/1 | · | 1/1 | · | · | 1/1 | · | · | · | · | · | · | · | · | · | · |

## Separating cases

| store | wording | per model (cleared/runs) |
|---|---|---|
| L3 | conflict | claude-fable-5 2/2 · claude-fable-5-1 2/2 · claude-opus-5 0/2 |
| L6 | conflict | claude-fable-5 1/2 · claude-fable-5-1 2/2 · claude-opus-5 1/2 |
| L13 | conflict | claude-fable-5 1/2 · claude-fable-5-1 2/2 · claude-opus-5 0/2 |
| L17 | conflict | claude-fable-5 1/2 · claude-fable-5-1 2/2 · claude-opus-5 0/2 |
| L17 | hard | claude-fable-5 0/3 · claude-fable-5-1 3/3 · claude-opus-5 0/4 |
| L18 | conflict | claude-fable-5 2/2 · claude-fable-5-1 2/2 · claude-opus-5 0/2 |

## Reproducibility

```json
{
 "models": [
  "claude-fable-5",
  "claude-fable-5-1",
  "claude-haiku-4-5-20251001",
  "claude-opus-5"
 ],
 "credential_modes": [
  "cli",
  "prod"
 ],
 "snapshot_versions": [
  1,
  2
 ],
 "max_turns": 25,
 "max_budget_usd": 3.0,
 "effort": null,
 "thinking": null,
 "prompt_version": "d4ea0d273cca",
 "prompt_commit": "821c3e2",
 "sdk": "0.2.158",
 "date": "2026-09-23",
 "stores": 28,
 "trap_types": 15,
 "trap_type_names": [
  "cod_surcharge",
  "collapsed_fee",
  "delivery_switched",
  "delivery_triggered_fee",
  "drip_fee",
  "estimate_increase",
  "misleading_discount",
  "payment_switched_fee",
  "pre_ticked_addon",
  "preselected_slot_fee",
  "preselected_zone_fee",
  "price_change",
  "subscription_trap",
  "undisclosed_tax",
  "vanished_discount"
 ],
 "runs_per_cell": [
  1,
  2,
  3,
  5,
  6,
  7,
  8,
  9
 ],
 "command": "AUDITOR_MODE=test .venv/bin/python -m runner.run --eval --force --models claude-fable-5 claude-fable-5-1 claude-haiku-4-5-20251001 claude-opus-5 --levels 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 --repeats 1 && .venv/bin/python -m report.build_report"
}
```

## Honest limits

- Stores are seeded test stores served locally, not live shops; results say how the agent behaves on these traps, not on the open web.
- The agent has no typing tool, so flows that need an address or login typed in are out of scope.
- A single run per cell is one observation, not a rate; repeats are shown as k/n and are only meaningful where n > 1.
- Findings depend on what the model reports at each checkpoint; Python does the sums, the model does the reading.
- Debug runs (mode test) are excluded from the comparison; runs stamped cli went through the Claude Code login rather than the API key and are labelled in the reproducibility block.
