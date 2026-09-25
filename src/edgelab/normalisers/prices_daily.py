"""`prices_daily` normaliser: raw CSV snapshot -> typed price_daily rows.

Story: stories/STORY-004-prices-daily-collector.md
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple, Union
from pathlib import Path

from edgelab.collectors.prices_daily import parse_price_csv
from edgelab.storage.price_store import PriceBar, write_price_bar
from edgelab.storage.raw_snapshot import read_raw_snapshot

PathLike = Union[str, "Path"]


@dataclass(frozen=True)
class PricesDailyNormaliseResult:
    bars_written: Tuple[PriceBar, ...]


def normalise_prices_daily_snapshot(
    snapshot_id: int,
    security_id: str,
    *,
    raw_db_path: PathLike,
    price_db_path: PathLike,
) -> PricesDailyNormaliseResult:
    """Read one prices_daily raw snapshot, parse it, and persist each
    row to the price store -- idempotently: re-running this over the
    same snapshot (or an overlapping date range from a separate
    collection run) never creates duplicate rows, via price_store's
    own dedup on (security_id, date).
    """
    _snapshot, payload = read_raw_snapshot(snapshot_id, db_path=raw_db_path)
    rows = parse_price_csv(payload)

    written = tuple(
        write_price_bar(
            PriceBar(
                security_id=security_id,
                date=row.date,
                open=row.open,
                high=row.high,
                low=row.low,
                close=row.close,
                adj_close=row.adj_close,
                volume=row.volume,
                snapshot_id=snapshot_id,
            ),
            db_path=price_db_path,
        )
        for row in rows
    )
    return PricesDailyNormaliseResult(bars_written=written)
