"""Unit tests for src/edgelab/signals/strategy.py (STORY-011).

Uses only trivial stub strategies -- no real strategy logic exists
yet (Gate 0 has not run; no experiment has reached ACCEPT).
"""

from __future__ import annotations

from typing import Optional

from edgelab.signals.execution_mode import ExecutionMode
from edgelab.signals.signal import EntryRange, Signal
from edgelab.signals.strategy import MarketState, Strategy


class NullStrategy:
    """Never signals -- proves the Protocol shape works for the
    NO_SIGNAL case."""

    strategy_id = "NULL"
    strategy_version = "0.0"

    def evaluate(self, market_state: MarketState) -> Optional[Signal]:
        return None


class CannedStrategy:
    """Always returns the same canned Signal -- proves the Protocol
    shape works for the signal-fires case, and that the same
    market_state always yields the same result (determinism)."""

    strategy_id = "CANNED"
    strategy_version = "1.0"

    def evaluate(self, market_state: MarketState) -> Optional[Signal]:
        return Signal(
            symbol="AAPL",
            direction="LONG",
            signal_time=market_state.as_of,
            data_time=market_state.as_of,
            entry_range=EntryRange(min=100.0, max=101.0),
            invalidation=95.0,
            strategy_id=self.strategy_id,
            strategy_version=self.strategy_version,
            execution_mode=ExecutionMode.BACKTEST,
        )


def test_null_strategy_satisfies_the_protocol_and_returns_no_signal():
    strategy: Strategy = NullStrategy()
    assert strategy.evaluate(MarketState(as_of="2026-09-25T14:32:00Z")) is None


def test_canned_strategy_is_deterministic_given_the_same_market_state():
    strategy: Strategy = CannedStrategy()
    state = MarketState(as_of="2026-09-25T14:32:00Z")
    first = strategy.evaluate(state)
    second = strategy.evaluate(state)
    assert first == second
    assert first.signal_time == state.as_of
