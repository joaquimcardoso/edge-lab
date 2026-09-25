"""Immutable raw snapshot store.

See docs/01-point-in-time-rules.md §7 and docs/03-architecture.md's
`raw_snapshot` table (docs/03-architecture.md#core-data-model). This
module is intentionally append-only: it exposes no update or delete
function for any row it writes, for any reason. If a payload turns
out to be wrong, the fix is a new, later snapshot — never editing
this one.

Story: stories/STORY-001-raw-snapshot-store.md
"""

from __future__ import annotations

import gzip
import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, Union

PathLike = Union[str, "Path"]


class EmptyPayloadError(ValueError):
    """Raised when a caller tries to persist an empty or missing payload.

    A failed download must never produce a signal
    (docs/02-data-sources.md), so this module refuses to write a row
    for it at all — not even a row marked "failed".
    """


class IntegrityError(RuntimeError):
    """Raised when a stored payload's SHA-256 no longer matches its
    on-disk bytes at read time."""


@dataclass(frozen=True)
class RawSnapshot:
    id: int
    source: str
    url: Optional[str]
    retrieved_at: str
    first_seen_at: str
    sha256: str
    payload_path: str
    payload_bytes: int


_SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    url TEXT,
    retrieved_at TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    payload_path TEXT NOT NULL,
    payload_bytes INTEGER NOT NULL
);
"""


def _connect(db_path: PathLike) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute(_SCHEMA)
    conn.commit()
    return conn


def write_raw_snapshot(
    source: str,
    retrieved_at: str,
    payload: Optional[bytes],
    *,
    db_path: PathLike,
    data_dir: PathLike,
    url: Optional[str] = None,
    first_seen_at: Optional[str] = None,
) -> RawSnapshot:
    """Persist one fetch attempt's raw payload as an immutable row.

    Writes exactly one new row every call — including when the
    payload content is byte-identical to a previous write, because
    *when this system observed something* matters even when the
    content didn't change. The payload bytes themselves are stored
    once per distinct content (content-addressed by sha256); only the
    row, not the blob, is duplicated.

    Raises EmptyPayloadError, and writes nothing at all, if payload
    is None or empty.
    """
    if payload is None or len(payload) == 0:
        raise EmptyPayloadError(
            f"refusing to write a raw_snapshot for source={source!r}: "
            "payload is empty or None (a failed fetch must never "
            "produce a snapshot)"
        )

    digest = hashlib.sha256(payload).hexdigest()
    effective_first_seen_at = first_seen_at or retrieved_at

    data_dir = Path(data_dir)
    source_dir = data_dir / source
    source_dir.mkdir(parents=True, exist_ok=True)
    # Stored gzip-compressed on disk per ADR-0006 ("raw payloads are
    # compressed"); sha256 is always computed over the uncompressed
    # payload so the hash identifies the logical content, independent
    # of gzip's own non-deterministic-across-versions framing bytes.
    payload_path = source_dir / f"{digest}.bin.gz"
    if not payload_path.exists():
        payload_path.write_bytes(gzip.compress(payload))

    conn = _connect(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO raw_snapshot "
            "(source, url, retrieved_at, first_seen_at, sha256, payload_path, payload_bytes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                source,
                url,
                retrieved_at,
                effective_first_seen_at,
                digest,
                str(payload_path),
                len(payload),
            ),
        )
        conn.commit()
        row_id = cur.lastrowid
    finally:
        conn.close()

    return RawSnapshot(
        id=row_id,
        source=source,
        url=url,
        retrieved_at=retrieved_at,
        first_seen_at=effective_first_seen_at,
        sha256=digest,
        payload_path=str(payload_path),
        payload_bytes=len(payload),
    )


def read_raw_snapshot(
    snapshot_id: int, *, db_path: PathLike
) -> Tuple[RawSnapshot, bytes]:
    """Read back a row and its payload, re-verifying the SHA-256 every time.

    Raises IntegrityError if the on-disk payload no longer matches
    the hash recorded at write time — this is the check that makes
    "immutable" a verified property, not just an intention.
    """
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT id, source, url, retrieved_at, first_seen_at, "
            "sha256, payload_path, payload_bytes "
            "FROM raw_snapshot WHERE id = ?",
            (snapshot_id,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        raise KeyError(f"no raw_snapshot with id={snapshot_id}")

    snapshot = RawSnapshot(*row)
    payload = gzip.decompress(Path(snapshot.payload_path).read_bytes())
    actual_digest = hashlib.sha256(payload).hexdigest()
    if actual_digest != snapshot.sha256:
        raise IntegrityError(
            f"raw_snapshot id={snapshot_id}: recorded sha256="
            f"{snapshot.sha256} but on-disk payload now hashes to "
            f"{actual_digest}"
        )
    return snapshot, payload
