"""Unit tests for src/edgelab/storage/raw_snapshot.py.

Covers STORY-001's acceptance criteria: round-trip write/read,
empty-payload rejection, hash-tampering detection, determinism of
repeated writes (same content -> same sha256/file bytes, still two
distinct rows), first_seen_at defaulting, and that no update/delete
function is exposed by the module at all.
"""

from __future__ import annotations

import gzip
import inspect
import sqlite3
from pathlib import Path

import pytest

from edgelab.storage import raw_snapshot as rs


@pytest.fixture
def store(tmp_path):
    return {
        "db_path": tmp_path / "raw.sqlite3",
        "data_dir": tmp_path / "data",
    }


def test_write_read_round_trip(store):
    written = rs.write_raw_snapshot(
        "edgar_8k",
        "2026-09-25T12:00:00Z",
        b"hello world",
        db_path=store["db_path"],
        data_dir=store["data_dir"],
        url="https://example.com/doc",
    )

    assert written.id is not None
    assert written.source == "edgar_8k"
    assert written.url == "https://example.com/doc"
    assert written.payload_bytes == len(b"hello world")

    read_snapshot, payload = rs.read_raw_snapshot(
        written.id, db_path=store["db_path"]
    )

    assert payload == b"hello world"
    assert read_snapshot.sha256 == written.sha256
    assert read_snapshot.payload_path == written.payload_path
    assert read_snapshot.source == "edgar_8k"


def test_payload_is_gzip_compressed_on_disk(store):
    written = rs.write_raw_snapshot(
        "edgar_8k",
        "2026-09-25T12:00:00Z",
        b"hello world" * 100,
        db_path=store["db_path"],
        data_dir=store["data_dir"],
    )

    on_disk = Path(written.payload_path).read_bytes()
    # Must actually be gzip-compressed per ADR-0006, not raw bytes.
    assert on_disk[:2] == b"\x1f\x8b"
    assert gzip.decompress(on_disk) == b"hello world" * 100


@pytest.mark.parametrize("bad_payload", [None, b""])
def test_empty_payload_is_rejected(store, bad_payload):
    with pytest.raises(rs.EmptyPayloadError):
        rs.write_raw_snapshot(
            "edgar_8k",
            "2026-09-25T12:00:00Z",
            bad_payload,
            db_path=store["db_path"],
            data_dir=store["data_dir"],
        )

    # No row must have been written for the rejected attempt.
    if store["db_path"].exists():
        conn = sqlite3.connect(str(store["db_path"]))
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM raw_snapshot"
            ).fetchone()[0]
        finally:
            conn.close()
        assert count == 0


def test_hash_tampering_is_detected_on_read(store):
    written = rs.write_raw_snapshot(
        "edgar_8k",
        "2026-09-25T12:00:00Z",
        b"original content",
        db_path=store["db_path"],
        data_dir=store["data_dir"],
    )

    # Tamper with the on-disk (compressed) payload after the fact.
    payload_path = Path(written.payload_path)
    payload_path.write_bytes(gzip.compress(b"tampered content"))

    with pytest.raises(rs.IntegrityError):
        rs.read_raw_snapshot(written.id, db_path=store["db_path"])


def test_reading_unknown_id_raises_key_error(store):
    # Force schema creation without writing any row.
    rs._connect(store["db_path"]).close()
    with pytest.raises(KeyError):
        rs.read_raw_snapshot(9999, db_path=store["db_path"])


def test_identical_writes_are_deterministic_but_two_rows(store):
    first = rs.write_raw_snapshot(
        "edgar_8k",
        "2026-09-25T12:00:00Z",
        b"same bytes",
        db_path=store["db_path"],
        data_dir=store["data_dir"],
    )
    second = rs.write_raw_snapshot(
        "edgar_8k",
        "2026-09-25T13:00:00Z",
        b"same bytes",
        db_path=store["db_path"],
        data_dir=store["data_dir"],
    )

    # Same content -> same sha256, same content-addressed file, same
    # on-disk bytes -- but two distinct rows, because *when* this was
    # observed matters even when the content is unchanged.
    assert first.sha256 == second.sha256
    assert first.payload_path == second.payload_path
    assert first.id != second.id
    assert Path(first.payload_path).read_bytes() == Path(
        second.payload_path
    ).read_bytes()

    conn = sqlite3.connect(str(store["db_path"]))
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM raw_snapshot"
        ).fetchone()[0]
    finally:
        conn.close()
    assert count == 2


def test_first_seen_at_defaults_to_retrieved_at(store):
    written = rs.write_raw_snapshot(
        "edgar_8k",
        "2026-09-25T12:00:00Z",
        b"payload",
        db_path=store["db_path"],
        data_dir=store["data_dir"],
    )
    assert written.first_seen_at == "2026-09-25T12:00:00Z"


def test_first_seen_at_can_be_set_explicitly(store):
    written = rs.write_raw_snapshot(
        "edgar_8k",
        "2026-09-25T12:00:00Z",
        b"payload",
        db_path=store["db_path"],
        data_dir=store["data_dir"],
        first_seen_at="2026-09-25T11:55:00Z",
    )
    assert written.first_seen_at == "2026-09-25T11:55:00Z"
    assert written.retrieved_at == "2026-09-25T12:00:00Z"


def test_no_update_or_delete_function_is_exposed():
    names = {name for name, _ in inspect.getmembers(rs, inspect.isfunction)}
    forbidden_substrings = ("update", "delete", "remove", "modify")
    offending = [
        name
        for name in names
        if any(bad in name.lower() for bad in forbidden_substrings)
    ]
    assert offending == [], (
        "raw_snapshot module must stay append-only, but exposes: "
        f"{offending}"
    )
