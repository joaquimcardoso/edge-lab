"""Unit tests for src/edgelab/report/day_verdict.py (STORY-010).

Each BAD trigger is proven independently sufficient (matching
STORY-007's "each bar independently required" testing pattern), plus
WARN, GOOD, and that all firing reasons accumulate rather than
stopping at the first.
"""

from __future__ import annotations

from edgelab.audit.feed_latency import LatencyStats
from edgelab.report.daily_report import CollectorFailureRecord, DailyOpsReport, LatencyGap
from edgelab.report.day_verdict import BAD, GOOD, WARN, score_day


def _base_report(**overrides) -> DailyOpsReport:
    defaults = dict(
        report_date="2026-09-25",
        snapshots_today_by_source={"edgar_8k": 3},
        events_today_by_type={"earnings_release": 3},
        total_snapshots_all_time=3,
        total_events_all_time=3,
        integrity_checked=3,
        integrity_failures=(),
        failures_today=(),
        latency_stats=(),
        latency_gaps=(),
        data_dir_bytes=1_000,
        collector_runs_today=5,
        disk_total_bytes=1_000_000_000,
        disk_free_bytes=500_000_000,
    )
    defaults.update(overrides)
    return DailyOpsReport(**defaults)


def _passing_stats(**overrides) -> LatencyStats:
    defaults = dict(
        source="edgar_8k", event_type="earnings_release",
        total_premarket_events=20, seen_before_open_count=18,
        share_seen_before_open=0.9, lag_seconds_p50=15.0,
        lag_seconds_p90=25.0, lag_seconds_p95=28.0, passed=True,
    )
    defaults.update(overrides)
    return LatencyStats(**defaults)


def test_good_day_with_no_issues():
    report = _base_report(latency_stats=(_passing_stats(),))
    verdict = score_day(report, is_scheduled_collection_day=True)
    assert verdict.verdict == GOOD
    assert verdict.reasons == ()


def test_bad_integrity_failure_alone_is_sufficient():
    report = _base_report(integrity_failures=(7,))
    verdict = score_day(report, is_scheduled_collection_day=True)
    assert verdict.verdict == BAD
    assert any("integrity failure" in r for r in verdict.reasons)


def test_bad_gate0_failing_with_enough_samples_alone_is_sufficient():
    failing = _passing_stats(passed=False, total_premarket_events=15, share_seen_before_open=0.5)
    report = _base_report(latency_stats=(failing,))
    verdict = score_day(report, is_scheduled_collection_day=True)
    assert verdict.verdict == BAD
    assert any("Gate 0 failing" in r for r in verdict.reasons)


def test_gate0_failing_with_too_few_samples_does_not_trigger_bad():
    failing_but_small = _passing_stats(passed=False, total_premarket_events=3)
    report = _base_report(latency_stats=(failing_but_small,))
    verdict = score_day(report, is_scheduled_collection_day=True)
    assert verdict.verdict == GOOD
    assert verdict.reasons == ()


def test_bad_low_disk_free_ratio_alone_is_sufficient():
    report = _base_report(disk_total_bytes=1_000_000_000, disk_free_bytes=50_000_000)  # 5%
    verdict = score_day(report, is_scheduled_collection_day=True)
    assert verdict.verdict == BAD
    assert any("disk free ratio" in r for r in verdict.reasons)


def test_bad_zero_heartbeats_on_scheduled_day_alone_is_sufficient():
    report = _base_report(collector_runs_today=0)
    verdict = score_day(report, is_scheduled_collection_day=True)
    assert verdict.verdict == BAD
    assert any("zero heartbeats" in r for r in verdict.reasons)


def test_zero_heartbeats_on_non_scheduled_day_is_not_bad():
    report = _base_report(collector_runs_today=0)
    verdict = score_day(report, is_scheduled_collection_day=False)
    assert verdict.verdict == GOOD


def test_warn_for_recorded_failures_with_nothing_else_wrong():
    report = _base_report(
        failures_today=(
            CollectorFailureRecord(
                timestamp="2026-09-25T09:00:00Z", ticker="AAPL", cik="320193",
                accession_number="", url="", reason="503",
            ),
        )
    )
    verdict = score_day(report, is_scheduled_collection_day=True)
    assert verdict.verdict == WARN
    assert any("collector failure" in r for r in verdict.reasons)


def test_multiple_bad_triggers_all_accumulate_in_reasons():
    report = _base_report(
        integrity_failures=(1,),
        disk_total_bytes=1_000_000_000,
        disk_free_bytes=10_000_000,  # 1%
        collector_runs_today=0,
    )
    verdict = score_day(report, is_scheduled_collection_day=True)
    assert verdict.verdict == BAD
    assert len(verdict.reasons) == 3
    assert any("integrity failure" in r for r in verdict.reasons)
    assert any("disk free ratio" in r for r in verdict.reasons)
    assert any("zero heartbeats" in r for r in verdict.reasons)


def test_gate0_progress_labels_insufficient_data_separately_from_failing():
    insufficient = _passing_stats(passed=False, total_premarket_events=2)
    report = _base_report(
        latency_stats=(insufficient,),
        latency_gaps=(LatencyGap(source="edgar_8k", event_type="material_agreement", reason="no data"),),
    )
    verdict = score_day(report, is_scheduled_collection_day=True)
    statuses = {(c.source, c.event_type): c.status for c in verdict.gate0_progress.combos}
    assert statuses[("edgar_8k", "earnings_release")] == "INSUFFICIENT_DATA"
    assert statuses[("edgar_8k", "material_agreement")] == "INSUFFICIENT_DATA"
    assert verdict.verdict == GOOD  # insufficient data never triggers BAD/WARN on its own
