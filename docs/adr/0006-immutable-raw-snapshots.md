# ADR-0006 — Immutable raw snapshots

**Status:** Accepted

## Context
Vendors revise historical data silently. A backtest must be reproducible exactly as run.

## Decision
Every raw payload is stored as received with source, `retrieved_at`, `first_seen_at` and a SHA-256 hash. Normalised tables are derived and rebuildable. Experiment runs reference snapshot IDs.

## Consequences
- Storage grows continuously; raw payloads are compressed.
- Backups of the raw store are mandatory (see [04](../04-infrastructure.md)).
