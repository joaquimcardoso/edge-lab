# ADR-0005 — Manual execution on XTB

**Status:** Accepted

## Context
The broker is XTB. XTB discontinued its API on 14 March 2025 and does not support automated strategies.

## Decision
The system produces signals and a paper log. Orders are placed manually. No execution engine is built.

## Consequences
- Strategies requiring precise timing (daily) carry a higher acceptance bar.
- If automated execution becomes necessary, it requires a broker with an API and a new ADR.
