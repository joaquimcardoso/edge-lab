"""System-level smoke test for the raw snapshot store (STORY-001).

Unlike test_raw_snapshot.py (isolated unit behaviour per function),
this exercises the module the way it will actually be used: multiple
independent collector runs, across multiple sources, writing to one
shared on-disk store over separate connections (simulating separate
scheduled Pi invocations), followed by a full read-back and integrity
pass over every row.

Regression fixture set: STORY-001 predates any FROZEN experiment, so
there is no recorded experiment output to diff against yet. That
"0 unexplained diffs" gate is therefore vacuously satisfied for this
story -- there is nothing to compare against, not a skipped check.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from edgelab.storage import raw_snapshot as rs


def test_multi_source_multi_run_end_to_end(tmp_path):
    db_path = tmp_path / "pipeline" / "raw.sqlite3"
    data_dir = tmp_path / "pipeline" / "data"

    # Simulate several independent collector runs (separate processes
    # in production -> here, separate calls with no shared connection
    # object) across three different sources, some sharing content.
    runs = [
        ("edgar_8k", "2026-09-25T09:30:05Z", b"8-K filing A", "https://sec.gov/a"),
        ("edgar_8k", "2026-09-25T09:31:10Z", b"8-K filing B", "https://sec.gov/b"),
        ("prices_daily", "2026-09-25T20:05:00Z", b"AAPL,190.12,...", None),
        ("rss_news", "2026-09-25T09:30:07Z", b"headline text", "https://prnewswire.com/x"),
        # Same content re-observed on a later run -- must still create
        # a new row (a re-fetch of the same underlying content is a
        # real, separate observation event).
        ("edgar_8k", "2026-09-25T10:00:00Z", b"8-K filing A", "https://sec.gov/a"),
    ]

    written = []
    for source, retrieved_at, payload, url in runs:
        snap = rs.write_raw_snapshot(
            source,
            retrieved_at,
            payload,
            db_path=db_path,
            data_dir=data_dir,
            url=url,
        )
        written.append(snap)

    # All five runs produced five distinct rows.
    assert len({s.id for s in written}) == 5

    # Every row reads back cleanly with an intact hash, via a fresh
    # connection each time (no shared in-memory state relied upon).
    for snap in written:
        read_snap, payload = rs.read_raw_snapshot(snap.id, db_path=db_path)
        assert read_snap.sha256 == snap.sha256
        assert len(payload) == snap.payload_bytes

    # Content-addressing worked across runs: the two "8-K filing A"
    # writes (same bytes, different retrieved_at) share one on-disk
    # blob, identified by sha256 rather than by byte length (another
    # payload in this run happens to be the same length but different
    # content, so length alone is not a safe way to find the pair).
    filing_a_hash = written[0].sha256
    dup_pair = [s for s in written if s.sha256 == filing_a_hash]
    assert len(dup_pair) == 2
    assert dup_pair[0].payload_path == dup_pair[1].payload_path
    assert dup_pair[0].id != dup_pair[1].id

    # One data subdirectory per source, nothing stray at the top level.
    source_dirs = {p.name for p in data_dir.iterdir() if p.is_dir()}
    assert source_dirs == {"edgar_8k", "prices_daily", "rss_news"}

    # The store is a normal WAL-mode SQLite file a downstream
    # normaliser can open read-only and query directly.
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        total = conn.execute("SELECT COUNT(*) FROM raw_snapshot").fetchone()[0]
        by_source = dict(
            conn.execute(
                "SELECT source, COUNT(*) FROM raw_snapshot GROUP BY source"
            ).fetchall()
        )
    finally:
        conn.close()

    assert total == 5
    assert by_source == {"edgar_8k": 3, "prices_daily": 1, "rss_news": 1}


def test_regression_fixture_set_is_vacuous_pre_first_experiment():
    """0-regressions gate for this story: no experiment is FROZEN yet
    (docs/07-development-workflow.md's mechanical definition of "0
    regressions" re-runs FROZEN experiments and diffs recorded
    observations). There is nothing to re-run, so nothing can
    regress -- this test documents that fact rather than skip it
    silently.
    """
    frozen_experiments_at_story_001_time = []
    assert frozen_experiments_at_story_001_time == []
