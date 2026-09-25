"""Unit tests for scripts/collect_premarket_8k.py (STORY-008).

run()'s three distinct outcomes (success, per-CIK collection
failure, zero-filings-today) and load_universe()'s validation, all
against fakes -- no real network, no real systemd. Reuses the
existing edgar_8k fixture machinery rather than inventing a second
one.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

import collect_premarket_8k as cp

from edgelab.config import CollectorConfig
from tests.unit.test_edgar_8k import FakeHttpClient, FakeResponse, make_submissions_fixture
from tests.unit.test_edgar_8k_normaliser import make_header_text


def _config(tmp_path) -> CollectorConfig:
    data_dir = tmp_path / "data"
    return CollectorConfig(
        sec_user_agent="edge-lab test contact@example.com",
        data_dir=data_dir,
        raw_db_path=data_dir / "raw.sqlite3",
        event_db_path=data_dir / "event.sqlite3",
        reports_dir=data_dir / "reports",
        universe_path=tmp_path / "universe.csv",
    )


def test_run_success_outcome_collects_and_normalises(tmp_path):
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

    summary = cp.run([("AAPL", "320193")], http_client=client, config=config)

    assert len(summary.outcomes) == 1
    outcome = summary.outcomes[0]
    assert outcome.ticker == "AAPL"
    assert outcome.snapshots_written == 3
    assert outcome.events_written == 3  # 1 mapped item per filing x 3 filings
    assert outcome.failures == ()
    assert summary.ciks_with_failures == ()


def test_run_records_per_cik_collection_failure_without_stopping_others(tmp_path):
    config = _config(tmp_path)

    class RaisingHttpClient:
        def get(self, url, *, headers, timeout):
            raise ConnectionError("simulated network outage")

    good_fixture = make_submissions_fixture()
    good_url = "https://data.sec.gov/submissions/CIK0000789019.json"
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

    class MixedHttpClient:
        """Fails only for the first CIK's submissions call, succeeds for the second."""

        def __init__(self, ok_responses):
            self.ok_responses = ok_responses

        def get(self, url, *, headers, timeout):
            if url == "https://data.sec.gov/submissions/CIK0000320193.json":
                raise ConnectionError("simulated network outage")
            return self.ok_responses[url]

    client = MixedHttpClient(responses)

    summary = cp.run(
        [("BADCO", "320193"), ("MSFT", "789019")], http_client=client, config=config
    )

    assert len(summary.outcomes) == 2
    badco, msft = summary.outcomes
    assert badco.ticker == "BADCO"
    assert badco.snapshots_written == 0
    assert len(badco.failures) == 1
    assert "simulated network outage" in badco.failures[0].reason

    assert msft.ticker == "MSFT"
    assert msft.snapshots_written == 3
    assert msft.failures == ()

    assert summary.ciks_with_failures == ("320193",)


def test_run_zero_filings_today_is_not_a_failure(tmp_path):
    config = _config(tmp_path)
    empty_fixture = {"cik": 1018724, "filings": {"recent": {"form": []}}}
    url = "https://data.sec.gov/submissions/CIK0001018724.json"
    client = FakeHttpClient({url: FakeResponse(200, json_body=empty_fixture)})

    summary = cp.run([("AMZN", "1018724")], http_client=client, config=config)

    outcome = summary.outcomes[0]
    assert outcome.snapshots_written == 0
    assert outcome.events_written == 0
    assert outcome.failures == ()
    assert summary.ciks_with_failures == ()


def test_load_universe_reads_ticker_cik_pairs(tmp_path):
    path = tmp_path / "universe.csv"
    with path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["ticker", "cik"])
        writer.writerow(["AAPL", "320193"])
        writer.writerow(["MSFT", "789019"])

    pairs = cp.load_universe(path)
    assert pairs == [("AAPL", "320193"), ("MSFT", "789019")]


def test_load_universe_raises_for_missing_file(tmp_path):
    with pytest.raises(cp.UniverseError, match="not found"):
        cp.load_universe(tmp_path / "does_not_exist.csv")


def test_load_universe_raises_for_header_with_no_data_rows(tmp_path):
    path = tmp_path / "universe.csv"
    path.write_text("ticker,cik\n")
    with pytest.raises(cp.UniverseError, match="no data rows"):
        cp.load_universe(path)


def test_load_universe_raises_for_wrong_header(tmp_path):
    path = tmp_path / "universe.csv"
    path.write_text("symbol,id\nAAPL,320193\n")
    with pytest.raises(cp.UniverseError, match="must have a header"):
        cp.load_universe(path)
