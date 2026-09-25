"""Unit tests for src/edgelab/collectors/prices_daily.py.

No test here touches yfinance or the network -- HistoryFetcher is
always a fake, per STORY-004's acceptance criteria.
"""

from __future__ import annotations

import pandas as pd
import pytest

from edgelab.collectors import prices_daily as pd_collector


def make_history_dataframe():
    """A small, realistic yfinance-shaped DataFrame: a DatetimeIndex
    named 'Date' and Open/High/Low/Close/'Adj Close'/Volume columns
    (auto_adjust=False, actions=False), including one row where
    adj_close differs from close (a split/dividend adjustment).
    """
    index = pd.DatetimeIndex(["2026-09-18", "2026-09-19", "2026-09-20"], name="Date")
    return pd.DataFrame(
        {
            "Open": [224.0, 225.5, 226.0],
            "High": [226.0, 227.0, 228.5],
            "Low": [223.0, 224.5, 224.1],
            "Close": [225.5, 226.2, 227.0],
            "Adj Close": [225.0, 225.7, 227.0],  # earlier rows adjusted for a later dividend
            "Volume": [50_000_000, 48_000_000, 54_000_000],
        },
        index=index,
    )


class FakeHistoryFetcher:
    def __init__(self, result=None, exception=None):
        self.result = result
        self.exception = exception
        self.calls = []

    def fetch(self, ticker, *, start, end):
        self.calls.append((ticker, start, end))
        if self.exception is not None:
            raise self.exception
        return self.result


def test_dataframe_to_csv_bytes_shape():
    payload = pd_collector._dataframe_to_csv_bytes(make_history_dataframe())
    text = payload.decode("utf-8")
    header = text.splitlines()[0]
    assert header == "date,Open,High,Low,Close,Adj Close,Volume"
    assert "2026-09-18" in text
    assert "2026-09-20" in text


def test_collect_prices_daily_writes_raw_snapshot(tmp_path):
    fetcher = FakeHistoryFetcher(result=make_history_dataframe())
    snapshot = pd_collector.collect_prices_daily(
        "AAPL",
        start="2026-09-18",
        end="2026-09-21",
        history_fetcher=fetcher,
        db_path=tmp_path / "raw.sqlite3",
        data_dir=tmp_path / "data",
        now=lambda: "2026-09-21T21:05:00Z",
    )
    assert snapshot.source == "prices_daily"
    assert fetcher.calls == [("AAPL", "2026-09-18", "2026-09-21")]


def test_collect_prices_daily_raises_on_fetch_exception(tmp_path):
    fetcher = FakeHistoryFetcher(exception=ValueError("YFRateLimitError: 429"))
    with pytest.raises(pd_collector.PricesDailyError):
        pd_collector.collect_prices_daily(
            "AAPL",
            start="2026-09-18",
            end="2026-09-21",
            history_fetcher=fetcher,
            db_path=tmp_path / "raw.sqlite3",
            data_dir=tmp_path / "data",
        )


def test_collect_prices_daily_raises_on_empty_result(tmp_path):
    fetcher = FakeHistoryFetcher(result=pd.DataFrame())
    with pytest.raises(pd_collector.PricesDailyError):
        pd_collector.collect_prices_daily(
            "DELISTEDXYZ",
            start="2026-09-18",
            end="2026-09-21",
            history_fetcher=fetcher,
            db_path=tmp_path / "raw.sqlite3",
            data_dir=tmp_path / "data",
        )


def test_parse_price_csv_happy_path():
    payload = pd_collector._dataframe_to_csv_bytes(make_history_dataframe())
    rows = pd_collector.parse_price_csv(payload)

    assert [row.date for row in rows] == ["2026-09-18", "2026-09-19", "2026-09-20"]
    first = rows[0]
    assert first.close == 225.5
    assert first.adj_close == 225.0
    assert first.close != first.adj_close  # the adjustment this fixture is testing for
    assert first.volume == 50_000_000


def test_parse_price_csv_skips_single_malformed_row_but_keeps_others():
    text = (
        "date,Open,High,Low,Close,Adj Close,Volume\n"
        "2026-09-18,224.0,226.0,223.0,225.5,225.0,50000000\n"
        "2026-09-19,not-a-number,227.0,224.5,226.2,225.7,48000000\n"
        "2026-09-20,226.0,228.5,224.1,227.0,227.0,54000000\n"
    )
    rows = pd_collector.parse_price_csv(text.encode("utf-8"))
    assert [row.date for row in rows] == ["2026-09-18", "2026-09-20"]


def test_parse_price_csv_raises_when_every_row_fails():
    # A plausible schema-drift scenario: "Adj Close" got renamed.
    text = (
        "date,Open,High,Low,Close,Adjusted Close,Volume\n"
        "2026-09-18,224.0,226.0,223.0,225.5,225.0,50000000\n"
    )
    with pytest.raises(pd_collector.PricesDailyError):
        pd_collector.parse_price_csv(text.encode("utf-8"))


def test_parse_price_csv_empty_input_returns_empty_list_not_error():
    text = "date,Open,High,Low,Close,Adj Close,Volume\n"
    assert pd_collector.parse_price_csv(text.encode("utf-8")) == []
