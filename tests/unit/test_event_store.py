"""Unit tests for src/edgelab/storage/event_store.py."""

from __future__ import annotations

from edgelab.storage import event_store as es


def make_event(**overrides):
    defaults = dict(
        security_id="0000320193",
        type="earnings_release",
        direction=None,
        published_at="2026-09-20T16:32:11Z",
        first_seen_at="2026-09-20T16:45:00Z",
        known_at="2026-09-20T16:45:00Z",
        session_date=None,
        source="edgar_8k",
        source_id="0000320193-26-000050",
        snapshot_id=1,
        classifier_version="rules-v1-8k-item-code",
    )
    defaults.update(overrides)
    return es.Event(**defaults)


def test_write_and_read_round_trip(tmp_path):
    db_path = tmp_path / "events.sqlite3"
    written = es.write_event(make_event(), db_path=db_path)

    assert written.event_id is not None
    read_back = es.read_event(written.event_id, db_path=db_path)
    assert read_back == written


def test_write_is_deduplicated_on_source_source_id_type(tmp_path):
    db_path = tmp_path / "events.sqlite3"
    first = es.write_event(make_event(), db_path=db_path)
    second = es.write_event(make_event(), db_path=db_path)

    assert first.event_id == second.event_id

    conn_events = es.list_events_for_snapshot(1, db_path=db_path)
    assert len(conn_events) == 1


def test_different_type_same_filing_is_not_deduplicated(tmp_path):
    db_path = tmp_path / "events.sqlite3"
    earnings = es.write_event(make_event(type="earnings_release"), db_path=db_path)
    agreement = es.write_event(make_event(type="material_agreement"), db_path=db_path)

    assert earnings.event_id != agreement.event_id
    assert len(es.list_events_for_snapshot(1, db_path=db_path)) == 2


def test_list_events_for_snapshot_filters_by_snapshot_id(tmp_path):
    db_path = tmp_path / "events.sqlite3"
    es.write_event(make_event(snapshot_id=1, source_id="acc-1"), db_path=db_path)
    es.write_event(make_event(snapshot_id=2, source_id="acc-2"), db_path=db_path)

    assert len(es.list_events_for_snapshot(1, db_path=db_path)) == 1
    assert len(es.list_events_for_snapshot(2, db_path=db_path)) == 1
    assert len(es.list_events_for_snapshot(999, db_path=db_path)) == 0


def test_reading_unknown_event_id_raises_key_error(tmp_path):
    db_path = tmp_path / "events.sqlite3"
    es._connect(db_path).close()
    try:
        es.read_event(9999, db_path=db_path)
        raise AssertionError("expected KeyError")
    except KeyError:
        pass
