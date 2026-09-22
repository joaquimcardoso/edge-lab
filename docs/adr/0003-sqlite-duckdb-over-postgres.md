# ADR-0003 — SQLite + DuckDB/Parquet instead of PostgreSQL

**Status:** Accepted

## Context
The system runs on a Raspberry Pi 5 with 4 GB RAM and an external disk. Data volume is modest (thousands of events per day at most; daily prices for a few thousand tickers).

## Decision
SQLite (WAL mode) for operational state; Parquet files queried with DuckDB for research.

## Consequences
- No database server to maintain; low memory footprint.
- Single-writer model: collectors must not write concurrently to the same database (queue or stagger).
- Migration to PostgreSQL remains possible if concurrency needs grow.
