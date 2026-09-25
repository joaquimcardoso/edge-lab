"""System-level test for scripts/backfill_historical.py (STORY-014).

backfill_prices end-to-end against a fake HistoryFetcher, through the
real raw store and real price store in a temp dir -- proving
collect_prices_daily + normalise_prices_daily_snapshot actually
compose through this entrypoint, not just that each piece works in
isolation.
"""

from __future__ import annotations

import backfill_historical as bh

from edgelab.config import CollectorConfig
from edgelab.storage.price_store import read_price_bars_for_security
from tests.unit.test_prices_daily_collector import FakeHistoryFetcher, make_history_dataframe


def test_backfill_prices_end_to_end(tmp_path):
    data_dir = tmp_path / "data"
    config = CollectorConfig(
        sec_user_agent="edge-lab system test contact@example.com",
        data_dir=data_dir,
        raw_db_path=data_dir / "raw.sqlite3",
        event_db_path=data_dir / "event.sqlite3",
        reports_dir=data_dir / "reports",
        universe_path=tmp_path / "universe.csv",
        log_dir=data_dir / "logs",
        price_db_path=data_dir / "price_daily.sqlite3",
    )
    config.data_dir.mkdir(parents=True)

    fetcher = FakeHistoryFetcher(result=make_history_dataframe())

    summary = bh.backfill_prices(
        [("AAPL", "0000320193")],
        history_fetcher=fetcher,
        config=config,
        start="2026-09-18",
        end="2026-09-21",
    )

    assert summary.total_bars == 3
    assert summary.tickers_with_failures == ()

    # The price store really exists on disk and is readable back
    # through its own real module, not just asserted against the
    # in-memory summary.
    bars = read_price_bars_for_security("0000320193", db_path=config.price_db_path)
    assert [b.date for b in bars] == ["2026-09-18", "2026-09-19", "2026-09-20"]
    assert bars[0].close == 225.5
    assert bars[0].adj_close == 225.0

    # Re-running the same backfill over an overlapping range must
    # never duplicate rows -- price_store's own dedup on
    # (security_id, date), exercised through this entrypoint.
    second = bh.backfill_prices(
        [("AAPL", "0000320193")],
        history_fetcher=FakeHistoryFetcher(result=make_history_dataframe()),
        config=config,
        start="2026-09-18",
        end="2026-09-21",
    )
    assert second.total_bars == 3
    assert len(read_price_bars_for_security("0000320193", db_path=config.price_db_path)) == 3
