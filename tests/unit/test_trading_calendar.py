"""Unit tests for src/edgelab/calendar/trading_calendar.py.

Backed by pandas_market_calendars' real NYSE calendar -- no network
call (holidays are computed locally by the library), and no
hand-rolled weekday approximation to keep in sync ourselves.
"""

from __future__ import annotations

import pytest

from edgelab.calendar import trading_calendar as tc


def test_is_trading_day_true_for_ordinary_weekday():
    assert tc.is_trading_day("2026-09-21") is True  # a Monday


def test_is_trading_day_false_for_weekend():
    assert tc.is_trading_day("2026-09-19") is False  # Saturday
    assert tc.is_trading_day("2026-09-20") is False  # Sunday


def test_is_trading_day_false_for_thanksgiving_holiday():
    # Thanksgiving 2026 is Thursday 2026-11-26.
    assert tc.is_trading_day("2026-11-26") is False


def test_is_trading_day_true_on_black_friday_half_day():
    # The day after Thanksgiving is a half day, but still a trading day.
    assert tc.is_trading_day("2026-11-27") is True


def test_next_trading_day_skips_weekend():
    assert tc.next_trading_day("2026-09-18") == "2026-09-21"  # Fri -> Mon


def test_next_trading_day_skips_thanksgiving_holiday_cluster():
    # Wed before Thanksgiving -> the holiday (Thu) is skipped -> Fri (half day, still valid).
    assert tc.next_trading_day("2026-11-25") == "2026-11-27"


def test_next_trading_day_is_strictly_after_input_even_if_input_is_a_trading_day():
    assert tc.next_trading_day("2026-09-21") == "2026-09-22"


@pytest.mark.parametrize(
    "utc_timestamp,expected_session_date,label",
    [
        ("2026-09-21T12:00:00Z", "2026-09-21", "pre-open (08:00 ET on a Monday)"),
        ("2026-09-21T15:00:00Z", "2026-09-21", "intraday (11:00 ET)"),
        ("2026-09-21T21:00:00Z", "2026-09-22", "post-close (17:00 ET)"),
        ("2026-09-19T12:00:00Z", "2026-09-21", "Saturday -> next trading day (Monday)"),
        ("2026-11-26T12:00:00Z", "2026-11-27", "Thanksgiving -> next trading day"),
    ],
)
def test_compute_session_date_mapping_table(utc_timestamp, expected_session_date, label):
    assert tc.compute_session_date(utc_timestamp) == expected_session_date, label


def test_compute_session_date_exactly_at_market_open_is_same_day():
    # 09:30 ET on a September weekday (EDT, UTC-4) = 13:30 UTC.
    assert tc.compute_session_date("2026-09-21T13:30:00Z") == "2026-09-21"


def test_compute_session_date_exactly_at_market_close_rolls_to_next_day():
    # 16:00 ET (EDT, UTC-4) = 20:00 UTC -- the table's ">16:00" boundary
    # is treated as inclusive-of-close-time-itself here (< close is
    # "still open," so exactly close time rolls forward).
    assert tc.compute_session_date("2026-09-21T20:00:00Z") == "2026-09-22"


def test_compute_session_date_handles_dst_transition_correctly():
    # 2026-11-01 is the Sunday before the US falls back to EST
    # (first Sunday in November); 2026-11-02 (Monday) is already EST
    # (UTC-5). 14:00 UTC on 2026-11-02 = 09:00 ET -- before open.
    assert tc.compute_session_date("2026-11-02T14:00:00Z") == "2026-11-02"
    # 14:35 UTC the same day = 09:35 ET -- after open, intraday, same day.
    assert tc.compute_session_date("2026-11-02T14:35:00Z") == "2026-11-02"
