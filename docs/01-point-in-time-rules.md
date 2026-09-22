# 01 — Point-in-time rules

These rules apply to every collector, feature and experiment. A result that violates them is invalid regardless of how good it looks.

## 1. Time fields

Every event and every derived observation carries these fields. All timestamps are stored in UTC and interpreted in `America/New_York` for session logic.

| Field | Meaning |
|---|---|
| `published_at` | When the source says the information was published (e.g. SEC acceptance time). |
| `first_seen_at` | When **this system** first observed it. Only exists for data collected live. |
| `known_at` | The time the decision logic is allowed to use. See rule 2. |
| `retrieved_at` | When the raw payload was downloaded (may be much later, for historical backfills). |
| `session_date` | The first regular session that could react to the event. |
| `signal_date` | The session at whose close (or open, for daily) the signal is computed. |
| `entry_date` | The session in which a position would be opened. |

## 2. Rule for `known_at`

- **Live-collected data:** `known_at = first_seen_at`.
- **Historical data with a reliable timestamp** (e.g. SEC EDGAR acceptance time): `known_at = published_at + declared_feed_lag`, where `declared_feed_lag` comes from the latency audit (see [EXP-002](experiments/daily/EXP-002-intraday-continuation.md)).
- **Historical data with a date but no time:** the event is assumed to be known only **after the close of the event date**. See rule 4.
- **Historical data with neither:** excluded.

A decision at time *t* may only use records with `known_at <= t`.

## 3. Session mapping

| Event time (ET) | `session_date` |
|---|---|
| Before 09:30 | Same day |
| 09:30–16:00 (intraday) | Same day, but **excluded** from V1 experiments |
| After 16:00 | Next trading day |
| Weekend / holiday | Next trading day |

Use an exchange calendar library for trading days and half-days. US and European daylight-saving changes happen on different dates; never hard-code a Lisbon–New York offset.

## 4. Date-only events (conservative rule)

When a source provides only a date (e.g. analyst actions from Yahoo Finance), the event could have happened before the open, during the session or after the close. The conservative rule is:

- The reaction window is sessions **D** and **D+1**.
- Filters are measured on that two-session window.
- The earliest entry is the **open of D+2**.

This loses part of any real effect. It is the price of avoiding look-ahead.

## 5. Derived features

- ATR, beta, average volume and any rolling statistic use data **through the previous close** (t-1).
- Beta is estimated from a trailing window ending at t-1, never from the full sample.
- Sector classification is **as of the event date**. The 2018 GICS reclassification moved several large companies (including Meta and Alphabet) to Communication Services, and sector ETFs such as XLC did not exist before then. Keep a dated sector history and a documented fallback for early periods.
- Fundamentals are keyed by the **filing date** (`filed` in SEC XBRL data), not by the fiscal period end.

## 6. Survivorship

- The universe for any historical date includes companies that were listed on that date, including those later delisted, acquired or bankrupt.
- When delisted prices are unavailable, the experiment report must state the coverage gap and its likely direction of bias.

## 7. Immutable raw snapshots

Vendors revise historical data. The system therefore stores every raw payload exactly as received, with `retrieved_at`, `source`, and a SHA-256 hash. Normalised tables are always rebuildable from raw snapshots. A backtest references the snapshot hashes it used.

## 8. LLM contamination

Language models have a training cutoff and may "know" what happened after historical events. Therefore:

- LLM classification is **never** used on events that occurred before the model's training cutoff when that classification feeds a backtest.
- For historical experiments, use deterministic rules, structured vendor fields or a frozen classifier trained only on data prior to the test window.
- Every LLM-assisted record stores `model_provider`, `model_name`, `model_version`, `prompt_version`.

## 9. Forbidden inputs

| Never use | Why |
|---|---|
| Analyst price targets as a price or entry level | They are opinions about the future, not market data |
| Forecast, expected or projected indicators | Not observed data |
| Full-session volume or close in a same-session (daily) decision | Only known after the decision |
| The day's high/low/close to decide the day's entry | Look-ahead |
| Parameters fitted on the period being tested | In-sample contamination |
| A threshold chosen because it includes a known winner | Hindsight |

## 10. Live-data freshness (Phase 3+)

For live signals and manual execution, prices shown to the operator must include currency, exchange and timestamp, and be verified against a second source when used for an order. Signals built on data older than the strategy's freshness threshold are suppressed, not downgraded.

## Checklist for every new feature

- [ ] Which time field gates it?
- [ ] Is every input's `known_at` ≤ decision time?
- [ ] Are rolling statistics computed through t-1?
- [ ] Is the sector/universe membership as of the event date?
- [ ] Can it be rebuilt from raw snapshots?
