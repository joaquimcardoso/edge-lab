# STORY-014 — Historical backfill entrypoint (8-K raw snapshots + prices, collect-only where normalisation would be unsafe)

| Field | Value |
|---|---|
| Status | TRADING_REVIEWED |
| Owner stage | Trading Expert Agent |

## Source

The user's explicit question: "this system will be executing only live test, why not also test with old data, like paper test for all methods existing?" Answered in conversation with two concrete blockers -- (1) zero historical data has ever been collected in this repository (confirmed: no `.db`/`.sqlite` files exist anywhere), and (2) [01-point-in-time-rules.md](../docs/01-point-in-time-rules.md)'s `known_at = published_at + declared_feed_lag` formula for historical normalisation requires Gate 0's measured latency audit, which [STORY-003](STORY-003-edgar-8k-normaliser.md)'s own text explicitly forbids using before that audit exists. This story closes blocker (1) as far as it safely can without touching blocker (2).

## Goal

A one-time (not scheduled) backfill entrypoint that populates real historical raw evidence using the exact collectors STORY-002/STORY-004 already built and tested -- no new collector logic, no new data source. Two independent halves, because they have genuinely different point-in-time safety properties, discovered during this story's own design review:

1. **8-K backfill: raw snapshots only, deliberately not normalised.** Reuses `collect_8k_for_cik` as-is to pull whatever SEC EDGAR's `filings.recent` window currently returns (documented gap: roughly the last year; older history needs `filings.files` pagination, not implemented -- named below as a follow-on, not silently worked around). These raw snapshots are genuine, valuable, immutable evidence (ADR-0006) worth capturing now before they age out of that window. They are **not** run through `normalise_snapshot` here: that normaliser sets `known_at = first_seen_at` (01-point-in-time-rules.md §2, "live-collected rule") -- correct when `first_seen_at` is a real-time collection timestamp, but silently wrong for a backfilled snapshot, where `first_seen_at` would be today's backfill run time, not when the filing was actually knowable historically. Running the existing normaliser over backfilled 8-K snapshots would fabricate incorrect `known_at` values and corrupt point-in-time correctness for any future backtest that used them -- exactly the class of mistake this project's own rules exist to prevent. Normalising these snapshots is deferred until a historical-specific normalisation path (using the frozen `published_at + declared_feed_lag` formula, once Gate 0 supplies a real `declared_feed_lag`) exists -- tracked as an explicit open item, not built here.
2. **Prices backfill: collect and normalise, fully safe today.** `PriceBar` (src/edgelab/storage/price_store.py) carries no `known_at`/`first_seen_at` field at all -- daily OHLCV bars are unambiguous, published once per day, with no live-vs-historical timing distinction this repository tracks (01-point-in-time-rules.md §12 only distinguishes raw close from adjusted close, not timing). `collect_prices_daily` already takes an arbitrary `[start, end)` range. So prices are collected **and** normalised into `price_daily` end to end, immediately usable once Phase 2's historical price-based experiments (e.g. EXP-001F) actually run.

## Acceptance criteria

- [x] `src/edgelab/config.py`'s `CollectorConfig` gains `price_db_path: Path`, derived under `EDGELAB_DATA_DIR` by default (`price_daily.db`) and individually overridable via `EDGELAB_PRICE_DB_PATH`, following the exact pattern of every other derived path this dataclass already has. Every existing hand-built `CollectorConfig(...)` in the test suite is updated to pass it (same precedent STORY-009 set when it added `log_dir`).
- [x] `scripts/backfill_historical.py` exposes `backfill_8k(cik_ticker_pairs, *, http_client, config) -> RunSummary`-shaped result (reusing `CollectionFailure`/per-CIK isolation the same way STORY-008's `run()` does) that calls `collect_8k_for_cik` per CIK and writes raw snapshots only -- it never imports or calls `normalise_snapshot`.
- [x] `backfill_prices(cik_ticker_pairs, *, history_fetcher, config, start, end) -> RunSummary`-shaped result that calls `collect_prices_daily` then `normalise_prices_daily_snapshot` per (ticker, cik), isolating a `PricesDailyError` for one ticker from stopping the rest of the universe (same per-item isolation principle as `backfill_8k` and STORY-008's `run()`).
- [x] `main()` wires both functions to real config, `RequestsHttpClient`, `YFinanceHistoryFetcher`, and the universe file, selectable via a `--kind {8k,prices,both}` CLI flag (default `both`) and `--start`/`--end` flags for the prices half (defaulting to a multi-year lookback ending yesterday) -- runnable by hand on the Pi or a laptop, not installed as a systemd timer (this is explicitly a one-time/on-demand job, not a recurring schedule).
- [x] Never silently retries or reduces scope on a partial failure -- both halves log every per-item failure via the same `append_failure_log`-style JSONL pattern STORY-009 established, reusing that exact function where the shape matches.
- [x] This story's own text (here and in a corresponding entry in [06-trading-system-audit-v1.md](../docs/06-trading-system-audit-v1.md)) states plainly, in one place easy to find later: backfilled 8-K raw snapshots exist on disk but produce zero events until a historical-safe normalisation path is built -- so nobody mistakes "the backfill ran" for "historical 8-K event data is ready to backtest."
- [x] Unit tests: `backfill_8k`'s per-CIK success/failure isolation (fake `HttpClient`, no real network) and an explicit assertion that no `event.db` row exists afterward (proving the "never normalises" acceptance criterion, not just documenting it). `backfill_prices`'s per-ticker success/failure isolation (fake `HistoryFetcher`) and that `price_daily` rows exist afterward. `CollectorConfig`'s new `price_db_path` default-derivation and override.
- [x] System test: `backfill_prices` end-to-end against a fake `HistoryFetcher`, through the real raw store and real price store in a temp dir, asserting final `price_daily` state.

## Explicit scope boundary

- Does not implement SEC EDGAR's `filings.files` pagination for filings older than the `filings.recent` window -- named as a real, current gap in this story's own text and in the audit doc, not fixed here. A future story can add it if deeper 8-K history becomes worth the added complexity.
- Does not build historical-safe 8-K normalisation (the `published_at + declared_feed_lag` path) -- blocked on Gate 0's actual measured audit per STORY-003's own frozen text; building it now would mean guessing at `declared_feed_lag`, which that story explicitly forbids.
- Does not run on a schedule -- no systemd unit, no cron. A human runs this by hand when they want to (re-)seed historical data.
- Does not decide which years of price history are "enough" for any strategy -- `--start`/`--end` are operator-supplied; this story only makes the range parameterizable and safe to run repeatedly (idempotent via `price_store`'s own dedup).
- Does not touch STORY-008's scheduled 15-minute 8-K poll or STORY-009/010's daily report/verdict/Telegram pipeline in any way -- fully additive, separate entrypoint script.

## Definition of done

All seven gates apply, as every prior story. Same real-network caveat as every other collector in this repository: this sandbox's egress does not reach `data.sec.gov` or Yahoo Finance, so both collectors are exercised only against fakes here, exactly as STORY-002/004/008 already are.

## Credentials, if any

None beyond what STORY-008 already requires (`EDGELAB_SEC_USER_AGENT`, `EDGELAB_DATA_DIR`) -- yfinance needs no key.
