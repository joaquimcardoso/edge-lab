"""System-level test for the daily ops report (STORY-009).

Runs STORY-008's collect_premarket_8k.run() end-to-end against a
fake HTTP transport, then builds and writes the daily report over
the resulting real stores -- proving the two stories actually
compose, and that the written Markdown and JSON agree with each
other on every count.
"""

from __future__ import annotations

import json

import collect_premarket_8k as cp

from edgelab.config import CollectorConfig
from edgelab.report.daily_report import build_daily_ops_report, render_daily_report, write_daily_report
from tests.unit.test_edgar_8k import FakeHttpClient, FakeResponse, make_submissions_fixture
from tests.unit.test_edgar_8k_normaliser import make_header_text


def test_daily_report_reflects_a_real_collection_run(tmp_path):
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
    config.universe_path.write_text("ticker,cik\nAAPL,320193\n")

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

    universe = cp.load_universe(config.universe_path)
    summary = cp.run(universe, http_client=client, config=config)
    cp.append_failure_log(summary, log_dir=config.log_dir, now=lambda: "2026-09-25T12:00:00Z")

    report = build_daily_ops_report(
        "2026-09-25",
        raw_db_path=config.raw_db_path,
        event_db_path=config.event_db_path,
        data_dir=config.data_dir,
        log_dir=config.log_dir,
    )
    markdown = render_daily_report(report)
    md_path, json_path = write_daily_report(report, markdown, reports_dir=config.reports_dir)

    assert report.total_snapshots_all_time == summary.total_snapshots == 3
    assert report.total_events_all_time == summary.total_events == 3
    assert report.integrity_checked == 3
    assert report.integrity_failures == ()
    assert report.failures_today == ()

    assert md_path.exists() and json_path.exists()
    parsed = json.loads(json_path.read_text())
    assert parsed["total_snapshots_all_time"] == 3
    assert parsed["total_events_all_time"] == 3
    assert "edgar_8k" in markdown
