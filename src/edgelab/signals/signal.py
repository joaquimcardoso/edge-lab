"""Structured trading signal -- the data contract a strategy produces,
shared by every execution mode (backtest, historical replay, paper,
live signal). One engine, one signal shape, regardless of where the
data came from -- same discipline as every analysis module already
in this repository (STORY-007's compute_latency_stats, STORY-009's
report builder): reused, never duplicated per caller.

No confidence field exists here, deliberately -- not defaulted to
None, simply absent. ADR-0001 ("no LLM in the decision path") and
the point of a deterministic strategy engine is undermined by a
field that invites a plausible-sounding score with no statistical
basis behind it. If a real, validated confidence measure is ever
justified, that is a deliberate spec change with its own review, not
a field sitting here waiting to be populated.

Story: stories/STORY-011-signal-schema-and-execution-mode.md
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from edgelab.signals.execution_mode import ExecutionMode

DIRECTIONS = ("LONG", "SHORT", "EXIT")


class InvalidSignalError(ValueError):
    """Raised when a Signal's own fields are internally inconsistent."""


@dataclass(frozen=True)
class EntryRange:
    min: float
    max: float

    def __post_init__(self) -> None:
        if self.min > self.max:
            raise InvalidSignalError(
                f"entry_range.min ({self.min}) must be <= entry_range.max ({self.max})"
            )


@dataclass(frozen=True)
class Signal:
    symbol: str
    direction: str  # one of DIRECTIONS
    signal_time: str  # ISO-8601 UTC -- when the strategy fired
    data_time: str  # the known_at boundary of the last input used
    entry_range: EntryRange
    invalidation: float
    strategy_id: str
    strategy_version: str
    execution_mode: ExecutionMode
    target: Optional[float] = None

    def __post_init__(self) -> None:
        if self.direction not in DIRECTIONS:
            raise InvalidSignalError(
                f"direction must be one of {DIRECTIONS}, got {self.direction!r}"
            )

    def signal_identity(self) -> Tuple[str, str, str, str, str]:
        """The tuple a future signal store dedups on -- (strategy_id,
        strategy_version, symbol, direction, signal_time). Same
        pattern as event_store.py's (source, source_id, type): a
        real-field tuple, not an invented ID. Two signals that differ
        only in, say, target or invalidation are still the same
        signal for dedup purposes -- what fired, for whom, when.
        """
        return (self.strategy_id, self.strategy_version, self.symbol, self.direction, self.signal_time)
