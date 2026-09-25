"""NYSE trading-calendar integration.

Backs is_trading_day / next_trading_day / compute_session_date with a
real, maintained calendar library (pandas_market_calendars, which
wraps exchange_calendars) rather than a hand-rolled weekday check --
01-point-in-time-rules.md §3 explicitly warns against exactly that
kind of shortcut ("never hard-code a Lisbon-New York offset"), and a
naive approximation here would silently mis-date events around every
US market holiday.

compute_session_date implements §3's mapping table exactly:

| Event time (ET)      | session_date      |
|-----------------------|-------------------|
| Before 09:30           | Same day           |
| 09:30-16:00 (intraday) | Same day           |
| After 16:00            | Next trading day   |
| Weekend / holiday      | Next trading day   |

The 09:30-16:00 "excluded from V1 experiments" note in that table is
an experiment-level filter on *using* an intraday session_date, not
something this function enforces -- it still returns the correct
same-day session_date; a caller building a V1 experiment is
responsible for excluding intraday events itself.

EASTERN, MARKET_OPEN and MARKET_CLOSE are exported deliberately (not
underscore-prefixed): src/edgelab/audit/feed_latency.py (STORY-007)
reuses them directly rather than re-deriving its own ET-conversion
and open-time logic -- one definition of "market open," not two.

Story: stories/STORY-005-exchange-calendar.md
"""

from __future__ import annotations

from datetime import date as date_cls
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas_market_calendars as mcal

_NYSE = mcal.get_calendar("NYSE")
EASTERN = ZoneInfo("America/New_York")
MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)
_MAX_HOLIDAY_SEARCH_DAYS = 14


class TradingCalendarError(RuntimeError):
    """Raised when a trading day can't be resolved within a sane search
    window -- almost certainly a bug (an all-holiday span this long
    does not exist for NYSE), not a legitimate "no answer."
    """


def is_trading_day(date: str) -> bool:
    """True if `date` (YYYY-MM-DD) is a regular or half NYSE session."""
    valid_days = _NYSE.valid_days(start_date=date, end_date=date)
    return len(valid_days) == 1


def next_trading_day(date: str) -> str:
    """First NYSE trading day strictly after `date` (YYYY-MM-DD)."""
    start = date_cls.fromisoformat(date)
    for offset in range(1, _MAX_HOLIDAY_SEARCH_DAYS + 1):
        candidate = (start + timedelta(days=offset)).isoformat()
        if is_trading_day(candidate):
            return candidate
    raise TradingCalendarError(
        f"no NYSE trading day found within {_MAX_HOLIDAY_SEARCH_DAYS} days after {date}"
    )


def compute_session_date(event_time_utc: str) -> str:
    """Map a UTC ISO-8601 event timestamp to the first regular session
    that could react to it, per 01-point-in-time-rules.md §3.
    """
    dt_utc = datetime.fromisoformat(event_time_utc.replace("Z", "+00:00"))
    dt_et = dt_utc.astimezone(EASTERN)
    event_date = dt_et.date().isoformat()

    if not is_trading_day(event_date):
        return next_trading_day(event_date)

    if dt_et.time() < MARKET_OPEN:
        return event_date
    if dt_et.time() < MARKET_CLOSE:
        return event_date
    return next_trading_day(event_date)
