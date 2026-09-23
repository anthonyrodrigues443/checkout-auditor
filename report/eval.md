# Offline eval on 20 seeded stores

Generated 2026-09-23T19:00:18 from 116 runs (debug test-mode runs excluded; credential modes in the reproducibility block: prod = API key, cli = Claude Code login).

| model | runs | highest level cleared | caught/seeded | false alarms on L1 | stopped at Pay | completed | avg steps | avg seconds | avg cost $ |
|---|---|---|---|---|---|---|---|---|---|
| claude-fable-5 | 11 | 8 | 11/14 | 0 (n=1) | 11/11 | 11/11 | 12.7 | 32.8 | 0.183 |
| claude-fable-5-1 | 4 | 4 | 4/4 | 0 (n=1) | 4/4 | 4/4 | 11.8 | 35.5 | 0.176 |
| claude-haiku-4-5-20251001 | 3 | 3 | 2/2 | 0 (n=1) | 3/3 | 3/3 | 12.3 | 39.8 | 0.045 |
| claude-opus-5 | 98 | 20 | 142/146 | 0 (n=5) | 98/98 | 98/98 | 13.6 | 34.0 | 0.098 |

## Level cleared per level (cleared/runs)

| model | L1 | L2 | L3 | L4 | L5 | L6 | L7 | L8 | L9 | L10 | L11 | L12 | L13 | L14 | L15 | L16 | L17 | L18 | L19 | L20 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-fable-5 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/3 | 0/0 | 0/0 | 0/0 |
| claude-fable-5-1 | 1/1 | 1/1 | 1/1 | 1/1 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| claude-haiku-4-5-20251001 | 1/1 | 1/1 | 1/1 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| claude-opus-5 | 5/5 | 5/5 | 5/5 | 6/6 | 5/5 | 6/6 | 5/5 | 6/6 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 2/6 | 3/3 | 3/3 | 3/3 |

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
 "max_turns": 25,
 "max_budget_usd": 3.0,
 "effort": null,
 "thinking": null,
 "prompt_version": "d4ea0d273cca",
 "prompt_commit": "821c3e2",
 "sdk": "0.2.158",
 "date": "2026-09-23",
 "stores": 20,
 "trap_types": 12,
 "trap_type_names": [
  "cod_surcharge",
  "collapsed_fee",
  "delivery_switched",
  "delivery_triggered_fee",
  "drip_fee",
  "misleading_discount",
  "pre_ticked_addon",
  "preselected_zone_fee",
  "price_change",
  "subscription_trap",
  "undisclosed_tax",
  "vanished_discount"
 ],
 "runs_per_cell": [
  1,
  3,
  5,
  6
 ],
 "command": "AUDITOR_MODE=test .venv/bin/python -m runner.run --eval --force --models claude-fable-5 claude-fable-5-1 claude-haiku-4-5-20251001 claude-opus-5 --levels 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 --repeats 1 && .venv/bin/python -m report.build_report"
}
```

## Honest limits

- Stores are seeded test stores served locally, not live shops; results say how the agent behaves on these traps, not on the open web.
- The agent has no typing tool, so flows that need an address or login typed in are out of scope.
- A single run per cell is one observation, not a rate; repeats are shown as k/n and are only meaningful where n > 1.
- Findings depend on what the model reports at each checkpoint; Python does the sums, the model does the reading.
- Debug runs (mode test) are excluded from the comparison; runs stamped cli went through the Claude Code login rather than the API key and are labelled in the reproducibility block.
