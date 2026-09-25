"""Daily operations report -- the artifact this repository's own
Reporter component (docs/03-architecture.md) was always meant to
produce but nothing wired together until now.

Pure analysis over already-persisted state: reads the raw snapshot
store, event store, and STORY-008's collector-failure log; writes
nothing to any of them. Same "collector runs the schedule, this
repository analyses the result" split as STORY-007's feed-latency
harness, which this module reuses rather than reimplementing.

Story: stories/STORY-009-daily-ops-report.md
"""

from __future__ import annotations

import json
import shutil
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from edgelab.audit.feed_latency import (
    FeedLatencyAuditError,
    LatencyStats,
    compute_latency_stats,
)
from edgelab.audit.feed_latency import render_report as render_latency_table
from edgelab.calendar.trading_calendar import EASTERN
from edgelab.storage.event_store import list_all_events
from edgelab.storage.raw_snapshot import IntegrityError, RawSnapshot, list_all_raw_snapshots, read_raw_snapshot

PathLike = Union[str, "Path"]


def _to_et_date(iso_utc: str) -> str:
    """Convert an ISO-8601 UTC timestamp (this repository's storage
    convention throughout) to its America/New_York calendar date.
    """
    dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
    return dt.astimezone(EASTERN).date().isoformat()


@dataclass(frozen=True)
class LatencyGap:
    source: str
    event_type: Optional[str]
    reason: str


@dataclass(frozen=True)
class CollectorFailureRecord:
    timestamp: str
    ticker: str
    cik: str
    accession_number: str
    url: str
    reason: str


@dataclass(frozen=True)
class DailyOpsReport:
    report_date: str
    snapshots_today_by_source: Dict[str, int]
    events_today_by_type: Dict[str, int]
    total_snapshots_all_time: int
    total_events_all_time: int
    integrity_checked: int
    integrity_failures: Tuple[int, ...]
    failures_today: Tuple[CollectorFailureRecord, ...]
    latency_stats: Tuple[LatencyStats, ...]
    latency_gaps: Tuple[LatencyGap, ...]
    data_dir_bytes: int
    collector_runs_today: int
    disk_total_bytes: Optional[int]
    disk_free_bytes: Optional[int]


def _dir_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def _integrity_check(
    snapshots: List[RawSnapshot], *, db_path: PathLike, sample_size: int
) -> Tuple[int, Tuple[int, ...]]:
    """Re-verify sha256 for up to `sample_size` of the most recently
    written snapshots, via the existing read_raw_snapshot -- never a
    second hand-rolled hash check.
    """
    sample = snapshots[-sample_size:] if sample_size else []
    failures: List[int] = []
    for snap in sample:
        try:
            read_raw_snapshot(snap.id, db_path=db_path)
        except IntegrityError:
            failures.append(snap.id)
    return len(sample), tuple(failures)


def _count_heartbeats_today(log_dir: Path, report_date: str) -> int:
    log_path = log_dir / "run_heartbeats.jsonl"
    if not log_path.exists():
        return 0
    count = 0
    for line in log_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if _to_et_date(row["timestamp"]) == report_date:
            count += 1
    return count


def _disk_usage(path: Path) -> Tuple[Optional[int], Optional[int]]:
    """(total_bytes, free_bytes) for the filesystem containing `path`,
    or (None, None) if that filesystem cannot be inspected (e.g. the
    directory does not exist yet on a completely fresh install) --
    a missing disk-usage reading is treated as "unknown," never as
    "0 bytes free," by every caller.
    """
    probe = path if path.exists() else path.parent
    try:
        while not probe.exists() and probe != probe.parent:
            probe = probe.parent
        usage = shutil.disk_usage(probe)
        return usage.total, usage.free
    except OSError:
        return None, None


def _read_failures_today(log_dir: Path, report_date: str) -> Tuple[CollectorFailureRecord, ...]:
    log_path = log_dir / "collector_failures.jsonl"
    if not log_path.exists():
        return ()
    records: List[CollectorFailureRecord] = []
    for line in log_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if _to_et_date(row["timestamp"]) != report_date:
            continue
        records.append(CollectorFailureRecord(**row))
    return tuple(records)


def build_daily_ops_report(
    report_date: str,
    *,
    raw_db_path: PathLike,
    event_db_path: PathLike,
    data_dir: PathLike,
    log_dir: PathLike,
    integrity_sample_size: int = 20,
) -> DailyOpsReport:
    """Build one day's operations report. Never raises for a
    zero-activity day (weekend, holiday, or before any collection
    has run) -- an empty store produces a valid report stating that
    plainly, not an error.
    """
    data_dir = Path(data_dir)
    log_dir = Path(log_dir)

    all_snapshots = list_all_raw_snapshots(db_path=raw_db_path)
    all_events = list_all_events(db_path=event_db_path)

    snapshots_today = [s for s in all_snapshots if _to_et_date(s.first_seen_at) == report_date]
    events_today = [e for e in all_events if _to_et_date(e.first_seen_at) == report_date]

    snapshots_today_by_source: Dict[str, int] = dict(Counter(s.source for s in snapshots_today))
    events_today_by_type: Dict[str, int] = dict(Counter(e.type for e in events_today))

    integrity_checked, integrity_failures = _integrity_check(
        all_snapshots, db_path=raw_db_path, sample_size=integrity_sample_size
    )

    failures_today = _read_failures_today(log_dir, report_date)
    collector_runs_today = _count_heartbeats_today(log_dir, report_date)
    disk_total_bytes, disk_free_bytes = _disk_usage(data_dir)

    # Cumulative (all-time) Gate 0 latency, per (source, event_type)
    # combination actually present -- not just today's, since Gate 0
    # is judged over the whole 2-3 week campaign, not one day.
    combos = sorted({(e.source, e.type) for e in all_events})
    latency_stats: List[LatencyStats] = []
    latency_gaps: List[LatencyGap] = []
    for source, event_type in combos:
        try:
            stats = compute_latency_stats(all_events, source=source, event_type=event_type)
            latency_stats.append(stats)
        except FeedLatencyAuditError as exc:
            latency_gaps.append(LatencyGap(source=source, event_type=event_type, reason=str(exc)))

    return DailyOpsReport(
        report_date=report_date,
        snapshots_today_by_source=snapshots_today_by_source,
        events_today_by_type=events_today_by_type,
        total_snapshots_all_time=len(all_snapshots),
        total_events_all_time=len(all_events),
        integrity_checked=integrity_checked,
        integrity_failures=integrity_failures,
        failures_today=failures_today,
        latency_stats=tuple(latency_stats),
        latency_gaps=tuple(latency_gaps),
        data_dir_bytes=_dir_size_bytes(data_dir),
        collector_runs_today=collector_runs_today,
        disk_total_bytes=disk_total_bytes,
        disk_free_bytes=disk_free_bytes,
    )


def render_daily_report(report: DailyOpsReport) -> str:
    """Markdown, matching this repository's existing report convention
    (docs/03-architecture.md's Reporter component) -- reuses
    feed_latency.render_report's own table rather than a second
    implementation of it.
    """
    lines = [f"# Daily operations report — {report.report_date}", ""]

    lines.append("## Collection today")
    if not report.snapshots_today_by_source and not report.events_today_by_type:
        lines.append("No snapshots or events recorded for this date.")
    else:
        lines.append("| Source | Snapshots today |")
        lines.append("|---|---|")
        for source, count in sorted(report.snapshots_today_by_source.items()):
            lines.append(f"| {source} | {count} |")
        lines.append("")
        lines.append("| Event type | Events today |")
        lines.append("|---|---|")
        for event_type, count in sorted(report.events_today_by_type.items()):
            lines.append(f"| {event_type} | {count} |")
    lines.append("")

    lines.append("## Cumulative totals")
    lines.append(f"- Total raw snapshots (all time): {report.total_snapshots_all_time}")
    lines.append(f"- Total events (all time): {report.total_events_all_time}")
    lines.append(f"- Data directory size: {report.data_dir_bytes:,} bytes")
    lines.append(f"- Collector runs today (heartbeats): {report.collector_runs_today}")
    if report.disk_total_bytes is not None and report.disk_free_bytes is not None:
        free_ratio = report.disk_free_bytes / report.disk_total_bytes
        lines.append(f"- Disk free: {report.disk_free_bytes:,} / {report.disk_total_bytes:,} bytes ({free_ratio:.0%})")
    else:
        lines.append("- Disk free: unknown")
    lines.append("")

    lines.append("## Integrity check")
    if report.integrity_checked == 0:
        lines.append("No raw snapshots to check yet.")
    elif report.integrity_failures:
        lines.append(
            f"**{len(report.integrity_failures)} of {report.integrity_checked} sampled "
            f"snapshots FAILED sha256 verification**: ids {list(report.integrity_failures)}"
        )
    else:
        lines.append(f"{report.integrity_checked} sampled snapshots verified OK (sha256 matched).")
    lines.append("")

    lines.append("## Collector failures today")
    if not report.failures_today:
        lines.append("None recorded.")
    else:
        lines.append("| Timestamp | Ticker | CIK | Reason |")
        lines.append("|---|---|---|---|")
        for f in report.failures_today:
            lines.append(f"| {f.timestamp} | {f.ticker} | {f.cik} | {f.reason} |")
    lines.append("")

    lines.append("## Gate 0 — cumulative feed latency (all data collected so far)")
    if report.latency_stats:
        lines.append(render_latency_table(list(report.latency_stats)))
    else:
        lines.append("No source/event-type combination has enough pre-market data yet.")
    if report.latency_gaps:
        lines.append("")
        lines.append("Insufficient data yet for:")
        for gap in report.latency_gaps:
            event_type_label = gap.event_type or "(all)"
            lines.append(f"- {gap.source} / {event_type_label}: {gap.reason}")

    return "\n".join(lines)


def write_daily_report(
    report: DailyOpsReport, markdown: str, *, reports_dir: PathLike
) -> Tuple[Path, Path]:
    """Write both the Markdown report and its JSON sibling (the latter
    is what STORY-010's rubric reads, so it never has to re-parse
    Markdown). Overwrites any existing report for the same date --
    a report is a snapshot of current state, not append-only evidence;
    regenerating it from the same underlying store is expected.
    """
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    md_path = reports_dir / f"{report.report_date}-ops.md"
    json_path = reports_dir / f"{report.report_date}-ops.json"
    md_path.write_text(markdown)
    json_path.write_text(json.dumps(asdict(report), indent=2))
    return md_path, json_path
