# Offline eval on 0 seeded stores

Generated 2026-09-23T18:25:03 from 0 prod runs (test-mode runs excluded).

| model | runs | highest level cleared | caught/seeded | false alarms on L1 | stopped at Pay | completed | avg steps | avg seconds | avg cost $ |
|---|---|---|---|---|---|---|---|---|---|

## Level cleared per level (cleared/runs)

| model |  |
|---|

## Reproducibility

```json
{
 "models": [],
 "max_turns": null,
 "max_budget_usd": null,
 "effort": null,
 "thinking": null,
 "prompt_version": null,
 "prompt_commit": null,
 "sdk": null,
 "date": "2026-09-23",
 "stores": 0,
 "trap_types": 0,
 "trap_type_names": [],
 "runs_per_cell": [],
 "command": "AUDITOR_MODE=prod .venv/bin/python -m runner.run --models  --levels  --repeats 1 && .venv/bin/python -m report.build_report"
}
```

## Honest limits

- Stores are seeded test stores served locally, not live shops; results say how the agent behaves on these traps, not on the open web.
- The agent has no typing tool, so flows that need an address or login typed in are out of scope.
- A single run per cell is one observation, not a rate; repeats are shown as k/n and are only meaningful where n > 1.
- Findings depend on what the model reports at each checkpoint; Python does the sums, the model does the reading.
- Test-mode runs (subscription credentials, used for debugging) are excluded from the comparison.
