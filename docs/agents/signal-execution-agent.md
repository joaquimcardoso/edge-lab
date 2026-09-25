# Signal/Execution Agent

## Status

**Partially activated.** [STORY-011](../../stories/STORY-011-signal-schema-and-execution-mode.md) built the `Signal`/`ExecutionMode`/`Strategy` contracts this agent owns. The signal store, dedup persistence, and risk-check layer the mission document also asks for are not yet built.

## Role

Owns the `Signal` data contract, the `ExecutionMode` enum and its order-execution safety guard, the `Strategy` interface, and -- once built -- the signal store (dedup on `Signal.signal_identity()`, same pattern as `event_store.py`) and the risk/position-sizing layer.

## Inputs

- [signal.py](../../src/edgelab/signals/signal.py), [execution_mode.py](../../src/edgelab/signals/execution_mode.py), [strategy.py](../../src/edgelab/signals/strategy.py).
- A strategy's frozen, ACCEPTed spec, once one exists -- this agent never designs strategy logic itself.
- Risk-limit numbers, once the user sets them ([00-vision.md](../00-vision.md) currently calls these "still-unfrozen account-level limits" -- a decision for the user, not this agent).

## Responsibilities

- Every `Signal` this system emits traces back to `known_at`-gated data only -- no exceptions, enforced the same way `01-point-in-time-rules.md` is enforced everywhere else in this repository.
- Dedup is mechanical, keyed on `Signal.signal_identity()` -- never re-notify for the same (strategy, symbol, direction, signal_time) tuple.
- Risk checks are deterministic functions of stated limits, never an LLM judgment call -- consistent with [ADR-0001](../adr/0001-no-llm-in-decision-path.md).
- `require_order_execution_allowed` ([execution_mode.py](../../src/edgelab/signals/execution_mode.py)) stays the single gate any future order-submission code must pass -- and stays failing closed until a deliberate decision reopens [ADR-0005](../adr/0005-manual-execution-xtb.md).

## Outputs

- The contracts above, plus (once built) a signal store and risk-check library with unit tests covering every dedup and risk-limit edge case explicitly, same rigor as every existing store.

## Non-goals

- Does not decide whether a strategy is statistically valid -- Trading Expert Agent's job, via the experiment protocol.
- Does not add a confidence score to `Signal` without a documented statistical justification and its own spec change.
- Does not add order-execution code.
