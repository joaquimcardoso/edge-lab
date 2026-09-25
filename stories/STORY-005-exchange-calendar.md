# STORY-005 — Exchange-calendar integration

| Field | Value |
|---|---|
| Status | TRADING_REVIEWED |
| Owner stage | Story Agent |

## Source

Added to the MVP sequence by the Trading Expert Agent's review after [STORY-003](STORY-003-normaliser-event-store.md) ([06-trading-system-audit-v1.md](../docs/06-trading-system-audit-v1.md#story-003--8-k-normaliser-and-event-store-2026-09-25)): STORY-003 deliberately left `session_date` unset rather than fake it, and the feature builder (item 6) needs trading-day arithmetic for rolling windows regardless. Both needs share one dependency. Rule source: [01-point-in-time-rules.md §3](../docs/01-point-in-time-rules.md) (session mapping table) — "Use an exchange calendar library for trading days and half-days... never hard-code a Lisbon–New York offset."

## Goal

A small calendar module, backed by a real, maintained NYSE trading-calendar library (not a hand-rolled weekday check), that answers "is this a trading day" and "what is the next trading day," and a `compute_session_date` function implementing rule 3's mapping table exactly. Then: wire it into STORY-003's `edgar_8k` normaliser so `session_date` is actually populated instead of `None`.

## Acceptance criteria

- [ ] `is_trading_day(date)` and `next_trading_day(date)` (first trading day strictly after `date`) are backed by `pandas_market_calendars`' NYSE calendar — real holidays (including observed-holiday shifts) and half-days, not a weekday-only approximation.
- [ ] `compute_session_date(event_time_utc)` converts a UTC ISO-8601 timestamp to `America/New_York` via `zoneinfo` (DST-correct, never a hard-coded offset) and applies [01-point-in-time-rules.md §3](../docs/01-point-in-time-rules.md)'s table exactly: before 09:30 ET on a trading day → same day; 09:30–16:00 ET → same day (the *intraday-exclusion* from V1 experiments is an experiment-level filter, not this function's job); after 16:00 ET → next trading day; a weekend or holiday date → next trading day, regardless of time.
- [ ] The `edgar_8k` normaliser (STORY-003) is updated to call `compute_session_date(published_at)` instead of leaving `session_date` as `None` — closing that story's carried-forward open item. `known_at`'s own computation (`= first_seen_at`) is unchanged; only `session_date` changes.
- [ ] Unit tests cover: a holiday (e.g. Thanksgiving) and the surrounding weekend correctly excluded from `is_trading_day`; the day after a holiday cluster resolved correctly by `next_trading_day`; each of the four session-mapping branches (pre-open, intraday, post-close, weekend/holiday) with a concrete UTC timestamp; a timestamp near a US DST transition resolving to the correct ET wall-clock time.
- [ ] System test: re-running STORY-003's normaliser end-to-end now produces a non-`None` `session_date` on every event, consistent with the timestamp in the fixture used.

## Explicit scope boundary

- No half-day-aware intraday cutoff logic beyond what `pandas_market_calendars`' schedule already encodes — a half-day still counts as a trading day for `is_trading_day`/`next_trading_day`; adjusting the 16:00 close boundary on a half-day (13:00 ET close) is deferred until a story actually needs same-day intraday precision (Daily's Gate 0, STORY-007).
- NYSE calendar only — no other exchange, consistent with this repository's US-equity scope.
- Does not touch `prices_daily` (STORY-004) — `price_daily` rows are already keyed by trading-day date from yfinance directly; no session-date field exists on that table per `03-architecture.md`'s schema.

## Definition of done

All seven gates apply. System Tester's "re-run every FROZEN experiment" clause remains vacuous — no experiment is FROZEN yet.

## Credentials, if any

None. The calendar library computes holidays locally; no external calls.
