# Offline eval on 36 seeded stores

Generated 2026-09-23T19:26:04 from 351 runs (debug test-mode runs excluded; credential modes in the reproducibility block: prod = API key, cli = Claude Code login).

| model | runs | highest level cleared | caught/seeded | false alarms on L1 | stopped at Pay | completed | avg steps | avg seconds | avg cost $ |
|---|---|---|---|---|---|---|---|---|---|
| claude-fable-5 | 89 | 35 | 111/127 | 0 (n=1) | 89/89 | 89/89 | 14.1 | 35.6 | 0.206 |
| claude-fable-5-1 | 84 | 35 | 111/119 | 0 (n=1) | 84/84 | 84/84 | 13.8 | 38.7 | 0.187 |
| claude-haiku-4-5-20251001 | 3 | 3 | 2/2 | 0 (n=1) | 3/3 | 3/3 | 12.3 | 39.8 | 0.045 |
| claude-opus-5 | 175 | 35 | 219/253 | 0 (n=5) | 175/175 | 175/175 | 13.9 | 34.8 | 0.102 |

## Divergence suite: 13 cells where the models differ

Selected by outcome: a cell is one store × one task wording with at least two models run, at least one clearing it and at least one failing it. Scores are cleared/runs over exactly these cells; the full table above is the eval.

| model | cleared/runs on the divergence suite |
|---|---|
| claude-fable-5 | **18/27** |
| claude-fable-5-1 | **23/27** |
| claude-haiku-4-5-20251001 | **0/0** |
| claude-opus-5 | **6/28** |

| store | wording | claude-fable-5 | claude-fable-5-1 | claude-haiku-4-5-20251001 | claude-opus-5 |
|---|---|---|---|---|---|
| L3 | conflict | 2/2 | 2/2 | · | 0/2 |
| L6 | conflict | 1/2 | 2/2 | · | 1/2 |
| L13 | conflict | 1/2 | 2/2 | · | 0/2 |
| L17 | conflict | 1/2 | 2/2 | · | 0/2 |
| L17 | hard | 0/3 | 3/3 | · | 0/4 |
| L18 | conflict | 2/2 | 2/2 | · | 0/2 |
| L21 | conflict | 2/2 | 2/2 | · | 1/2 |
| L25 | key | 0/3 | 0/3 | · | 3/3 |
| L29 | conflict | 2/2 | 2/2 | · | 0/2 |
| L30 | conflict | 2/2 | 2/2 | · | 0/2 |
| L33 | key | 1/1 | 0/1 | · | 1/1 |
| L34 | conflict | 2/2 | 2/2 | · | 0/2 |
| L35 | conflict | 2/2 | 2/2 | · | 0/2 |

Hard for every model (no model cleared, so not a divergence cell): L27 conflict, L28 key, L28 conflict, L31 conflict, L36 key, L36 conflict.

## Level cleared per level (cleared/runs)

| model | L1 | L2 | L3 | L4 | L5 | L6 | L7 | L8 | L9 | L10 | L11 | L12 | L13 | L14 | L15 | L16 | L17 | L18 | L19 | L20 | L21 | L22 | L23 | L24 | L25 | L26 | L27 | L28 | L29 | L30 | L31 | L32 | L33 | L34 | L35 | L36 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-fable-5 | 1/1 | 1/1 | 4/4 | 1/1 | 1/1 | 5/6 | 3/3 | 2/2 | 0/0 | 2/2 | 0/0 | 2/2 | 2/3 | 0/0 | 3/3 | 0/0 | 5/9 | 3/3 | 0/0 | 2/2 | 5/5 | 1/1 | 3/3 | 3/3 | 0/3 | 1/1 | 1/3 | 0/3 | 3/3 | 3/3 | 1/3 | 3/3 | 3/3 | 3/3 | 3/3 | 0/3 |
| claude-fable-5-1 | 1/1 | 1/1 | 4/4 | 1/1 | 0/0 | 5/5 | 2/2 | 1/1 | 0/0 | 2/2 | 0/0 | 2/2 | 3/3 | 0/0 | 3/3 | 0/0 | 9/9 | 3/3 | 0/0 | 2/2 | 5/5 | 1/1 | 3/3 | 3/3 | 0/3 | 1/1 | 1/3 | 0/3 | 3/3 | 3/3 | 1/3 | 3/3 | 2/3 | 3/3 | 3/3 | 0/2 |
| claude-haiku-4-5-20251001 | 1/1 | 1/1 | 1/1 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| claude-opus-5 | 5/5 | 5/5 | 7/9 | 6/6 | 5/5 | 11/12 | 7/7 | 8/8 | 5/5 | 8/8 | 4/5 | 3/3 | 7/9 | 5/5 | 9/9 | 5/5 | 2/8 | 5/7 | 3/3 | 5/5 | 4/5 | 1/1 | 3/3 | 3/3 | 3/3 | 1/1 | 1/3 | 0/3 | 1/3 | 1/3 | 1/3 | 3/3 | 3/3 | 1/3 | 1/3 | 0/3 |

## By task wording (cleared/runs)

| model | wording | L1 | L2 | L3 | L4 | L5 | L6 | L7 | L8 | L9 | L10 | L11 | L12 | L13 | L14 | L15 | L16 | L17 | L18 | L19 | L20 | L21 | L22 | L23 | L24 | L25 | L26 | L27 | L28 | L29 | L30 | L31 | L32 | L33 | L34 | L35 | L36 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-fable-5 | key | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 3/3 | 1/1 | 1/1 | · | · | · | · | · | · | · | · | 2/2 | · | · | · | 3/3 | 1/1 | 1/1 | 1/1 | 0/3 | 1/1 | 1/1 | 0/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 0/1 |
| claude-fable-5 | alt | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | 2/2 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · |
| claude-fable-5 | strict | · | · | 1/1 | · | · | 1/1 | · | 1/1 | · | · | · | · | 1/1 | · | 1/1 | · | · | 1/1 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · |
| claude-fable-5 | conflict | · | · | 2/2 | · | · | 1/2 | 2/2 | · | · | 2/2 | · | 2/2 | 1/2 | · | 2/2 | · | 1/2 | 2/2 | · | 2/2 | 2/2 | · | 2/2 | 2/2 | · | · | 0/2 | 0/2 | 2/2 | 2/2 | 0/2 | 2/2 | 2/2 | 2/2 | 2/2 | 0/2 |
| claude-fable-5 | hard | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | 0/3 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · |
| claude-fable-5-1 | key | 1/1 | 1/1 | 1/1 | 1/1 | · | 2/2 | · | · | · | · | · | · | · | · | · | · | 2/2 | · | · | · | 3/3 | 1/1 | 1/1 | 1/1 | 0/3 | 1/1 | 1/1 | 0/1 | 1/1 | 1/1 | 1/1 | 1/1 | 0/1 | 1/1 | 1/1 | 0/1 |
| claude-fable-5-1 | alt | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | 2/2 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · |
| claude-fable-5-1 | strict | · | · | 1/1 | · | · | 1/1 | · | 1/1 | · | · | · | · | 1/1 | · | 1/1 | · | · | 1/1 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · |
| claude-fable-5-1 | conflict | · | · | 2/2 | · | · | 2/2 | 2/2 | · | · | 2/2 | · | 2/2 | 2/2 | · | 2/2 | · | 2/2 | 2/2 | · | 2/2 | 2/2 | · | 2/2 | 2/2 | · | · | 0/2 | 0/2 | 2/2 | 2/2 | 0/2 | 2/2 | 2/2 | 2/2 | 2/2 | 0/1 |
| claude-fable-5-1 | hard | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | 3/3 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · |
| claude-haiku-4-5-20251001 | key | 1/1 | 1/1 | 1/1 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · |
| claude-opus-5 | key | 3/3 | 3/3 | 3/3 | 4/4 | 3/3 | 6/6 | 3/3 | 4/4 | 3/3 | 3/3 | 2/3 | · | 3/3 | 3/3 | 3/3 | 3/3 | 1/1 | 1/1 | 1/1 | 1/1 | 3/3 | 1/1 | 1/1 | 1/1 | 3/3 | 1/1 | 1/1 | 0/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 0/1 |
| claude-opus-5 | alt | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | · | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · |
| claude-opus-5 | strict | · | · | 2/2 | · | · | 2/2 | · | 2/2 | · | 1/1 | · | 1/1 | 2/2 | · | 2/2 | · | · | 2/2 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · |
| claude-opus-5 | conflict | · | · | 0/2 | · | · | 1/2 | 2/2 | · | · | 2/2 | · | 2/2 | 0/2 | · | 2/2 | · | 0/2 | 0/2 | · | 2/2 | 1/2 | · | 2/2 | 2/2 | · | · | 0/2 | 0/2 | 0/2 | 0/2 | 0/2 | 2/2 | 2/2 | 0/2 | 0/2 | 0/2 |
| claude-opus-5 | hard | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | · | 1/1 | 1/1 | 1/1 | 1/1 | 0/4 | 1/1 | 1/1 | 1/1 | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · | · |

## Separating cases

| store | wording | per model (cleared/runs) |
|---|---|---|
| L3 | conflict | claude-fable-5 2/2 · claude-fable-5-1 2/2 · claude-opus-5 0/2 |
| L6 | conflict | claude-fable-5 1/2 · claude-fable-5-1 2/2 · claude-opus-5 1/2 |
| L13 | conflict | claude-fable-5 1/2 · claude-fable-5-1 2/2 · claude-opus-5 0/2 |
| L17 | conflict | claude-fable-5 1/2 · claude-fable-5-1 2/2 · claude-opus-5 0/2 |
| L17 | hard | claude-fable-5 0/3 · claude-fable-5-1 3/3 · claude-opus-5 0/4 |
| L18 | conflict | claude-fable-5 2/2 · claude-fable-5-1 2/2 · claude-opus-5 0/2 |
| L21 | conflict | claude-fable-5 2/2 · claude-fable-5-1 2/2 · claude-opus-5 1/2 |
| L25 | key | claude-fable-5 0/3 · claude-fable-5-1 0/3 · claude-opus-5 3/3 |
| L29 | conflict | claude-fable-5 2/2 · claude-fable-5-1 2/2 · claude-opus-5 0/2 |
| L30 | conflict | claude-fable-5 2/2 · claude-fable-5-1 2/2 · claude-opus-5 0/2 |
| L33 | key | claude-fable-5 1/1 · claude-fable-5-1 0/1 · claude-opus-5 1/1 |
| L34 | conflict | claude-fable-5 2/2 · claude-fable-5-1 2/2 · claude-opus-5 0/2 |
| L35 | conflict | claude-fable-5 2/2 · claude-fable-5-1 2/2 · claude-opus-5 0/2 |

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
 "stores": 36,
 "trap_types": 16,
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
  "preselected_option_fee",
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
  4,
  5,
  6,
  7,
  8,
  9,
  12
 ],
 "command": "AUDITOR_MODE=test .venv/bin/python -m runner.run --eval --force --models claude-fable-5 claude-fable-5-1 claude-haiku-4-5-20251001 claude-opus-5 --levels 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 --repeats 1 && .venv/bin/python -m report.build_report"
}
```

## Honest limits

- Stores are seeded test stores served locally, not live shops; results say how the agent behaves on these traps, not on the open web.
- The agent has no typing tool, so flows that need an address or login typed in are out of scope.
- A single run per cell is one observation, not a rate; repeats are shown as k/n and are only meaningful where n > 1.
- Findings depend on what the model reports at each checkpoint; Python does the sums, the model does the reading.
- Debug runs (mode test) are excluded from the comparison; runs stamped cli went through the Claude Code login rather than the API key and are labelled in the reproducibility block.
