"""Feed-latency audit harness -- Gate 0 for EXP-002.

Reads already-collected events (their published_at/first_seen_at,
populated by src/edgelab/normalisers/edgar_8k.py) and reports, per
source, the full first_seen_at - published_at lag distribution and
the share of pre-market events seen before 09:30 ET -- then applies
Gate 0's exact pass bar (docs/experiments/daily/EXP-002-intraday-continuation.md):
>= 80% seen before open AND median lag <= 30 seconds, both required.

This module does not run the 2-3 week live polling campaign Gate 0
describes -- that is an operational/scheduling activity on the Pi
(docs/04-infrastructure.md). It is the analysis that campaign's
collected data feeds into.

Story: stories/STORY-007-feed-latency-audit.md
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Sequence

from edgelab.calendar.trading_calendar import EASTERN, MARKET_OPEN, is_trading_day
from edgelab.storage.event_store import Event

PASS_SHARE_BEFORE_OPEN = 0.80
PASS_MEDIAN_LAG_SECONDS = 30.0


class FeedLatencyAuditError(RuntimeError):
    """Raised when there is nothing usable to audit -- zero matching
    pre-market events. Never silently reported as a PASS or a FAIL;
    an empty result is not a verdict.
    """


def is_premarket_event(published_at: str) -> bool:
    """True only if published_at's America/New_York time is before
    09:30 ET on a genuine NYSE trading day -- reuses STORY-005's
    calendar rather than a second hand-rolled weekday/time check.
    """
    dt_utc = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    dt_et = dt_utc.astimezone(EASTERN)
    if not is_trading_day(dt_et.date().isoformat()):
        return False
    return dt_et.time() < MARKET_OPEN


def _seen_before_same_day_open(published_at: str, first_seen_at: str) -> bool:
    """True only if first_seen_at is before 09:30 ET on the SAME
    calendar day as published_at -- not merely "before 09:30 ET on
    whatever day it happened to be seen."

    Caught during review: reusing is_premarket_event(first_seen_at)
    for this check would wrongly count a filing missed all of Monday
    and only picked up at, say, 06:00 ET Tuesday as "seen before
    open," because 06:00 ET Tuesday genuinely is before Tuesday's own
    09:30 -- but Tuesday's open is not the open this event's
    pre-market visibility is being measured against.
    """
    published_et_date = (
        datetime.fromisoformat(published_at.replace("Z", "+00:00")).astimezone(EASTERN).date()
    )
    seen_et = datetime.fromisoformat(first_seen_at.replace("Z", "+00:00")).astimezone(EASTERN)
    return seen_et.date() == published_et_date and seen_et.time() < MARKET_OPEN


def lag_seconds(published_at: str, first_seen_at: str) -> float:
    published = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    seen = datetime.fromisoformat(first_seen_at.replace("Z", "+00:00"))
    return (seen - published).total_seconds()


def _percentile(sorted_values: Sequence[float], pct: float) -> float:
    """Linear-interpolation percentile (the same method as numpy's and
    Excel's default), over an already-sorted sequence. pct in [0, 100].
    """
    if not sorted_values:
        raise ValueError("cannot take a percentile of an empty sequence")
    if len(sorted_values) == 1:
        return sorted_values[0]

    rank = (pct / 100.0) * (len(sorted_values) - 1)
    lower_index = math.floor(rank)
    upper_index = math.ceil(rank)
    if lower_index == upper_index:
        return sorted_values[lower_index]
    fraction = rank - lower_index
    return sorted_values[lower_index] + fraction * (
        sorted_values[upper_index] - sorted_values[lower_index]
    )


@dataclass(frozen=True)
class LatencyStats:
    source: str
    event_type: Optional[str]
    total_premarket_events: int
    seen_before_open_count: int
    share_seen_before_open: float
    lag_seconds_p50: float
    lag_seconds_p90: float
    lag_seconds_p95: float
    passed: bool


def compute_latency_stats(
    events: List[Event], *, source: str, event_type: Optional[str] = None
) -> LatencyStats:
    """Gate 0's audit for one source (optionally filtered further to
    one event type), over a set of already-collected events.

    Raises FeedLatencyAuditError if no event in `events` is both a
    match for (source, event_type) and pre-market -- there is nothing
    to compute a verdict from, and reporting a default PASS or FAIL
    in that case would misrepresent "no data" as a real result.
    """
    candidates = [e for e in events if e.source == source]
    if event_type is not None:
        candidates = [e for e in candidates if e.type == event_type]
    premarket = [e for e in candidates if e.published_at and is_premarket_event(e.published_at)]

    if not premarket:
        raise FeedLatencyAuditError(
            f"no pre-market events found for source={source!r} event_type={event_type!r} "
            "-- cannot compute a Gate 0 verdict from zero observations"
        )

    lags = sorted(lag_seconds(e.published_at, e.first_seen_at) for e in premarket)
    seen_before_open = [
        e for e in premarket if _seen_before_same_day_open(e.published_at, e.first_seen_at)
    ]

    total = len(premarket)
    seen_count = len(seen_before_open)
    share = seen_count / total
    p50 = _percentile(lags, 50)
    p90 = _percentile(lags, 90)
    p95 = _percentile(lags, 95)

    passed = share >= PASS_SHARE_BEFORE_OPEN and p50 <= PASS_MEDIAN_LAG_SECONDS

    return LatencyStats(
        source=source,
        event_type=event_type,
        total_premarket_events=total,
        seen_before_open_count=seen_count,
        share_seen_before_open=share,
        lag_seconds_p50=p50,
        lag_seconds_p90=p90,
        lag_seconds_p95=p95,
        passed=passed,
    )


def render_report(stats_list: List[LatencyStats]) -> str:
    """Markdown table, one row per (source, event_type), matching this
    repository's existing Markdown-report convention
    (docs/03-architecture.md's Reporter component).
    """
    lines = [
        "| Source | Event type | N (pre-market) | Share before open | p50 lag (s) | p90 lag (s) | p95 lag (s) | Gate 0 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for stats in stats_list:
        verdict = "PASS" if stats.passed else "FAIL"
        event_type_label = stats.event_type or "(all)"
        lines.append(
            f"| {stats.source} | {event_type_label} | {stats.total_premarket_events} | "
            f"{stats.share_seen_before_open:.0%} | {stats.lag_seconds_p50:.1f} | "
            f"{stats.lag_seconds_p90:.1f} | {stats.lag_seconds_p95:.1f} | {verdict} |"
        )
    return "\n".join(lines)
