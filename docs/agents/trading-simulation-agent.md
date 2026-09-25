# Trading Simulation Agent

## Status

**Not yet activated.** Neither the replay engine nor the paper portfolio this agent would own has been built. This spec exists so that when that work starts, it starts with a defined owner and defined non-goals rather than being improvised inline.

## Role

Owns the historical replay engine (chronological, no-future-information processing over already-collected `price_daily`/`event` data) and the paper portfolio (simulated orders, fills, fees, slippage, cash, positions, P&L, drawdown, exposure) once either exists. Both are pure simulation over already-validated data flows -- this agent never decides whether a strategy is any good, only whether the simulation faithfully represents what would have happened.

## Inputs

- [09-operations-rubric.md](../09-operations-rubric.md) and this repository's existing "collector runs the schedule, this repository analyses the result" split -- the replay engine is analysis, read-only, over Phase 1's stores, same as every audit/report module already built.
- The [Signal](../../src/edgelab/signals/signal.py) / [ExecutionMode](../../src/edgelab/signals/execution_mode.py) contracts (STORY-011).
- A strategy's frozen spec, once one exists to replay or paper-trade.

## Responsibilities

- The replay engine must be provably incapable of exposing a record with `known_at` after the current replay timestamp -- proven by a look-ahead-detection test suite, not asserted.
- The paper portfolio never overwrites historical results (same immutability discipline as `raw_snapshot.py`) and every simulated trade is auditable back to the signal and data that produced it.
- Reuses [STORY-011](../../stories/STORY-011-signal-schema-and-execution-mode.md)'s `Signal`/`ExecutionMode` rather than inventing parallel types for backtest vs. paper.

## Outputs

- A replay engine and paper-portfolio store, once built, each with unit and system tests matching this repository's existing rigor (fakes only where network/broker calls would otherwise be needed -- there are none here, since no broker exists).

## Non-goals

- Does not decide strategy logic or acceptance -- that is the Trading Expert Agent's rubric over the experiment protocol.
- Does not touch Phase 1 collection code or schemas except to read from them.
- Does not add any broker/order-execution code ([ADR-0005](../adr/0005-manual-execution-xtb.md): manual execution, no API).
