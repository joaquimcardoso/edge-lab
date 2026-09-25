"""System-level test for the prices_daily collector + normaliser (STORY-004).

Runs collect_prices_daily against a fake HistoryFetcher, then
normalise_prices_daily_snapshot against the real STORY-001 raw store,
verifying the result reads back correctly through the real price
store and that re-normalising is idempotent. No network call.

Regression fixture set: still vacuous -- no experiment is FROZEN yet.
"""

from __future__ import annotations

import pandas as pd

from edgelab.collectors.prices_daily import collect_prices_daily
from edgelab.normalisers.prices_daily import normalise_prices_daily_snapshot
from edgelab.storage.price_store import read_price_bars_for_security
from tests.unit.test_prices_daily_collector import FakeHistoryFetcher, make_history_dataframe


def test_collect_and_normalise_end_to_end(tmp_path):
    raw_db_path = tmp_path / "raw.sqlite3"
    raw_data_dir = tmp_path / "raw_data"
    price_db_path = tmp_path / "prices.sqlite3"

    fetcher = FakeHistoryFetcher(result=make_history_dataframe())
    snapshot = collect_prices_daily(
        "AAPL",
        start="2026-09-18",
        end="2026-09-21",
        history_fetcher=fetcher,
        db_path=raw_db_path,
        data_dir=raw_data_dir,
        now=lambda: "2026-09-21T21:05:00Z",
    )

    result = normalise_prices_daily_snapshot(
        snapshot.id,
        "0000320193",
        raw_db_path=raw_db_path,
        price_db_path=price_db_path,
    )

    assert len(result.bars_written) == 3
    bars = read_price_bars_for_security("0000320193", db_path=price_db_path)
    assert [bar.date for bar in bars] == ["2026-09-18", "2026-09-19", "2026-09-20"]
    assert all(bar.snapshot_id == snapshot.id for bar in bars)
    # Raw close and adjusted close are genuinely distinct columns.
    assert bars[0].close == 225.5
    assert bars[0].adj_close == 225.0


def test_normalise_prices_daily_snapshot_is_idempotent(tmp_path):
    raw_db_path = tmp_path / "raw.sqlite3"
    raw_data_dir = tmp_path / "raw_data"
    price_db_path = tmp_path / "prices.sqlite3"

    fetcher = FakeHistoryFetcher(result=make_history_dataframe())
    snapshot = collect_prices_daily(
        "AAPL",
        start="2026-09-18",
        end="2026-09-21",
        history_fetcher=fetcher,
        db_path=raw_db_path,
        data_dir=raw_data_dir,
    )

    first = normalise_prices_daily_snapshot(
        snapshot.id, "0000320193", raw_db_path=raw_db_path, price_db_path=price_db_path
    )
    second = normalise_prices_daily_snapshot(
        snapshot.id, "0000320193", raw_db_path=raw_db_path, price_db_path=price_db_path
    )

    assert [b.price_id for b in first.bars_written] == [b.price_id for b in second.bars_written]
    assert len(read_price_bars_for_security("0000320193", db_path=price_db_path)) == 3
