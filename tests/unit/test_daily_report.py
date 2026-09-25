"""Unit tests for src/edgelab/report/daily_report.py (STORY-009)."""

from __future__ import annotations

import gzip
import json

from edgelab.report.daily_report import (
    build_daily_ops_report,
    render_daily_report,
    write_daily_report,
)
from edgelab.storage.event_store import Event, write_event
from edgelab.storage.raw_snapshot import write_raw_snapshot


def test_date_bucketing_crosses_midnight_et_correctly(tmp_path):
    raw_db_path = tmp_path / "raw.sqlite3"
    data_dir = tmp_path / "raw_data"
    event_db_path = tmp_path / "event.sqlite3"

    # 2026-09-21T03:59:00Z is 2026-09-20 23:59 America/New_York (EDT, UTC-4).
    write_raw_snapshot(
        "edgar_8k", "2026-09-21T03:59:00Z", b"before-midnight-et",
        db_path=raw_db_path, data_dir=data_dir,
        first_seen_at="2026-09-21T03:59:00Z",
    )
    # 2026-09-21T04:01:00Z is 2026-09-21 00:01 America/New_York.
    write_raw_snapshot(
        "edgar_8k", "2026-09-21T04:01:00Z", b"after-midnight-et",
        db_path=raw_db_path, data_dir=data_dir,
        first_seen_at="2026-09-21T04:01:00Z",
    )

    report_sep20 = build_daily_ops_report(
        "2026-09-20", raw_db_path=raw_db_path, event_db_path=event_db_path,
        data_dir=data_dir, log_dir=tmp_path / "logs",
    )
    report_sep21 = build_daily_ops_report(
        "2026-09-21", raw_db_path=raw_db_path, event_db_path=event_db_path,
        data_dir=data_dir, log_dir=tmp_path / "logs",
    )

    assert report_sep20.snapshots_today_by_source == {"edgar_8k": 1}
    assert report_sep21.snapshots_today_by_source == {"edgar_8k": 1}
    assert report_sep20.total_snapshots_all_time == 2


def test_zero_activity_day_produces_valid_report_not_an_error(tmp_path):
    report = build_daily_ops_report(
        "2026-09-20",
        raw_db_path=tmp_path / "raw.sqlite3",
        event_db_path=tmp_path / "event.sqlite3",
        data_dir=tmp_path / "data",
        log_dir=tmp_path / "logs",
    )
    assert report.snapshots_today_by_source == {}
    assert report.events_today_by_type == {}
    assert report.total_snapshots_all_time == 0
    assert report.integrity_checked == 0
    assert report.integrity_failures == ()
    assert report.failures_today == ()
    markdown = render_daily_report(report)
    assert "No snapshots or events recorded" in markdown
    assert "No raw snapshots to check yet" in markdown


def test_integrity_check_names_exactly_the_tampered_snapshot(tmp_path):
    raw_db_path = tmp_path / "raw.sqlite3"
    data_dir = tmp_path / "raw_data"

    good = write_raw_snapshot(
        "edgar_8k", "2026-09-20T12:00:00Z", b"untouched payload",
        db_path=raw_db_path, data_dir=data_dir,
    )
    tampered = write_raw_snapshot(
        "edgar_8k", "2026-09-20T12:05:00Z", b"payload that will be corrupted",
        db_path=raw_db_path, data_dir=data_dir,
    )

    # Corrupt the tampered snapshot's on-disk bytes directly.
    with gzip.open(tampered.payload_path, "wb") as fh:
        fh.write(b"corrupted bytes, does not match recorded sha256")

    report = build_daily_ops_report(
        "2026-09-20",
        raw_db_path=raw_db_path,
        event_db_path=tmp_path / "event.sqlite3",
        data_dir=data_dir,
        log_dir=tmp_path / "logs",
        integrity_sample_size=20,
    )

    assert report.integrity_checked == 2
    assert report.integrity_failures == (tampered.id,)
    assert good.id not in report.integrity_failures
    markdown = render_daily_report(report)
    assert "FAILED sha256 verification" in markdown
    assert str(tampered.id) in markdown


def test_write_daily_report_produces_matching_markdown_and_json(tmp_path):
    report = build_daily_ops_report(
        "2026-09-20",
        raw_db_path=tmp_path / "raw.sqlite3",
        event_db_path=tmp_path / "event.sqlite3",
        data_dir=tmp_path / "data",
        log_dir=tmp_path / "logs",
    )
    markdown = render_daily_report(report)
    reports_dir = tmp_path / "reports"

    md_path, json_path = write_daily_report(report, markdown, reports_dir=reports_dir)

    assert md_path == reports_dir / "2026-09-20-ops.md"
    assert json_path == reports_dir / "2026-09-20-ops.json"
    assert md_path.read_text() == markdown
    parsed = json.loads(json_path.read_text())
    assert parsed["report_date"] == "2026-09-20"
    assert parsed["total_snapshots_all_time"] == 0


def test_write_daily_report_overwrites_same_date(tmp_path):
    reports_dir = tmp_path / "reports"
    report1 = build_daily_ops_report(
        "2026-09-20", raw_db_path=tmp_path / "raw.sqlite3",
        event_db_path=tmp_path / "event.sqlite3",
        data_dir=tmp_path / "data", log_dir=tmp_path / "logs",
    )
    write_daily_report(report1, render_daily_report(report1), reports_dir=reports_dir)

    write_raw_snapshot(
        "edgar_8k", "2026-09-20T12:00:00Z", b"new activity",
        db_path=tmp_path / "raw.sqlite3", data_dir=tmp_path / "data",
    )
    report2 = build_daily_ops_report(
        "2026-09-20", raw_db_path=tmp_path / "raw.sqlite3",
        event_db_path=tmp_path / "event.sqlite3",
        data_dir=tmp_path / "data", log_dir=tmp_path / "logs",
    )
    md_path, json_path = write_daily_report(report2, render_daily_report(report2), reports_dir=reports_dir)

    parsed = json.loads(json_path.read_text())
    assert parsed["total_snapshots_all_time"] == 1
