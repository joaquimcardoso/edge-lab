"""Execution-mode enum and the live-order-execution safety guard.

Four modes share one strategy engine (the mission document's core
principle, and already this repository's own discipline elsewhere):
BACKTEST, HISTORICAL_REPLAY, PAPER, LIVE_SIGNAL. None of them may
submit a real broker order -- ADR-0005 already decided execution is
manual, via XTB, with no API. LIVE_ORDER_EXECUTION_ALLOWED_MODES is
deliberately empty: there is no broker integration in this
repository, so there is nothing for any mode to be allowed to do.
require_order_execution_allowed exists now, before any order-
submission code does, so that if such code is ever added, it has to
call this guard and finds it fails closed by default -- the
"LIVE_SIGNAL != LIVE_ORDER_EXECUTION must remain true" property made
concrete as code, not just a comment someone could miss.

Story: stories/STORY-011-signal-schema-and-execution-mode.md
"""

from __future__ import annotations

from enum import Enum


class ExecutionMode(str, Enum):
    BACKTEST = "BACKTEST"
    HISTORICAL_REPLAY = "HISTORICAL_REPLAY"
    PAPER = "PAPER"
    LIVE_SIGNAL = "LIVE_SIGNAL"


class ExecutionModeError(RuntimeError):
    """Raised when code attempts an operation its execution mode does
    not permit -- most importantly, submitting a real broker order.
    """


# Deliberately empty. No ExecutionMode may submit a real order today.
# Widening this set is a decision that reopens ADR-0005, not a
# config change -- it must never be done implicitly.
LIVE_ORDER_EXECUTION_ALLOWED_MODES: frozenset = frozenset()


def require_order_execution_allowed(mode: ExecutionMode) -> None:
    """Raises ExecutionModeError for every ExecutionMode that exists
    today -- there is no broker integration in this repository, so
    there is nothing on the other side of this guard yet. Any future
    order-submission code must call this first and will find it
    fails closed.
    """
    if mode not in LIVE_ORDER_EXECUTION_ALLOWED_MODES:
        raise ExecutionModeError(
            f"{mode.value} is not permitted to submit real broker orders. "
            "No ExecutionMode is today (ADR-0005: manual execution only, no API); "
            "widening LIVE_ORDER_EXECUTION_ALLOWED_MODES is a deliberate decision "
            "that reopens that ADR, not a default to relax."
        )
