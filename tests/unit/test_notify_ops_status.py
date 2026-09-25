"""Unit tests for src/edgelab/notify/notify_ops_status.py (STORY-013).

FakeTelegramSender only -- no real network. Proves the idempotency
contract (never re-sends for a report_date already recorded) and
that a send failure is never recorded as sent.
"""

from __future__ import annotations

import json

import pytest

from edgelab.notify.notify_ops_status import notify_ops_status
from edgelab.notify.telegram_sender import FakeTelegramSender, TelegramSendError
from edgelab.report.day_verdict import score_day
from tests.unit.test_day_verdict import _base_report, _passing_stats


def _report_and_verdict(**overrides):
    report = _base_report(latency_stats=(_passing_stats(),), **overrides)
    verdict = score_day(report, is_scheduled_collection_day=True)
    return report, verdict


def test_notify_ops_status_sends_and_records(tmp_path):
    report, verdict = _report_and_verdict()
    sender = FakeTelegramSender()

    sent = notify_ops_status(
        report, verdict, sender=sender, chat_id="chat-1", log_dir=tmp_path,
        now=lambda: "2026-09-25T21:00:00Z",
    )

    assert sent is True
    assert len(sender.sent) == 1
    chat_id, text = sender.sent[0]
    assert chat_id == "chat-1"
    assert "Verdict: GOOD" in text

    log_path = tmp_path / "telegram_sent.jsonl"
    assert log_path.exists()
    row = json.loads(log_path.read_text().splitlines()[0])
    assert row == {"report_date": "2026-09-25", "timestamp": "2026-09-25T21:00:00Z"}


def test_notify_ops_status_skips_second_send_same_day(tmp_path):
    report, verdict = _report_and_verdict()
    sender = FakeTelegramSender()

    first = notify_ops_status(report, verdict, sender=sender, chat_id="chat-1", log_dir=tmp_path)
    second = notify_ops_status(report, verdict, sender=sender, chat_id="chat-1", log_dir=tmp_path)

    assert first is True
    assert second is False
    assert len(sender.sent) == 1


def test_notify_ops_status_sends_again_for_a_different_day(tmp_path):
    sender = FakeTelegramSender()
    report1, verdict1 = _report_and_verdict(report_date="2026-09-25")
    report2, verdict2 = _report_and_verdict(report_date="2026-09-26")

    first = notify_ops_status(report1, verdict1, sender=sender, chat_id="chat-1", log_dir=tmp_path)
    second = notify_ops_status(report2, verdict2, sender=sender, chat_id="chat-1", log_dir=tmp_path)

    assert first is True
    assert second is True
    assert len(sender.sent) == 2


def test_notify_ops_status_does_not_record_a_failed_send(tmp_path):
    report, verdict = _report_and_verdict()

    class FailingSender:
        def send(self, chat_id, text):
            raise TelegramSendError("HTTP 500")

    with pytest.raises(TelegramSendError):
        notify_ops_status(report, verdict, sender=FailingSender(), chat_id="chat-1", log_dir=tmp_path)

    log_path = tmp_path / "telegram_sent.jsonl"
    assert not log_path.exists()

    # A retry after the failure is not treated as already-sent.
    sender = FakeTelegramSender()
    sent = notify_ops_status(report, verdict, sender=sender, chat_id="chat-1", log_dir=tmp_path)
    assert sent is True
    assert len(sender.sent) == 1
