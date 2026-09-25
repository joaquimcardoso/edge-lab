"""System-level test for the feed-latency audit harness (STORY-007).

Writes raw edgar_8k snapshots through STORY-001/002's real store,
normalises them through STORY-003's real normaliser (which populates
published_at/first_seen_at on every event), then audits the
resulting events end-to-end through STORY-007's harness.

Regression fixture set: still vacuous -- no experiment is FROZEN yet
(EXP-002 itself is explicitly blocked on this very gate).
"""

from __future__ import annotations

from edgelab.audit.feed_latency import compute_latency_stats, render_report
from edgelab.normalisers.edgar_8k import normalise_snapshot
from edgelab.storage.raw_snapshot import write_raw_snapshot
from tests.unit.test_edgar_8k_normaliser import make_header_text


def test_feed_latency_audit_end_to_end(tmp_path):
    raw_db_path = tmp_path / "raw.sqlite3"
    raw_data_dir = tmp_path / "raw_data"
    event_db_path = tmp_path / "events.sqlite3"

    # Five filings, all accepted pre-market on the same Monday
    # (2026-09-21), all "seen" (first_seen_at, i.e. retrieved_at
    # passed to write_raw_snapshot) 15 seconds later -- comfortably
    # inside Gate 0's pass bar.
    events = []
    for i in range(5):
        payload = make_header_text(
            accession=f"0000320193-26-00005{i}",
            acceptance="20260921120000",  # 08:00 ET Monday
            items=("Results of Operations and Financial Condition",),
        )
        snapshot = write_raw_snapshot(
            "edgar_8k",
            "2026-09-21T12:00:15Z",  # first_seen_at: 15s after acceptance
            payload,
            db_path=raw_db_path,
            data_dir=raw_data_dir,
        )
        result = normalise_snapshot(
            snapshot.id, raw_db_path=raw_db_path, event_db_path=event_db_path
        )
        events.extend(result.events_written)

    assert len(events) == 5

    stats = compute_latency_stats(events, source="edgar_8k", event_type="earnings_release")

    assert stats.total_premarket_events == 5
    assert stats.share_seen_before_open == 1.0
    assert stats.lag_seconds_p50 == 15.0
    assert stats.passed is True

    report = render_report([stats])
    assert "edgar_8k" in report
    assert "PASS" in report
    assert len(report) > 0
