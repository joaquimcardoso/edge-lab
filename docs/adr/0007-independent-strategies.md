# ADR-0007 — Independent strategies, no shared score

**Status:** Accepted

## Context
Swing, daily and value strategies have different horizons, data and risks. Combining them into one score hides which component carries any edge and invites overfitting.

## Decision
Each strategy has its own experiments, parameters and acceptance criteria. They share only data, point-in-time rules, the protocol and reporting.

## Consequences
- A stock can be bullish in one strategy and rejected in another; this is not a contradiction.
- Cross-strategy combinations (e.g. event + value agreement) may be tested later as their own experiment.
