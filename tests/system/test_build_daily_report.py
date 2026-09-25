"""System-level test for scripts/build_daily_report.py (STORY-010).

Runs a real collection (STORY-008's run()) through to a written
combined report+verdict artifact, asserting the artifact agrees with
directly calling score_day on the same report -- proving the
composition, not just each piece in isolation.
"""

from __future__ import annotations

import json

import build_daily_report as bdr
import collect_premarket_8k as cp

from edgelab.config import CollectorConfig
from edgelab.report.daily_report import build_daily_ops_report
from edgelab.report.day_verdict import score_day
from tests.unit.test_edgar_8k import FakeHttpClient, FakeResponse, make_submissions_fixture
from tests.unit.test_edgar_8k_normaliser import make_header_text


def test_build_and_write_agrees_with_direct_score_day(tmp_path):
    data_dir = tmp_path / "data"
    config = CollectorConfig(
        sec_user_agent="edge-lab system test contact@example.com",
        data_dir=data_dir,
        raw_db_path=data_dir / "raw.sqlite3",
        event_db_path=data_dir / "event.sqlite3",
        reports_dir=data_dir / "reports",
        universe_path=tmp_path / "universe.csv",
        log_dir=data_dir / "logs",
        price_db_path=data_dir / "price_daily.sqlite3",
    )
    config.data_dir.mkdir(parents=True)
    config.universe_path.write_text("ticker,cik\nAAPL,320193\n")

    fixture = make_submissions_fixture()
    submissions_url = "https://data.sec.gov/submissions/CIK0000320193.json"
    responses = {submissions_url: FakeResponse(200, json_body=fixture)}
    for acc, acceptance in [
        ("0000320193-26-000050", "20260925090000"),
        ("0000320193-26-000053", "20260925091000"),
        ("0000320193-26-000054", "20260925092000"),
    ]:
        url = f"https://www.sec.gov/Archives/edgar/data/320193/{acc}.txt"
        responses[url] = FakeResponse(
            200, content=make_header_text(accession=acc, acceptance=acceptance)
        )
    client = FakeHttpClient(responses)

    universe = cp.load_universe(config.universe_path)
    summary = cp.run(universe, http_client=client, config=config)
    cp.append_heartbeat(config.log_dir, now=lambda: "2026-09-25T12:00:00Z")
    cp.append_failure_log(summary, log_dir=config.log_dir, now=lambda: "2026-09-25T12:00:00Z")

    report, verdict, md_path, json_path = bdr.build_and_write(
        "2026-09-25",
        raw_db_path=config.raw_db_path,
        event_db_path=config.event_db_path,
        data_dir=config.data_dir,
        log_dir=config.log_dir,
        reports_dir=config.reports_dir,
    )

    direct_verdict = score_day(report, is_scheduled_collection_day=True)
    assert verdict.verdict == direct_verdict.verdict
    assert verdict.reasons == direct_verdict.reasons

    assert md_path.exists() and json_path.exists()
    assert "## Verdict:" in md_path.read_text()

    parsed = json.loads(json_path.read_text())
    assert parsed["verdict"]["verdict"] == verdict.verdict
    assert parsed["report"]["total_snapshots_all_time"] == 3
    assert parsed["report"]["collector_runs_today"] == 1
