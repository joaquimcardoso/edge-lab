# EXP-003 — 8-K drift

| Field | Value |
|---|---|
| Strategy | Swing |
| Status | DRAFT |
| Spec version | 0.1.0 |

The most defensible free experiment: SEC acceptance timestamps are exact and EDGAR includes later-delisted filers.

## Sub-experiments

- **EXP-003a:** 8-K item 2.02 (results of operations)
- **EXP-003b:** 8-K item 1.01 (material definitive agreement)

Tested and reported separately. Never pooled into one score.

## Hypothesis

- **H1:** After an 8-K of the given type followed by a positive, strong price reaction, the stock earns a positive beta-adjusted abnormal return over the following 10 sessions.
- **H0:** No positive abnormal return after base costs.

The filing does not reveal direction. Direction comes from the market reaction.

## Timing

- `known_at = acceptance time + declared_feed_lag`
- `session_date` per [01 §3](../../01-point-in-time-rules.md). Filings accepted 09:30–16:00 ET are excluded in V1.

## Filters

- `gap = open(S) / close(S−1) − 1` in **[+3%, +10%]**
- `volume(S) / ADV20(S−1) ≥ 2.0`
- Universe per [swing strategy](../../strategies/swing.md)
- For 003b: exclude filings within ±2 sessions of an item 2.02 filing

## Entry and exit

Entry at open of S+1. Exit at close of the 10th session after entry (primary). 5/20 secondary.

## Metrics, controls, statistics

As EXP-001, with control group: same gap/volume filters, no 8-K of any type on S−1..S.

## Acceptance criteria (to freeze)

Same structure as EXP-001.

## Known limitations

- Delisted-company prices from free sources may be incomplete; coverage is reported.
- Item 2.02 events are the classic post-earnings-drift setting, where recent literature questions how much drift remains after risk adjustment.

## Outcome

_Pending._
