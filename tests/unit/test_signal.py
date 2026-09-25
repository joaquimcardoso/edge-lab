"""Unit tests for src/edgelab/signals/signal.py (STORY-011)."""

from __future__ import annotations

import pytest

from edgelab.signals.execution_mode import ExecutionMode
from edgelab.signals.signal import EntryRange, InvalidSignalError, Signal


def _signal(**overrides) -> Signal:
    defaults = dict(
        symbol="AAPL",
        direction="LONG",
        signal_time="2026-09-25T14:32:08Z",
        data_time="2026-09-25T14:32:00Z",
        entry_range=EntryRange(min=241.20, max=242.00),
        invalidation=237.80,
        strategy_id="EXP-002",
        strategy_version="3.1",
        execution_mode=ExecutionMode.HISTORICAL_REPLAY,
    )
    defaults.update(overrides)
    return Signal(**defaults)


def test_valid_signal_constructs():
    signal = _signal()
    assert signal.symbol == "AAPL"
    assert signal.target is None


def test_entry_range_min_greater_than_max_raises():
    with pytest.raises(InvalidSignalError):
        EntryRange(min=242.00, max=241.20)


def test_invalid_direction_raises():
    with pytest.raises(InvalidSignalError):
        _signal(direction="SIDEWAYS")


@pytest.mark.parametrize("direction", ["LONG", "SHORT", "EXIT"])
def test_every_documented_direction_is_valid(direction):
    signal = _signal(direction=direction)
    assert signal.direction == direction


def test_signal_has_no_confidence_field():
    signal = _signal()
    assert not hasattr(signal, "confidence")


def test_signal_identity_is_the_documented_tuple():
    signal = _signal()
    assert signal.signal_identity() == (
        "EXP-002", "3.1", "AAPL", "LONG", "2026-09-25T14:32:08Z",
    )


def test_signal_identity_ignores_non_identity_fields():
    a = _signal(target=249.50, invalidation=237.80)
    b = _signal(target=None, invalidation=200.00)  # different target/invalidation
    assert a.signal_identity() == b.signal_identity()


def test_signal_identity_differs_when_signal_time_differs():
    a = _signal(signal_time="2026-09-25T14:32:08Z")
    b = _signal(signal_time="2026-09-25T14:33:08Z")
    assert a.signal_identity() != b.signal_identity()
