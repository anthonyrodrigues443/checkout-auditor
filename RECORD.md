# The tiled race (M6)

One command. Three windows, one per model, tiled side by side, each titled with its model ID,
with the agent's chosen action printed on the page at every step.

```bash
cd ~/Desktop/checkout-auditor && AUDITOR_MODE=test .venv/bin/python -m runner.run \
  --models claude-fable-5-1 claude-fable-5 claude-opus-5 \
  --levels 17 --task-set hard --repeats 1 \
  --headed --screen-width 1512 --screen-height 820 \
  --eval --force --submission tiled-race
```

Store L17 "Tamba Home" with the hard wording, "A copper water bottle, the 1 litre one, cheapest delivery."
The site pre-selected a "Outside Mumbai ₹80" delivery zone though the saved address is Mumbai.
Fable 5.1 leaves it as found and reports the ₹80. Fable 5 and Opus 5 switch it to the free zone,
which loses the finding. Takes about 40 seconds.

Watch for: each window's step overlay at the bottom, the zone select on the options page,
and the final totals (₹930 for 5.1, ₹850 for the other two).

Alternative, one visible window and the rest headless:

```bash
cd ~/Desktop/checkout-auditor && AUDITOR_HEADED_FIRST=1 AUDITOR_MODE=test .venv/bin/python -m runner.run \
  --models claude-fable-5-1 --levels 17 --task-set hard --eval
```
