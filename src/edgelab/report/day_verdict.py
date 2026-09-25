"""Good day / bad day operations verdict -- deterministic, no LLM,
applied mechanically to STORY-009's DailyOpsReport.

This scores operational health of the collection pipeline during the
Gate 0 campaign only. It does not, and cannot yet, say anything about
trading performance -- there is no strategy or paper-trading loop in
this repository (docs/00-vision.md's roadmap: this is Phase 1).

See docs/09-operations-rubric.md for the same rule in plain language;
that document and this module must never diverge.

Story: stories/STORY-010-ops-rubric-and-reviewer-agent.md
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from edgelab.report.daily_report import DailyOpsReport

GOOD = "GOOD"
WARN = "WARN"
BAD = "BAD"

DEFAULT_MIN_SAMPLE_FOR_GATE0_VERDICT = 10
DEFAULT_CRITICAL_DISK_FREE_RATIO = 0.10


@dataclass(frozen=True)
class Gate0ComboStatus:
    source: str
    event_type: "str | None"
    status: str  # "PASSING" | "FAILING" | "INSUFFICIENT_DATA"


@dataclass(frozen=True)
class Gate0Progress:
    combos: Tuple[Gate0ComboStatus, ...]

    @property
    def any_passing(self) -> bool:
        return any(c.status == "PASSING" for c in self.combos)

    @property
    def any_failing(self) -> bool:
        return any(c.status == "FAILING" for c in self.combos)


@dataclass(frozen=True)
class DayVerdict:
    report_date: str
    verdict: str  # GOOD | WARN | BAD
    reasons: Tuple[str, ...]
    gate0_progress: Gate0Progress


def _build_gate0_progress(
    report: DailyOpsReport, *, min_sample_for_gate0_verdict: int
) -> Gate0Progress:
    combos: List[Gate0ComboStatus] = []
    for stats in report.latency_stats:
        if stats.total_premarket_events < min_sample_for_gate0_verdict:
            status = "INSUFFICIENT_DATA"
        else:
            status = "PASSING" if stats.passed else "FAILING"
        combos.append(Gate0ComboStatus(source=stats.source, event_type=stats.event_type, status=status))
    for gap in report.latency_gaps:
        combos.append(
            Gate0ComboStatus(source=gap.source, event_type=gap.event_type, status="INSUFFICIENT_DATA")
        )
    return Gate0Progress(combos=tuple(combos))


def score_day(
    report: DailyOpsReport,
    *,
    is_scheduled_collection_day: bool,
    min_sample_for_gate0_verdict: int = DEFAULT_MIN_SAMPLE_FOR_GATE0_VERDICT,
    critical_disk_free_ratio: float = DEFAULT_CRITICAL_DISK_FREE_RATIO,
) -> DayVerdict:
    """Apply docs/09-operations-rubric.md's rule to one day's report.

    Every trigger that actually fired is recorded in `reasons`, in
    the rubric's own priority order -- not just whichever fired
    first -- so a BAD verdict never hides that other things were
    also wrong that day.
    """
    reasons: List[str] = []
    has_bad_trigger = False

    if report.integrity_failures:
        has_bad_trigger = True
        reasons.append(
            f"raw-store integrity failure: snapshot id(s) {list(report.integrity_failures)} "
            "failed sha256 re-verification"
        )

    failing_combos = [
        s
        for s in report.latency_stats
        if not s.passed and s.total_premarket_events >= min_sample_for_gate0_verdict
    ]
    if failing_combos:
        has_bad_trigger = True
    for stats in failing_combos:
        event_type_label = stats.event_type or "(all)"
        reasons.append(
            f"Gate 0 failing for {stats.source}/{event_type_label}: "
            f"share={stats.share_seen_before_open:.0%}, p50={stats.lag_seconds_p50:.1f}s "
            f"(n={stats.total_premarket_events})"
        )

    if report.disk_total_bytes and report.disk_free_bytes is not None:
        free_ratio = report.disk_free_bytes / report.disk_total_bytes
        if free_ratio < critical_disk_free_ratio:
            has_bad_trigger = True
            reasons.append(f"disk free ratio {free_ratio:.0%} below critical threshold {critical_disk_free_ratio:.0%}")

    if is_scheduled_collection_day and report.collector_runs_today == 0:
        has_bad_trigger = True
        reasons.append("collector was scheduled to run today but recorded zero heartbeats")

    if has_bad_trigger:
        verdict = BAD
    elif report.failures_today:
        verdict = WARN
        reasons.append(
            f"{len(report.failures_today)} collector failure(s) recorded today "
            "(collector did run; not severe enough alone for BAD)"
        )
    else:
        verdict = GOOD

    gate0_progress = _build_gate0_progress(
        report, min_sample_for_gate0_verdict=min_sample_for_gate0_verdict
    )

    return DayVerdict(
        report_date=report.report_date,
        verdict=verdict,
        reasons=tuple(reasons),
        gate0_progress=gate0_progress,
    )


def render_verdict(verdict: DayVerdict) -> str:
    lines = [f"## Verdict: {verdict.verdict}", ""]
    if verdict.reasons:
        for reason in verdict.reasons:
            lines.append(f"- {reason}")
    else:
        lines.append("No issues detected.")
    lines.append("")
    lines.append("### Gate 0 progress (per source / event type)")
    if verdict.gate0_progress.combos:
        for combo in verdict.gate0_progress.combos:
            event_type_label = combo.event_type or "(all)"
            lines.append(f"- {combo.source}/{event_type_label}: {combo.status}")
    else:
        lines.append("No data collected yet.")
    return "\n".join(lines)
