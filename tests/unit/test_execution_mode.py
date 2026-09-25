"""Unit tests for src/edgelab/signals/execution_mode.py (STORY-011)."""

from __future__ import annotations

import pytest

from edgelab.signals.execution_mode import (
    ExecutionMode,
    ExecutionModeError,
    LIVE_ORDER_EXECUTION_ALLOWED_MODES,
    require_order_execution_allowed,
)


def test_no_mode_is_allowed_to_submit_real_orders_today():
    assert LIVE_ORDER_EXECUTION_ALLOWED_MODES == frozenset()


@pytest.mark.parametrize("mode", list(ExecutionMode))
def test_require_order_execution_allowed_raises_for_every_current_mode(mode):
    with pytest.raises(ExecutionModeError, match="not permitted"):
        require_order_execution_allowed(mode)


def test_live_signal_mode_does_not_imply_order_execution():
    # The specific property the mission document names: LIVE_SIGNAL
    # must never be treated as LIVE_ORDER_EXECUTION.
    assert ExecutionMode.LIVE_SIGNAL not in LIVE_ORDER_EXECUTION_ALLOWED_MODES
    with pytest.raises(ExecutionModeError):
        require_order_execution_allowed(ExecutionMode.LIVE_SIGNAL)
