"""System-level test for the 8-K normaliser (STORY-003).

Writes a raw snapshot through STORY-001's real store (the same
function the STORY-002 collector calls), then runs normalise_snapshot
end-to-end against it and reads the resulting events back through
STORY-003's own event store -- proving the two stories' storage
layers actually compose, not just that each parses in isolation.

Also verifies STORY-005's wiring: session_date is populated (not
None) using the real NYSE calendar.

Regression fixture set: still vacuous, as in STORY-001/002 -- no
experiment is FROZEN yet.
"""

from __future__ import annotations

from edgelab.normalisers.edgar_8k import normalise_snapshot
from edgelab.storage.event_store import list_events_for_snapshot
from edgelab.storage.raw_snapshot import write_raw_snapshot
from tests.unit.test_edgar_8k_normaliser import make_header_text


def test_normalise_snapshot_end_to_end(tmp_path):
    raw_db_path = tmp_path / "raw.sqlite3"
    raw_data_dir = tmp_path / "raw_data"
    event_db_path = tmp_path / "events.sqlite3"

    payload = make_header_text(
        accession="0000320193-26-000050",
        acceptance="20260920163211",
        items=("Results of Operations and Financial Condition", "Entry into a Material Definitive Agreement"),
    )
    snapshot = write_raw_snapshot(
        "edgar_8k",
        "2026-09-20T16:45:00Z",
        payload,
        db_path=raw_db_path,
        data_dir=raw_data_dir,
        url="https://www.sec.gov/Archives/edgar/data/320193/0000320193-26-000050.txt",
    )

    result = normalise_snapshot(
        snapshot.id, raw_db_path=raw_db_path, event_db_path=event_db_path
    )

    assert len(result.events_written) == 2
    types = {event.type for event in result.events_written}
    assert types == {"earnings_release", "material_agreement"}
    assert result.unmapped_item_descriptions == ()

    for event in result.events_written:
        assert event.snapshot_id == snapshot.id
        assert event.known_at == snapshot.first_seen_at
        assert event.security_id == "0000320193"
        # STORY-005: session_date is now computed, not left None.
        assert event.session_date is not None
        assert event.session_date == "2026-09-21"  # 2026-09-20 acceptance is a Sunday

    stored = list_events_for_snapshot(snapshot.id, db_path=event_db_path)
    assert {e.type for e in stored} == types


def test_normalise_snapshot_is_idempotent(tmp_path):
    raw_db_path = tmp_path / "raw.sqlite3"
    raw_data_dir = tmp_path / "raw_data"
    event_db_path = tmp_path / "events.sqlite3"

    payload = make_header_text()
    snapshot = write_raw_snapshot(
        "edgar_8k",
        "2026-09-20T16:45:00Z",
        payload,
        db_path=raw_db_path,
        data_dir=raw_data_dir,
    )

    first = normalise_snapshot(snapshot.id, raw_db_path=raw_db_path, event_db_path=event_db_path)
    second = normalise_snapshot(snapshot.id, raw_db_path=raw_db_path, event_db_path=event_db_path)

    assert [e.event_id for e in first.events_written] == [e.event_id for e in second.events_written]
    assert len(list_events_for_snapshot(snapshot.id, db_path=event_db_path)) == len(
        first.events_written
    )
