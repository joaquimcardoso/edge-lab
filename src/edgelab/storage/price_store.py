"""Daily price store.

See docs/03-architecture.md#core-data-model's `price_daily` table.
Like event_store.py, writes here are deduplicated (on `security_id,
date`) rather than append-only in the raw_snapshot sense -- a dedup
hit returns the existing row unchanged, never updates it, and there
is no update function exposed.

Story: stories/STORY-004-prices-daily-collector.md
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List, Union

PathLike = Union[str, "Path"]


@dataclass(frozen=True)
class PriceBar:
    security_id: str
    date: str  # YYYY-MM-DD
    open: float
    high: float
    low: float
    close: float
    adj_close: float
    volume: int
    snapshot_id: int
    price_id: "int | None" = None


_SCHEMA = """
CREATE TABLE IF NOT EXISTS price_daily (
    price_id INTEGER PRIMARY KEY AUTOINCREMENT,
    security_id TEXT NOT NULL,
    date TEXT NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    adj_close REAL NOT NULL,
    volume INTEGER NOT NULL,
    snapshot_id INTEGER NOT NULL,
    UNIQUE(security_id, date)
);
"""

_COLUMNS = (
    "price_id, security_id, date, open, high, low, close, adj_close, volume, snapshot_id"
)


def _connect(db_path: PathLike) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute(_SCHEMA)
    conn.commit()
    return conn


def _row_to_bar(row) -> PriceBar:
    return PriceBar(
        price_id=row[0],
        security_id=row[1],
        date=row[2],
        open=row[3],
        high=row[4],
        low=row[5],
        close=row[6],
        adj_close=row[7],
        volume=row[8],
        snapshot_id=row[9],
    )


def write_price_bar(bar: PriceBar, *, db_path: PathLike) -> PriceBar:
    """Persist one day's OHLCV row, deduplicated on (security_id, date).

    A dedup hit returns the existing row unchanged -- never updates
    it and never creates a duplicate.
    """
    conn = _connect(db_path)
    try:
        existing = conn.execute(
            "SELECT price_id FROM price_daily WHERE security_id = ? AND date = ?",
            (bar.security_id, bar.date),
        ).fetchone()
        if existing is not None:
            return read_price_bar(existing[0], db_path=db_path)

        cur = conn.execute(
            "INSERT INTO price_daily "
            "(security_id, date, open, high, low, close, adj_close, volume, snapshot_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                bar.security_id,
                bar.date,
                bar.open,
                bar.high,
                bar.low,
                bar.close,
                bar.adj_close,
                bar.volume,
                bar.snapshot_id,
            ),
        )
        conn.commit()
        price_id = cur.lastrowid
    finally:
        conn.close()

    return PriceBar(
        price_id=price_id,
        security_id=bar.security_id,
        date=bar.date,
        open=bar.open,
        high=bar.high,
        low=bar.low,
        close=bar.close,
        adj_close=bar.adj_close,
        volume=bar.volume,
        snapshot_id=bar.snapshot_id,
    )


def read_price_bar(price_id: int, *, db_path: PathLike) -> PriceBar:
    conn = _connect(db_path)
    try:
        row = conn.execute(
            f"SELECT {_COLUMNS} FROM price_daily WHERE price_id = ?", (price_id,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise KeyError(f"no price_daily row with id={price_id}")
    return _row_to_bar(row)


def read_price_bars_for_security(security_id: str, *, db_path: PathLike) -> List[PriceBar]:
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            f"SELECT {_COLUMNS} FROM price_daily WHERE security_id = ? ORDER BY date",
            (security_id,),
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_bar(row) for row in rows]
