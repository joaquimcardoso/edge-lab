# Strategy — Swing

## Definition

Long positions held for 5–20 trading days after a material, company-specific event, entered **after** the market's initial reaction.

## Hypothesis family

Post-event drift: after positive new information, prices may continue to adjust over the following days. Academic evidence supports investigating this (post-earnings-announcement drift, post-revision drift), but its size and interpretation are contested. Part of it may be compensation for risk rather than underreaction. Every swing experiment therefore uses risk-adjusted abnormal returns and controls.

## Common rules

| Item | Rule |
|---|---|
| Universe | US common stocks, price ≥ $5, ADV20 ≥ $20M |
| Direction | Long only |
| Entry | Next regular-session open after the signal is fully known |
| Exit (research) | Fixed horizon; primary 10 sessions |
| Exit (live, later) | Separate experiments: trailing stop, partial exits, catalyst decay |
| Overnight / gap risk | Accepted; sized for in the live phase |

## Experiments

- [EXP-001 Analyst drift](../experiments/swing/EXP-001-analyst-drift.md)
- [EXP-003 8-K drift](../experiments/swing/EXP-003-8k-drift.md)
- [EXP-004 News events](../experiments/news/EXP-004-news-events.md) (later)

## Live-phase considerations

- Risk per trade is defined by distance to the invalidation level and a gap scenario, not only the stop distance.
- With ~€1,000 of capital, the number of concurrent positions is small; correlation between positions (same sector, same event day) must be capped.
- Execution is manual, near the US open (typically 14:30 Lisbon) or with limit orders placed in advance.
