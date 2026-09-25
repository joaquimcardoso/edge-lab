# STORY-009 — Daily operations report artifact

| Field | Value |
|---|---|
| Status | TRADING_REVIEWED |
| Owner stage | Story Agent |

## Source

The user's explicit request for "a black box... and look to artifacts generated" plus "right now neither artifacts format are prepared or anticipated." [03-architecture.md's Planned repository layout](../docs/03-architecture.md#planned-repository-layout) already names `reports/` ("generated markdown reports, committed") and the Reporter component ("Markdown reports, decision log entries") -- this story is the first thing that actually writes to it. Depends on [STORY-008](STORY-008-pi-collector-entrypoint.md)'s entrypoint and config.

## Goal

A single, reviewable artifact per calendar day (America/New_York, matching every other operational timestamp in this repository) summarising what the collection pipeline actually did: how many raw snapshots and events were written today, cumulative feed-latency progress toward Gate 0's real pass bar, a raw-store integrity spot-check, today's recorded collector failures, and disk usage -- written as both a Markdown report (for a human to read) and a JSON sibling (for STORY-010's rubric to score without re-parsing Markdown). This is analysis and reporting only: it reads already-persisted state, same "collector runs the schedule, this repository analyses the result" split as STORY-007.

## Acceptance criteria

- [ ] `storage/raw_snapshot.py` gains `list_all_raw_snapshots(*, db_path)` and `storage/event_store.py` gains `list_all_events(*, db_path)` -- read-only, for reporting; neither module's write/dedup/immutability behaviour changes.
- [ ] `scripts/collect_premarket_8k.py` gains `append_failure_log(summary, *, log_dir, now)`, appending one JSON line per recorded failure to `<log_dir>/collector_failures.jsonl` (append-only, matching the raw-store precedent) -- without this, a day's failures exist only in an in-memory `RunSummary` a systemd oneshot run never persists anywhere, making them invisible to any later review. `main()` calls it after every run. `CollectorConfig` gains `log_dir` (optional `EDGELAB_LOG_DIR` override, defaulting under `data_dir`, same pattern as every other derived path).
- [ ] `src/edgelab/report/daily_report.py`'s `build_daily_ops_report(report_date, *, raw_db_path, event_db_path, data_dir, log_dir, integrity_sample_size=20)` returns a `DailyOpsReport` with: snapshot counts by source for `report_date` (an America/New_York calendar date, derived from each record's `first_seen_at`/`retrieved_at`); event counts by type for the same date; all-time totals; an integrity check over a sample of up to `integrity_sample_size` raw snapshots (re-verifying sha256 via the existing `read_raw_snapshot`, never re-implementing that check); today's failures read back from `collector_failures.jsonl`; cumulative (all-time, not just today's) feed-latency stats per (source, event_type) via STORY-007's `compute_latency_stats`, reusing it rather than recomputing anything -- combinations with too little data yet are recorded as "insufficient data" (the `FeedLatencyAuditError` message), never silently omitted or shown as a false PASS/FAIL; total on-disk bytes under `data_dir`.
- [ ] `render_daily_report(report) -> str` produces Markdown matching this repository's existing report convention, reusing `feed_latency.render_report`'s own table for the latency section rather than a second implementation of the same table.
- [ ] `write_daily_report(report, markdown, *, reports_dir)` writes `reports/<date>-ops.md` and `reports/<date>-ops.json` (via `dataclasses.asdict`, nested `LatencyStats` included) -- re-running for the same date overwrites both (a report is a snapshot of state at generation time, not an append-only log; unlike raw evidence, regenerating it from the same underlying data is expected and safe).
- [ ] A day with zero snapshots/events (weekend, holiday, or before any collection has run) produces a valid, non-crashing report stating that plainly, not an empty or malformed one.
- [ ] Unit tests: date-bucketing (a record just before vs. just after midnight ET), the integrity check catching a real tampered payload (write two snapshots, corrupt one on disk, confirm the report names exactly that one as failed), a zero-activity day, and `append_failure_log`'s JSONL format and append (not overwrite) behaviour across two calls.
- [ ] System test: full pipeline -- `run()` from STORY-008 against a fake HTTP client, then `build_daily_ops_report` + `render_daily_report` + `write_daily_report` over the resulting real stores, asserting the written Markdown and JSON both exist and agree with each other on every count.

## Explicit scope boundary

- No good-day/bad-day verdict, no PASS/FAIL judgement of the day as a whole -- purely descriptive. STORY-010 scores it.
- Does not change collection scheduling or add new collectors -- 8-K only, same as STORY-008.
- `list_all_*` functions are simple full-table reads, acceptable at this project's local-SQLite, single-operator research scale; not paginated or indexed for a larger deployment -- noted here rather than silently assumed to scale indefinitely.
- Does not send any notification/alert -- the report is a file; STORY-010's Ops Reviewer Agent is what decides whether a human needs to be told.

## Definition of done

All seven gates apply.

## Credentials, if any

None beyond what STORY-008 already requires.
