"""Strategy interface -- the shape any future strategy implements,
regardless of which ExecutionMode calls it.

MarketState is intentionally minimal: a real strategy's own frozen
spec (docs/experiments/...) will define exactly what data it reads,
per that spec's own point-in-time rules. This story only fixes the
one property every mode depends on -- a hard as-of boundary -- so
that boundary can never be an afterthought bolted on per-strategy.

No concrete strategy is wired to this Protocol yet. Gate 0 has not
run; no experiment has reached ACCEPT (docs/05-experiment-protocol.md).
Tests here use only a trivial stub, never a real strategy's logic.

Story: stories/STORY-011-signal-schema-and-execution-mode.md
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

from edgelab.signals.signal import Signal


@dataclass(frozen=True)
class MarketState:
    """Placeholder shape for what a strategy reads to decide.

    as_of is the known_at boundary: a Strategy.evaluate() call must
    never be given, or read, anything with known_at > as_of. Enforcing
    that for real data is the replay/backtest engine's job (not yet
    built -- see STORY-011's scope boundary); this dataclass only
    carries the boundary itself.
    """

    as_of: str


class Strategy(Protocol):
    strategy_id: str
    strategy_version: str

    def evaluate(self, market_state: MarketState) -> Optional[Signal]:
        """Return a Signal if this strategy's rules fire at
        market_state.as_of, or None (NO_SIGNAL) otherwise. Must be
        deterministic: the same market_state must always produce the
        same result (ADR-0001).
        """
        ...
