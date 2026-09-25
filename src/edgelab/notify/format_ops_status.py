"""Pure Telegram message formatter for the daily ops status.

No network, no I/O -- formats STORY-009/010's already-real
DailyOpsReport/DayVerdict into text. Never formats a trading signal;
none exists yet. Every number in this message comes directly from
those two objects -- nothing here is generated or guessed.

Story: stories/STORY-013-telegram-ops-notification.md
"""

from __future__ import annotations

from edgelab.report.daily_report import DailyOpsReport
from edgelab.report.day_verdict import BAD, GOOD, WARN, DayVerdict

_VERDICT_EMOJI = {GOOD: "✅", WARN: "⚠️", BAD: "\U0001f6a8"}


def format_ops_status(report: DailyOpsReport, verdict: DayVerdict) -> str:
    emoji = _VERDICT_EMOJI.get(verdict.verdict, "")
    lines = [
        f"{emoji} edge-lab — Daily Ops Status",
        "",
        f"Date: {report.report_date} (America/New_York)",
        f"Verdict: {verdict.verdict}",
    ]
    if verdict.reasons:
        lines.append("")
        for reason in verdict.reasons:
            lines.append(f"• {reason}")

    lines.append("")
    lines.append("Collection today:")
    if report.snapshots_today_by_source:
        for source, count in sorted(report.snapshots_today_by_source.items()):
            events = report.events_today_by_type
            events_summary = ", ".join(f"{k}={v}" for k, v in sorted(events.items())) or "0 events"
            lines.append(f"• {source}: {count} snapshots, {events_summary}")
    else:
        lines.append("• none recorded")

    lines.append("")
    lines.append("Gate 0 progress:")
    if verdict.gate0_progress.combos:
        for combo in verdict.gate0_progress.combos:
            event_type_label = combo.event_type or "(all)"
            lines.append(f"• {combo.source}/{event_type_label}: {combo.status}")
    else:
        lines.append("• no data collected yet")

    lines.append("")
    lines.append(f"Integrity: {report.integrity_checked - len(report.integrity_failures)}/{report.integrity_checked} verified OK")
    if report.disk_total_bytes and report.disk_free_bytes is not None:
        free_ratio = report.disk_free_bytes / report.disk_total_bytes
        lines.append(f"Disk free: {free_ratio:.0%}")

    lines.append("")
    lines.append("Mode: Phase 1 — Collection & audit. No trading signal. No live trading exists.")
    return "\n".join(lines)
