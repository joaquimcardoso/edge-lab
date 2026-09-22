# ADR-0002 — Free data first

**Status:** Accepted

## Context
A timestamped vendor stack (prices incl. delisted + analyst events) costs roughly $180–280/month. No edge has been demonstrated yet.

## Decision
Phases 1–3 use free sources (SEC EDGAR, XBRL, yfinance, RSS, GDELT) plus the system's own forward snapshots.

**Purchase trigger:** buy paid data only when an experiment shows a positive result under base costs on free historical data and/or forward paper trading, and the paid data would confirm or refute it with a larger, cleaner sample.

## Consequences
- Weaker historical tests for analyst events (date only, survivorship).
- Forward collection starts early; the archive's value grows with time.
- The purchase decision is recorded as a new ADR.
