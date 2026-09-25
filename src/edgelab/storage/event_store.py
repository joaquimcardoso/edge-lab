"""Event store.

See docs/03-architecture.md#core-data-model's `event` table. Like
raw_snapshot.py, every write here is auditable back to raw evidence:
every row carries snapshot_id, the raw_snapshot it was derived from.

Unlike raw_snapshot.py this store is NOT append-only in the same
sense -- an (source, source_id, type) triple is deduplicated on
write, because re-running a normaliser over the same raw snapshot
must be idempotent (03-architecture.md's Normaliser responsibility:
"entity linking; dedup"). It is still never *mutated*: a dedup-hit
returns the existing row unchanged rather than updating it, and there
is no update function exposed, matching ADR-0006's spirit for
anything derived from immutable raw evidence.

Story: stories/STORY-003-normaliser-event-store.md
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union

PathLike = Union[str, "Path"]


@dataclass(frozen=True)
class Event:
    security_id: str
    type: str
    direction: Optional[str]
    published_at: Optional[str]
    first_seen_at: str
    known_at: str
    session_date: Optional[str]
    source: str
    source_id: str
    snapshot_id: int
    classifier_version: str
    event_id: Optional[int] = None


_SCHEMA = """
CREATE TABLE IF NOT EXISTS event (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    security_id TEXT NOT NULL,
    type TEXT NOT NULL,
    direction TEXT,
    published_at TEXT,
    first_seen_at TEXT NOT NULL,
    known_at TEXT NOT NULL,
    session_date TEXT,
    source TEXT NOT NULL,
    source_id TEXT NOT NULL,
    snapshot_id INTEGER NOT NULL,
    classifier_version TEXT NOT NULL,
    UNIQUE(source, source_id, type)
);
"""


def _connect(db_path: PathLike) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute(_SCHEMA)
    conn.commit()
    return conn


def write_event(event: Event, *, db_path: PathLike) -> Event:
    """Persist one event, deduplicated on (source, source_id, type).

    If an event with the same (source, source_id, type) already
    exists, that existing row is returned unchanged -- this call
    never updates it and never creates a duplicate. This is what
    makes normalise_snapshot safe to re-run over the same raw
    snapshot.
    """
    conn = _connect(db_path)
    try:
        cur = conn.execute(
            "SELECT event_id FROM event WHERE source = ? AND source_id = ? AND type = ?",
            (event.source, event.source_id, event.type),
        )
        existing = cur.fetchone()
        if existing is not None:
            return read_event(existing[0], db_path=db_path)

        cur = conn.execute(
            "INSERT INTO event "
            "(security_id, type, direction, published_at, first_seen_at, known_at, "
            "session_date, source, source_id, snapshot_id, classifier_version) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                event.security_id,
                event.type,
                event.direction,
                event.published_at,
                event.first_seen_at,
                event.known_at,
                event.session_date,
                event.source,
                event.source_id,
                event.snapshot_id,
                event.classifier_version,
            ),
        )
        conn.commit()
        event_id = cur.lastrowid
    finally:
        conn.close()

    return Event(
        event_id=event_id,
        security_id=event.security_id,
        type=event.type,
        direction=event.direction,
        published_at=event.published_at,
        first_seen_at=event.first_seen_at,
        known_at=event.known_at,
        session_date=event.session_date,
        source=event.source,
        source_id=event.source_id,
        snapshot_id=event.snapshot_id,
        classifier_version=event.classifier_version,
    )


_COLUMNS = (
    "event_id, security_id, type, direction, published_at, first_seen_at, "
    "known_at, session_date, source, source_id, snapshot_id, classifier_version"
)


def _row_to_event(row) -> Event:
    return Event(
        event_id=row[0],
        security_id=row[1],
        type=row[2],
        direction=row[3],
        published_at=row[4],
        first_seen_at=row[5],
        known_at=row[6],
        session_date=row[7],
        source=row[8],
        source_id=row[9],
        snapshot_id=row[10],
        classifier_version=row[11],
    )


def read_event(event_id: int, *, db_path: PathLike) -> Event:
    conn = _connect(db_path)
    try:
        row = conn.execute(
            f"SELECT {_COLUMNS} FROM event WHERE event_id = ?", (event_id,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise KeyError(f"no event with id={event_id}")
    return _row_to_event(row)


def list_events_for_snapshot(snapshot_id: int, *, db_path: PathLike) -> List[Event]:
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            f"SELECT {_COLUMNS} FROM event WHERE snapshot_id = ? ORDER BY event_id",
            (snapshot_id,),
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_event(row) for row in rows]
