# STORY-011 — Signal schema, execution-mode enum, strategy interface

| Field | Value |
|---|---|
| Status | TRADING_REVIEWED |
| Owner stage | Story Agent |

## Source

The user's request to add pieces of the "Research → Replay → Paper Trading → Live Signal" mission document that do not impact the current (Phase 1) lab. This story is the "Foundation" tier: a structured `Signal` data contract, an execution-mode enum with a live-order-execution safety guard, and a strategy interface -- none of it wired to any real strategy, since none exists yet (Phase 2 hasn't started). [ADR-0001](../docs/adr/0001-no-llm-in-decision-path.md) and [ADR-0005](../docs/adr/0005-manual-execution-xtb.md) govern this story's two hard constraints: no confidence score without statistical justification, and no live order execution path exists or is being built.

## Goal

A `Signal` dataclass and an `ExecutionMode` enum that any future strategy, backtest, replay, paper, or live-signal code can share -- so a strategy's logic is never duplicated per mode, matching this repository's existing discipline of one engine reused by every caller (STORY-007's `compute_latency_stats`, STORY-009's `render_report`, etc.). Plus a `Strategy` protocol, tested only against a trivial stub -- no real strategy is validated yet (Gate 0 hasn't run), so none is wired in.

## Acceptance criteria

- [ ] `src/edgelab/signals/signal.py`'s `Signal` dataclass: `symbol`, `direction` (`"LONG" | "SHORT" | "EXIT"`), `signal_time` (ISO-8601 UTC, this repository's timestamp convention throughout), `data_time` (the `known_at` boundary of the last input the strategy used -- the point-in-time evidence for the signal, not just when it fired), `entry_range` (`EntryRange(min, max)`), `invalidation`, `target` (optional), `strategy_id`, `strategy_version`, `execution_mode` (an `ExecutionMode`). Validates `entry_range.min <= entry_range.max` at construction, raising `ValueError` otherwise. **No `confidence` field exists** -- deliberately omitted, not defaulted to `None`, per ADR-0001 and the mission document's own "do not introduce a generic AI confidence score unless statistically justified": the temptation to quietly populate it later is removed by not having a field to populate.
- [ ] `signal_identity()` returns the exact tuple a future signal store would dedup on: `(strategy_id, strategy_version, symbol, direction, signal_time)` -- same "identity is a tuple of real fields, not an invented ID" pattern as `event_store.py`'s `(source, source_id, type)` dedup key. This story does not build the store itself (deferred -- see scope boundary); it defines the identity function the store will use.
- [ ] `src/edgelab/signals/execution_mode.py`'s `ExecutionMode` enum: `BACKTEST`, `HISTORICAL_REPLAY`, `PAPER`, `LIVE_SIGNAL`. `LIVE_ORDER_EXECUTION_ALLOWED_MODES` is a **deliberately empty** frozenset -- no mode in this system may submit a real broker order today (ADR-0005: manual execution only, no API). `require_order_execution_allowed(mode)` raises `ExecutionModeError` for every current mode, unconditionally -- this is the "LIVE_SIGNAL != LIVE_ORDER_EXECUTION must remain true" guard the mission document asks for, made concrete as code that fails closed rather than a comment.
- [ ] `src/edgelab/signals/strategy.py`'s `Strategy` Protocol: `strategy_id: str`, `strategy_version: str`, `evaluate(self, market_state: MarketState) -> Optional[Signal]`. `MarketState` is a minimal placeholder (`as_of: str`, the `known_at` boundary) -- intentionally thin; a real strategy's frozen spec will define what it actually needs to read, not this story.
- [ ] Unit tests: `Signal` construction (valid; `entry_range.min > max` raises), `signal_identity()`'s tuple shape and that two signals differing only in, say, `target` still produce the same identity (dedup is about "what/when/who," not every field), `require_order_execution_allowed` raising for every current `ExecutionMode` value, and a trivial stub `Strategy` (always returns `None`, or always returns a canned `Signal`) satisfying the Protocol via `isinstance`-style structural check or direct use.

## Explicit scope boundary

- No signal store, no paper portfolio, no risk/metrics libraries, no replay engine -- those are a separate, larger tier the user has not yet asked for; do not build them speculatively here.
- No real strategy logic -- `MarketState` and the stub `Strategy` in tests are placeholders, not EXP-002 or any other spec.
- No broker code exists or is added -- `require_order_execution_allowed` guards a path that has nothing on the other side of it yet.

## Definition of done

All seven gates apply.

## Credentials, if any

None.
