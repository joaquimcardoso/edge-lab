# STORY-004 — `prices_daily` collector and price store

| Field | Value |
|---|---|
| Status | TRADING_REVIEWED |
| Owner stage | Story Agent |

## Source

[07-development-workflow.md §Suggested MVP story sequence, item 4](../docs/07-development-workflow.md#suggested-mvp-story-sequence-phase-1): "`prices_daily` collector + price store (needed by every downstream feature)." Source rules from [02-data-sources.md §yfinance](../docs/02-data-sources.md#yfinance): "Treat as fragile. Every collector call is wrapped, failures are logged and surfaced, and a failed download never produces a signal." Table schema from [03-architecture.md §Core data model](../docs/03-architecture.md#core-data-model): `price_daily` — `security_id, date, open, high, low, close, adj_close, volume, snapshot_id`.

## Goal

A collector that fetches one security's daily OHLCV history from yfinance for a date range, persists the fetched data as an immutable raw snapshot, and a normaliser that parses that snapshot into typed `price_daily` rows — both raw close and adjusted close stored (per [01-point-in-time-rules.md §12](../docs/01-point-in-time-rules.md): adjusted close for returns/rolling stats, raw close for gaps).

## Acceptance criteria

- [ ] The yfinance call is behind an injected `HistoryFetcher` protocol (a `.fetch(ticker, start, end)` returning a DataFrame-like object), never called directly inside collection logic — unit and system tests run against a fake fetcher, no live network calls (this sandbox's egress does not reach Yahoo Finance, verified during STORY-002; a real network dependency in an automated suite is undesirable regardless).
- [ ] `collect_prices_daily(ticker, ...)` fetches history for `[start, end)`, serialises the result to CSV bytes, and persists it as one raw snapshot via `write_raw_snapshot` with `source="prices_daily"`.
- [ ] A fetch that raises, or returns zero rows, raises `PricesDailyError` — propagated, never silently written as "no prices for this range" (`02-data-sources.md`: "a failed download never produces a signal"; `04-infrastructure.md`: never converted into "no event").
- [ ] `parse_price_csv(raw_csv_bytes)` parses the stored CSV back into typed rows (`date, open, high, low, close, adj_close, volume`), independent of pandas/yfinance at parse time (raw bytes in, plain rows out) — so a stored snapshot can be re-parsed years later even if the fetch-time library has changed. A single malformed row is skipped, but if every row in a non-empty file fails to parse (e.g. a column got renamed upstream), that raises rather than silently returning zero rows — caught during review: an all-rows-failed result is a schema mismatch, not "no prices for this range."
- [ ] `normalise_prices_daily_snapshot(snapshot_id, security_id, ...)` reads one raw snapshot, parses it, and writes each row to the `price_daily` store, deduplicated on `(security_id, date)` so re-normalising the same snapshot (or overlapping date ranges from separate collection runs) never creates duplicate rows.
- [ ] Both `close` (raw) and `adj_close` (dividend/split-adjusted) are stored as distinct columns — never only one, per [01-point-in-time-rules.md §12](../docs/01-point-in-time-rules.md).
- [ ] Unit tests cover: CSV parsing against a realistic fixture (including a row with a stock-split-adjusted close different from raw close); a fetch failure and an empty-result fetch both raising `PricesDailyError`; dedup on `(security_id, date)`.
- [ ] System test: `collect_prices_daily` (fake fetcher) followed by `normalise_prices_daily_snapshot` end-to-end through the real raw-snapshot store, verifying stored rows read back correctly and that re-running normalisation is idempotent.

## Explicit scope boundary

- **The "raw" snapshot is yfinance's parsed DataFrame serialised to CSV, not Yahoo's original HTTP response.** A true byte-for-byte capture of Yahoo's chart API would mean bypassing `yfinance`'s own HTTP layer (which handles cookie/crumb anti-scraping requirements that changed multiple times through 2024–2025) and reimplementing that fragile logic ourselves — a worse trade than accepting one processing layer's remove from the literal wire bytes. This is the earliest artifact this repository's own code touches, which is what STORY-001's raw store is for; it is a materially weaker reconstructability guarantee than `edgar_8k`'s complete-submission `.txt` (STORY-002/003), and that difference is deliberate, not an oversight.
- No Stooq fallback yet — this story is yfinance only. A Stooq-backed collector for redundancy is future work, not blocking.
- No corporate-action *event* records (a split or dividend as its own typed event) — only its effect on `adj_close` is captured, via yfinance's own adjustment.
- No universe-wide scheduling — single-ticker collection, same boundary STORY-002 drew for `edgar_8k`.

## Definition of done

All seven gates apply. System Tester's "re-run every FROZEN experiment" clause remains vacuous — no experiment is FROZEN yet.

## Credentials, if any

None. yfinance requires no API key.
