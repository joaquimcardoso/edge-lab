# EXP-002 — Intraday continuation

| Field | Value |
|---|---|
| Strategy | Daily |
| Status | DRAFT — blocked by Gate 0 |
| Spec version | 0.1.0 |

## Gate 0 — Feed latency (runs first)

For 2–3 weeks of live pre-market sessions, poll each event source every few minutes from 08:00 ET and record `first_seen_at`. Report, per source, the distribution of `first_seen_at − published_at` and the share of pre-market events visible before 09:30 ET.

**Pass bar (proposed, to confirm before freezing):** a source passes Gate 0 only if at least 80% of its pre-market events show `first_seen_at` before 09:30 ET **and** the median `first_seen_at − published_at` lag against that event's primary wire timestamp is 30 seconds or less. A source that misses either bar is not used live. If no source passes for a given event type, EXP-002's backtest result for that event type is informational only, and the pre-market-continuation hypothesis is not pursued live on it — no amount of backtest quality substitutes for being unable to see the event in time.

## Hypothesis

- **H1:** When a stock has a positive event known before the open and opens with a moderate positive gap, its open-to-close beta-adjusted abnormal return is positive on average.
- **H0:** No positive abnormal return after costs.

## Events

- 8-K items 2.02 / 1.01 accepted before 09:30 ET minus declared feed lag
- Analyst actions with `first_seen_at` before 09:30 ET (forward snapshots only)

## Filter

- `gap_pct = open(t) / close(t−1) − 1`
- `ATRpct20 = ATR20(t−1) / close(t−1)` (Wilder ATR, data through t−1)
- `gap_atr = gap_pct / ATRpct20`
- Condition: **0 < gap_atr ≤ 1.0**

Not used: same-day volume, high, low, close; pre-market volume (V1).

## Entry and exit

Official open → official close of the same session.

## Metrics

- **Primary:** `R_oc − β_(t−1) × SPY_oc`
- Robustness: `R_oc − sector_ETF_oc`
- Net under optimistic / base / stress costs (stress includes pessimistic open slippage)

## Controls

`NO_IDENTIFIED_EVENT`: same `gap_atr` bucket, sector and month, no event from the same sources.

## Statistics

All observations on the same date share market moves: aggregate to a daily series (mean abnormal return of that day's events) and test the series, or cluster by date.

## Minimum sample (proposed, to confirm before freezing)

150 open-to-close observations, matching EXP-001, reported by subperiod. Below that, the result is reported INCONCLUSIVE per [00 Vision](../../00-vision.md), not REJECT — Daily's per-trade edge is expected to be smaller than Swing's, so an underpowered sample is especially likely to produce a false REJECT here.

## Acceptance criteria (to freeze)

- Primary positive with 95% CI excluding 0
- Positive **under the stress scenario**
- Greater than control
- Gate 0 passed for at least one live-usable source

## Follow-up

**EXP-002B** (only if accepted): minute bars; entry modelled as VWAP of the first N minutes or open plus pessimistic slippage; tests whether the effect is capturable with manual execution.

**Gating rule:** EXP-002 ACCEPT authorises running EXP-002B — it is not by itself a green light for live capital. Daily does not clear for Phase 5 until EXP-002B's executable-price version also reaches ACCEPT. A result measured against the idealised official open is not evidence of an executable edge for a strategy with manual execution.

## Outcome

_Pending._
