"""Unit tests for scripts/backfill_historical.py (STORY-014).

backfill_8k's per-CIK isolation and its "raw only, never normalises"
contract; backfill_prices' per-ticker isolation. No real network, no
real yfinance -- fakes throughout, same as every other collector test
in this repository.
"""

from __future__ import annotations

import pytest

import backfill_historical as bh

from edgelab.config import CollectorConfig
from tests.unit.test_edgar_8k import FakeHttpClient, FakeResponse, make_submissions_fixture
from tests.unit.test_edgar_8k_normaliser import make_header_text
from tests.unit.test_prices_daily_collector import FakeHistoryFetcher, make_history_dataframe


def _config(tmp_path) -> CollectorConfig:
    data_dir = tmp_path / "data"
    return CollectorConfig(
        sec_user_agent="edge-lab test contact@example.com",
        data_dir=data_dir,
        raw_db_path=data_dir / "raw.sqlite3",
        event_db_path=data_dir / "event.sqlite3",
        reports_dir=data_dir / "reports",
        universe_path=tmp_path / "universe.csv",
        log_dir=data_dir / "logs",
        price_db_path=data_dir / "price_daily.sqlite3",
    )


def test_backfill_8k_writes_raw_snapshots_and_never_normalises(tmp_path):
    config = _config(tmp_path)
    fixture = make_submissions_fixture()
    submissions_url = "https://data.sec.gov/submissions/CIK0000320193.json"
    responses = {submissions_url: FakeResponse(200, json_body=fixture)}
    for acc, acceptance in [
        ("0000320193-26-000050", "20260920163211"),
        ("0000320193-26-000053", "20260923090100"),
        ("0000320193-26-000054", "20260924074500"),
    ]:
        url = f"https://www.sec.gov/Archives/edgar/data/320193/{acc}.txt"
        responses[url] = FakeResponse(
            200, content=make_header_text(accession=acc, acceptance=acceptance)
        )
    client = FakeHttpClient(responses)

    summary = bh.backfill_8k([("AAPL", "320193")], http_client=client, config=config)

    assert len(summary.outcomes) == 1
    outcome = summary.outcomes[0]
    assert outcome.snapshots_written == 3
    # The whole point of this function: raw snapshots exist, but no
    # events were ever written -- proven against the real event store,
    # not just the in-memory outcome.
    assert outcome.events_written == 0
    assert summary.total_events == 0
    # normalise_snapshot() is what creates event.db in the first
    # place -- it never existing at all is direct proof this function
    # never called it, not just that the in-memory summary says zero.
    assert not config.event_db_path.exists()


def test_backfill_8k_isolates_one_ciks_failure_from_another(tmp_path):
    config = _config(tmp_path)
    good_fixture = make_submissions_fixture()
    good_url = "https://data.sec.gov/submissions/CIK0000320193.json"
    responses = {good_url: FakeResponse(200, json_body=good_fixture)}
    for acc, acceptance in [
        ("0000320193-26-000050", "20260920163211"),
        ("0000320193-26-000053", "20260923090100"),
        ("0000320193-26-000054", "20260924074500"),
    ]:
        url = f"https://www.sec.gov/Archives/edgar/data/320193/{acc}.txt"
        responses[url] = FakeResponse(
            200, content=make_header_text(accession=acc, acceptance=acceptance)
        )
    # No response registered for the second CIK's submissions URL --
    # FakeHttpClient.get raises KeyError for it, simulating a real
    # network/SEC failure for that one company only.
    client = FakeHttpClient(responses)

    summary = bh.backfill_8k(
        [("AAPL", "320193"), ("BROKEN", "999999")], http_client=client, config=config
    )

    assert len(summary.outcomes) == 2
    good, broken = summary.outcomes
    assert good.ticker == "AAPL"
    assert good.snapshots_written == 3
    assert good.failures == ()
    assert broken.ticker == "BROKEN"
    assert broken.snapshots_written == 0
    assert len(broken.failures) == 1
    assert summary.total_snapshots == 3
    assert summary.ciks_with_failures == ("999999",)


class _PerTickerHistoryFetcher:
    """Different behaviour per ticker -- FakeHistoryFetcher (reused
    elsewhere in this repository) only supports one fixed
    result/exception for every call, which can't express "AAPL
    succeeds, BROKEN fails" in a single fetcher instance.
    """

    def __init__(self, by_ticker):
        self._by_ticker = by_ticker
        self.calls = []

    def fetch(self, ticker, *, start, end):
        self.calls.append((ticker, start, end))
        behaviour = self._by_ticker[ticker]
        if isinstance(behaviour, Exception):
            raise behaviour
        return behaviour


def test_backfill_prices_writes_bars_and_isolates_one_tickers_failure(tmp_path):
    from edgelab.collectors.prices_daily import PricesDailyError
    from edgelab.storage.price_store import read_price_bars_for_security

    config = _config(tmp_path)
    fetcher = _PerTickerHistoryFetcher(
        {
            "AAPL": make_history_dataframe(),
            "BROKEN": PricesDailyError("yfinance fetch failed for BROKEN"),
        }
    )

    summary = bh.backfill_prices(
        [("AAPL", "0000320193"), ("BROKEN", "0000999999")],
        history_fetcher=fetcher,
        config=config,
        start="2026-09-18",
        end="2026-09-21",
    )

    assert len(summary.outcomes) == 2
    good, broken = summary.outcomes
    assert good.ticker == "AAPL"
    assert good.bars_written == 3
    assert good.failure is None
    assert broken.ticker == "BROKEN"
    assert broken.bars_written == 0
    assert broken.failure is not None
    assert summary.total_bars == 3
    assert summary.tickers_with_failures == ("BROKEN",)

    bars = read_price_bars_for_security("0000320193", db_path=config.price_db_path)
    assert [b.date for b in bars] == ["2026-09-18", "2026-09-19", "2026-09-20"]
    # The failed ticker never wrote anything to the price store.
    assert read_price_bars_for_security("0000999999", db_path=config.price_db_path) == []


def test_append_price_failure_log_records_only_failures(tmp_path):
    config = _config(tmp_path)
    summary = bh.PriceRunSummary(
        outcomes=(
            bh.PriceOutcome(ticker="AAPL", cik="0000320193", bars_written=3),
            bh.PriceOutcome(
                ticker="BROKEN", cik="0000999999", bars_written=0,
                failure=bh.PriceFailure(ticker="BROKEN", reason="yfinance fetch failed"),
            ),
        )
    )

    written = bh.append_price_failure_log(
        summary, log_dir=config.log_dir, now=lambda: "2026-09-25T12:00:00Z"
    )

    assert written == 1
    log_path = config.log_dir / "price_backfill_failures.jsonl"
    lines = log_path.read_text().splitlines()
    assert len(lines) == 1
    assert "BROKEN" in lines[0]
    assert "AAPL" not in lines[0]
