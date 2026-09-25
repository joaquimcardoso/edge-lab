"""System-level test for STORY-013: build_and_write's real report/verdict
composed with notify_ops_status, through a real collection run and a
real on-disk idempotency log -- proving the whole chain (collect ->
report -> verdict -> Telegram message) actually composes, not just
that notify_ops_status works against a hand-built fixture.
"""

from __future__ import annotations

import build_daily_report as bdr
import collect_premarket_8k as cp

from edgelab.config import CollectorConfig
from edgelab.notify.notify_ops_status import notify_ops_status
from edgelab.notify.telegram_sender import FakeTelegramSender
from tests.unit.test_edgar_8k import FakeHttpClient, FakeResponse, make_submissions_fixture
from tests.unit.test_edgar_8k_normaliser import make_header_text


def _run_one_day_collection(tmp_path):
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
    cp.run(universe, http_client=client, config=config)
    cp.append_heartbeat(config.log_dir, now=lambda: "2026-09-25T12:00:00Z")
    return config


def test_notify_ops_status_after_real_build_and_write(tmp_path):
    config = _run_one_day_collection(tmp_path)

    report, verdict, _md_path, _json_path = bdr.build_and_write(
        "2026-09-25",
        raw_db_path=config.raw_db_path,
        event_db_path=config.event_db_path,
        data_dir=config.data_dir,
        log_dir=config.log_dir,
        reports_dir=config.reports_dir,
    )

    sender = FakeTelegramSender()
    sent = notify_ops_status(report, verdict, sender=sender, chat_id="chat-1", log_dir=config.log_dir)

    assert sent is True
    assert len(sender.sent) == 1
    chat_id, text = sender.sent[0]
    assert chat_id == "chat-1"
    assert f"Verdict: {verdict.verdict}" in text
    assert "edgar_8k" in text
    assert "No trading signal. No live trading exists." in text

    # A second build+notify for the same date (e.g. a systemd retry)
    # must not re-send.
    report2, verdict2, _, _ = bdr.build_and_write(
        "2026-09-25",
        raw_db_path=config.raw_db_path,
        event_db_path=config.event_db_path,
        data_dir=config.data_dir,
        log_dir=config.log_dir,
        reports_dir=config.reports_dir,
    )
    sent_again = notify_ops_status(
        report2, verdict2, sender=sender, chat_id="chat-1", log_dir=config.log_dir
    )
    assert sent_again is False
    assert len(sender.sent) == 1
