# Offline eval on 16 seeded stores

Generated 2026-09-23T18:52:15 from 82 runs (debug test-mode runs excluded; credential modes in the reproducibility block: prod = API key, cli = Claude Code login).

| model | runs | highest level cleared | caught/seeded | false alarms on L1 | stopped at Pay | completed | avg steps | avg seconds | avg cost $ |
|---|---|---|---|---|---|---|---|---|---|
| claude-fable-5 | 8 | 8 | 11/11 | 0 (n=1) | 8/8 | 8/8 | 12.6 | 32.8 | 0.176 |
| claude-fable-5-1 | 4 | 4 | 4/4 | 0 (n=1) | 4/4 | 4/4 | 11.8 | 35.5 | 0.176 |
| claude-haiku-4-5-20251001 | 3 | 3 | 2/2 | 0 (n=1) | 3/3 | 3/3 | 12.3 | 39.8 | 0.045 |
| claude-opus-5 | 67 | 16 | 105/105 | 0 (n=5) | 67/67 | 67/67 | 13.9 | 34.1 | 0.097 |

## Level cleared per level (cleared/runs)

| model | L1 | L2 | L3 | L4 | L5 | L6 | L7 | L8 | L9 | L10 | L11 | L12 | L13 | L14 | L15 | L16 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-fable-5 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| claude-fable-5-1 | 1/1 | 1/1 | 1/1 | 1/1 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| claude-haiku-4-5-20251001 | 1/1 | 1/1 | 1/1 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| claude-opus-5 | 5/5 | 5/5 | 5/5 | 6/6 | 5/5 | 6/6 | 5/5 | 6/6 | 4/4 | 4/4 | 4/4 | 4/4 | 2/2 | 2/2 | 2/2 | 2/2 |

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
 "stores": 16,
 "trap_types": 10,
 "trap_type_names": [
  "cod_surcharge",
  "collapsed_fee",
  "delivery_switched",
  "delivery_triggered_fee",
  "drip_fee",
  "misleading_discount",
  "pre_ticked_addon",
  "price_change",
  "subscription_trap",
  "vanished_discount"
 ],
 "runs_per_cell": [
  1,
  2,
  4,
  5,
  6
 ],
 "command": "AUDITOR_MODE=test .venv/bin/python -m runner.run --eval --force --models claude-fable-5 claude-fable-5-1 claude-haiku-4-5-20251001 claude-opus-5 --levels 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 --repeats 1 && .venv/bin/python -m report.build_report"
}
```

## Honest limits

- Stores are seeded test stores served locally, not live shops; results say how the agent behaves on these traps, not on the open web.
- The agent has no typing tool, so flows that need an address or login typed in are out of scope.
- A single run per cell is one observation, not a rate; repeats are shown as k/n and are only meaningful where n > 1.
- Findings depend on what the model reports at each checkpoint; Python does the sums, the model does the reading.
- Debug runs (mode test) are excluded from the comparison; runs stamped cli went through the Claude Code login rather than the API key and are labelled in the reproducibility block.
