# EXP-001 — Analyst drift

| Field | Value |
|---|---|
| Strategy | Swing |
| Status | DRAFT |
| Spec version | 0.1.0 |

Two variants share the hypothesis and differ only in timing data:

- **EXP-001F (free):** yfinance analyst actions, date only. Historical test, conservative timing.
- **EXP-001T (timestamped):** own forward snapshots (`first_seen_at`), or paid timestamped data if purchased. Uses the gap definition.

## Hypothesis

- **H1:** After a positive analyst action (upgrade or price-target raise) confirmed by a strong price and volume reaction, the stock earns a positive beta-adjusted abnormal return over the following 10 sessions.
- **H0:** No positive abnormal return after base costs.

## Event

`analyst_upgrade` or `analyst_target_raise`. Multiple actions on the same security and date are collapsed into one observation (`n_actions` kept).

## Exclusions

- Events within ±2 sessions of an 8-K item 2.02 filing (earnings).
- Securities outside the universe on the event date.
- **Open item:** the rule above only covers earnings near *entry*. It does not yet cover an earnings release, another qualifying event, or a corporate action landing *inside* the 10-session hold itself (e.g. Monday upgrade, Thursday earnings). Until frozen, such observations are flagged with an `event_during_hold` attribute and reported separately, never silently pooled with clean observations. See [06 Trading System Audit](../../06-trading-system-audit-v1.md).

## Filters

**EXP-001F (date-only, reaction window D, D+1):**

- `reaction_return = close(D+1) / close(D−1) − 1` in **[+3%, +10%]**
- `max(volume(D), volume(D+1)) / ADV20(D−1) ≥ 2.0`
- Entry: **open of D+2**

**EXP-001T (timestamped):**

- `session_date` from [01 §3](../../01-point-in-time-rules.md); intraday events excluded
- `gap = open(S) / close(S−1) − 1` in **[+3%, +10%]**
- `volume(S) / ADV20(S−1) ≥ 2.0`
- Entry: **open of S+1**

## Exit

Fixed: close of the 10th session after entry (primary). 5 and 20 sessions are reported as secondary, descriptive only.

## Metrics

- **Primary:** 10-session beta-adjusted abnormal return.
- Secondary: sector-adjusted return; AR / ATR%20; win rate; median; profit factor; calendar-time portfolio drawdown.
- **Diagnostic, not used for acceptance:** for events present in both the EXP-001F and EXP-001T samples, the difference in captured 10-session abnormal return between the D+2 (date-only) entry and the S+1 (timestamped) entry. This turns the known "two-session window forgoes early drift" limitation into a measured number instead of an assumption.

## Controls

1. `NO_IDENTIFIED_ANALYST_EVENT`: same filters on reaction/gap and volume, no analyst action on D±1. Matched on sector, reaction size bucket and month.
2. Analyst actions that **fail** the reaction filter (tests whether the reaction adds information).

## Statistics and sample

- Calendar-time portfolio or date-clustered standard errors.
- Minimum 150 observations; subperiod table by year.

## Acceptance criteria (to freeze)

- Primary metric mean > 0 with 95% CI excluding 0 under clustering
- Positive under the base cost scenario
- Greater than control 1
- Positive in the majority of calendar years, with no single year contributing most of the effect

## Known limitations

- EXP-001F: yfinance history may be revised and covers delisted names poorly (survivorship bias, likely upward).
- The two-session reaction window forgoes early drift.

## Outcome

_Pending._
