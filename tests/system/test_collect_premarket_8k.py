"""System-level test for scripts/collect_premarket_8k.py (STORY-008).

Runs run() end-to-end against a fake HTTP transport, through the
real raw_snapshot / event_store stores in a temp dir -- proving
STORY-002/003's collector and normaliser, plus this story's new
config and universe loading, actually compose into a runnable
pipeline, not just that each piece parses in isolation.
"""

from __future__ import annotations

import collect_premarket_8k as cp

from edgelab.config import CollectorConfig
from edgelab.storage.event_store import list_events_for_snapshot
from edgelab.storage.raw_snapshot import read_raw_snapshot
from tests.unit.test_edgar_8k import FakeHttpClient, FakeResponse, make_submissions_fixture
from tests.unit.test_edgar_8k_normaliser import make_header_text


def test_collect_premarket_8k_end_to_end(tmp_path):
    data_dir = tmp_path / "data"
    config = CollectorConfig(
        sec_user_agent="edge-lab system test contact@example.com",
        data_dir=data_dir,
        raw_db_path=data_dir / "raw.sqlite3",
        event_db_path=data_dir / "event.sqlite3",
        reports_dir=data_dir / "reports",
        universe_path=tmp_path / "universe.csv",
        log_dir=data_dir / "logs",
    )
    config.data_dir.mkdir(parents=True)

    universe_path = config.universe_path
    universe_path.write_text("ticker,cik\nAAPL,320193\n")

    fixture = make_submissions_fixture()
    submissions_url = "https://data.sec.gov/submissions/CIK0000320193.json"
    responses = {submissions_url: FakeResponse(200, json_body=fixture)}
    for acc, acceptance in [
        ("0000320193-26-000050", "20260920163211"),
        ("0000320193-26-000053", "20260923090100"),
        ("0000320193-26-000054", "20260924074500"),
    ]:
        url = f"https://www.sec.gov/Archives/edgar/data/320193/{acc}.txt"
        responses[url] = FakeResponse(
            200, content=make_header_text(accession=acc, acceptance=acceptance)
        )
    client = FakeHttpClient(responses)

    universe = cp.load_universe(universe_path)
    summary = cp.run(universe, http_client=client, config=config)

    assert summary.total_snapshots == 3
    assert summary.total_events == 3
    assert summary.ciks_with_failures == ()

    # The raw store and event store both really exist on disk and
    # are readable back through their own real modules, not just
    # asserted against the in-memory RunSummary.
    outcome = summary.outcomes[0]
    assert outcome.snapshots_written == 3
    for snapshot_id in range(1, outcome.snapshots_written + 1):
        snapshot, payload = read_raw_snapshot(snapshot_id, db_path=config.raw_db_path)
        assert snapshot.source == "edgar_8k"
        events = list_events_for_snapshot(snapshot_id, db_path=config.event_db_path)
        assert len(events) >= 1
