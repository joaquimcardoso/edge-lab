"""Idempotent Telegram send for the daily ops status.

Wraps STORY-013's pure format_ops_status with the same append-only
"did this already happen today" pattern STORY-009/010 use for
collector_failures.jsonl and run_heartbeats.jsonl -- a systemd
oneshot unit that reruns (retry, manual re-trigger) must never
re-notify for a report_date already sent.

Story: stories/STORY-013-telegram-ops-notification.md
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from edgelab.notify.format_ops_status import format_ops_status
from edgelab.notify.telegram_sender import TelegramSender
from edgelab.report.daily_report import DailyOpsReport
from edgelab.report.day_verdict import DayVerdict

logger = logging.getLogger("edgelab.notify_ops_status")

_SENT_LOG_NAME = "telegram_sent.jsonl"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _already_sent(log_dir: Path, report_date: str) -> bool:
    log_path = log_dir / _SENT_LOG_NAME
    if not log_path.exists():
        return False
    for line in log_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if row.get("report_date") == report_date:
            return True
    return False


def _append_sent(log_dir: Path, report_date: str, *, now: Callable[[], str]) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / _SENT_LOG_NAME
    with log_path.open("a") as fh:
        fh.write(json.dumps({"report_date": report_date, "timestamp": now()}) + "\n")


def notify_ops_status(
    report: DailyOpsReport,
    verdict: DayVerdict,
    *,
    sender: TelegramSender,
    chat_id: str,
    log_dir: Path,
    now: Callable[[], str] = _utc_now_iso,
) -> bool:
    """Send the formatted ops status to Telegram, once per report_date.

    Returns True when a message was actually sent, False when a
    message for report.report_date was already recorded in
    <log_dir>/telegram_sent.jsonl and this call skipped sending.
    Deliberately does not catch a send failure from `sender` -- if
    sending raises, nothing is appended to the sent log (so a later
    retry will try again), and the exception propagates to the
    caller to decide whether that is fatal.
    """
    log_dir = Path(log_dir)
    if _already_sent(log_dir, report.report_date):
        logger.info("telegram: already sent for %s, skipping", report.report_date)
        return False
    text = format_ops_status(report, verdict)
    sender.send(chat_id, text)
    _append_sent(log_dir, report.report_date, now=now)
    logger.info("telegram: sent ops status for %s", report.report_date)
    return True
