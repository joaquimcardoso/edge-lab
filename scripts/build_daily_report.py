"""Entrypoint: build and write one day's operations report + verdict.

This is the script systemd invokes for the "Daily report" job
(docs/04-infrastructure.md, 17:00 ET). Pure wiring over STORY-009's
report builder and STORY-010's day_verdict -- one artifact (Markdown
+ JSON), not two files that can drift apart. Does not commit
anything to git -- that half of the infrastructure doc's "Daily
report + commit" job name is an explicit open item, not built here
(see STORY-010's scope boundary).

Story: stories/STORY-010-ops-rubric-and-reviewer-agent.md
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

from edgelab.calendar.trading_calendar import EASTERN, is_trading_day
from edgelab.config import load_collector_config, load_notification_config
from edgelab.notify.notify_ops_status import notify_ops_status
from edgelab.notify.telegram_sender import RequestsTelegramSender, TelegramSendError
from edgelab.report.daily_report import DailyOpsReport, build_daily_ops_report, render_daily_report
from edgelab.report.day_verdict import DayVerdict, render_verdict, score_day

logger = logging.getLogger("edgelab.build_daily_report")


def _today_et() -> str:
    return datetime.now(timezone.utc).astimezone(EASTERN).date().isoformat()


def _write_combined(
    report: DailyOpsReport, verdict: DayVerdict, markdown: str, *, reports_dir
) -> Tuple[Path, Path]:
    """Write one Markdown file and one JSON file per date, each
    carrying both the report and its verdict -- deliberately not
    STORY-009's report-only write_daily_report, so the report and
    its verdict can never drift into two files that disagree.
    """
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    md_path = reports_dir / f"{report.report_date}-ops.md"
    json_path = reports_dir / f"{report.report_date}-ops.json"
    md_path.write_text(markdown)
    json_path.write_text(
        json.dumps({"report": asdict(report), "verdict": asdict(verdict)}, indent=2)
    )
    return md_path, json_path


def build_and_write(
    report_date: str,
    *,
    raw_db_path,
    event_db_path,
    data_dir,
    log_dir,
    reports_dir,
) -> Tuple[DailyOpsReport, DayVerdict, Path, Path]:
    """Build the report and its verdict, render both into one
    Markdown document plus one JSON document, and write them.
    """
    report = build_daily_ops_report(
        report_date,
        raw_db_path=raw_db_path,
        event_db_path=event_db_path,
        data_dir=data_dir,
        log_dir=log_dir,
    )
    verdict = score_day(report, is_scheduled_collection_day=is_trading_day(report_date))
    markdown = render_daily_report(report) + "\n\n" + render_verdict(verdict)
    md_path, json_path = _write_combined(report, verdict, markdown, reports_dir=reports_dir)
    return report, verdict, md_path, json_path


def _send_ops_status_notification(
    report: DailyOpsReport, verdict: DayVerdict, *, log_dir
) -> None:
    """Best-effort Telegram notification: the report has already
    been written to disk by the time this runs, so a Telegram
    problem (bad token, network outage, rate limit) is logged loudly
    but never turned into a failure of the report-building job
    itself -- same isolation principle as collect_premarket_8k.run()
    not letting one CIK's failure stop the others.
    """
    notification_config = load_notification_config()
    if not notification_config.telegram_enabled:
        logger.info(
            "telegram: not configured (EDGELAB_TELEGRAM_BOT_TOKEN/EDGELAB_TELEGRAM_CHAT_ID "
            "unset) -- skipping notification"
        )
        return
    sender = RequestsTelegramSender(notification_config.telegram_bot_token)
    try:
        notify_ops_status(
            report,
            verdict,
            sender=sender,
            chat_id=notification_config.telegram_chat_id,
            log_dir=log_dir,
        )
    except TelegramSendError as exc:
        logger.error("telegram: send failed for %s: %s", report.report_date, exc)


def main(report_date: Optional[str] = None) -> DayVerdict:
    logging.basicConfig(level=logging.INFO)
    config = load_collector_config()
    date = report_date or _today_et()

    report, verdict, md_path, json_path = build_and_write(
        date,
        raw_db_path=config.raw_db_path,
        event_db_path=config.event_db_path,
        data_dir=config.data_dir,
        log_dir=config.log_dir,
        reports_dir=config.reports_dir,
    )
    logger.info("daily report written: %s (verdict=%s)", md_path, verdict.verdict)
    if verdict.verdict == "BAD":
        logger.error("verdict BAD for %s: %s", date, "; ".join(verdict.reasons))

    _send_ops_status_notification(report, verdict, log_dir=config.log_dir)

    return verdict


if __name__ == "__main__":
    main()
