# STORY-001 — Raw snapshot store

| Field | Value |
|---|---|
| Status | TRADING_REVIEWED |
| Owner stage | Story Agent |

## Source

[07-development-workflow.md §Suggested MVP story sequence, item 1](../docs/07-development-workflow.md#suggested-mvp-story-sequence-phase-1): "Raw snapshot store: write-only, immutable, SHA-256, for one source." Also required by [01-point-in-time-rules.md §7](../docs/01-point-in-time-rules.md) (immutable raw snapshots with `retrieved_at`, `source`, SHA-256) and the `raw_snapshot` table in [03-architecture.md §Core data model](../docs/03-architecture.md#core-data-model).

## Goal

A Python module that persists one fetch attempt's raw payload as an immutable, content-hashed row, with no update or delete capability exposed anywhere in its API, so every later collector can be built on top of it without re-solving immutability itself.

## Acceptance criteria

- [ ] `write_raw_snapshot(source, retrieved_at, payload, url=None, first_seen_at=None)` writes exactly one row to a `raw_snapshot` table (SQLite, WAL mode) with columns `id, source, url, retrieved_at, first_seen_at, sha256, payload_path, payload_bytes`, and writes the raw payload bytes to a content-addressed file at `payload_path`.
- [ ] `sha256` is computed from the actual payload bytes and verified to match on read-back.
- [ ] `first_seen_at` defaults to `retrieved_at` when not given (matches [01-point-in-time-rules.md §2](../docs/01-point-in-time-rules.md): "Live-collected data: `known_at = first_seen_at`").
- [ ] An empty or `None` payload raises an error and writes **no row at all** — a failed fetch must never produce a snapshot (per [02-data-sources.md](../docs/02-data-sources.md): "a failed download never produces a signal").
- [ ] The module exposes no update or delete function for any row it has written — not "discouraged," structurally absent from the public API.
- [ ] `read_raw_snapshot(snapshot_id)` returns the row plus the payload bytes, and re-verifies the SHA-256 on every read, raising if the on-disk payload doesn't match the recorded hash.
- [ ] Two writes of identical payload content at different `retrieved_at` times produce two separate rows (append-only: recording *when this system observed something* matters even if the content is unchanged).
- [ ] Unit tests cover: a successful write/read round trip, empty-payload rejection, hash-tampering detection on read, and that writing the same inputs twice is deterministic in content (same `sha256`, same file bytes) while still producing two distinct rows.

## Explicit scope boundary

- No collector (EDGAR 8-K, prices, etc.) is built in this story — that's STORY-002. This story only builds the thing collectors will write into.
- No normaliser, event store, or `known_at` computation beyond passing through `first_seen_at` — that's later stories.
- No deployment to the Pi. Built and tested in this repository only, per [07-development-workflow.md §Scope](../docs/07-development-workflow.md#scope).
- No `config/`-driven configuration system yet — `db_path` and `data_dir` are plain function arguments for now; wiring them to `config/` is deferred until a second module needs the same values.

## Definition of done

All seven gates apply except System Tester's "re-run every FROZEN experiment" clause, which is vacuously satisfied — no experiment is FROZEN yet, so there is nothing to regress against. System Tester still runs a small end-to-end smoke test of this module standalone.

## Credentials, if any

None. This story touches no external source.
