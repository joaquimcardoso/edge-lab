"""Unit tests for src/edgelab/notify/format_ops_status.py (STORY-013).

Pure string-formatting tests -- no network, no filesystem. Reuses
STORY-010's _base_report fixture so the same report shapes that
already drive score_day's tests also drive the message this repo
actually sends.
"""

from __future__ import annotations

from edgelab.notify.format_ops_status import format_ops_status
from edgelab.report.day_verdict import score_day
from edgelab.report.daily_report import CollectorFailureRecord
from tests.unit.test_day_verdict import _base_report, _passing_stats


def test_format_ops_status_good_day_mentions_verdict_and_mode():
    report = _base_report(latency_stats=(_passing_stats(),))
    verdict = score_day(report, is_scheduled_collection_day=True)

    text = format_ops_status(report, verdict)

    assert "Verdict: GOOD" in text
    assert "2026-09-25" in text
    assert "edgar_8k" in text
    assert "No trading signal. No live trading exists." in text


def test_format_ops_status_bad_day_includes_every_reason():
    report = _base_report(collector_runs_today=0)
    verdict = score_day(report, is_scheduled_collection_day=True)

    text = format_ops_status(report, verdict)

    assert "Verdict: BAD" in text
    assert verdict.reasons
    for reason in verdict.reasons:
        assert reason in text


def test_format_ops_status_no_data_yet_says_so_plainly():
    report = _base_report(
        snapshots_today_by_source={},
        events_today_by_type={},
        total_snapshots_all_time=0,
        total_events_all_time=0,
        integrity_checked=0,
        latency_stats=(),
        collector_runs_today=1,
    )
    verdict = score_day(report, is_scheduled_collection_day=True)

    text = format_ops_status(report, verdict)

    assert "none recorded" in text
    assert "no data collected yet" in text


def test_format_ops_status_never_mentions_a_trading_signal():
    report = _base_report(latency_stats=(_passing_stats(),))
    verdict = score_day(report, is_scheduled_collection_day=True)

    text = format_ops_status(report, verdict).lower()

    for forbidden in ("buy", "sell", "entry price", "position size"):
        assert forbidden not in text


def test_format_ops_status_warn_day_mentions_verdict_and_disclaimer():
    report = _base_report(
        latency_stats=(_passing_stats(),),
        failures_today=(
            CollectorFailureRecord(
                timestamp="2026-09-25T13:00:00Z",
                ticker="AAPL",
                cik="320193",
                accession_number="0000320193-26-000099",
                url="https://www.sec.gov/Archives/edgar/data/320193/example.txt",
                reason="HTTP 503",
            ),
        ),
    )
    verdict = score_day(report, is_scheduled_collection_day=True)

    text = format_ops_status(report, verdict)

    assert "Verdict: WARN" in text
    assert verdict.reasons
    for reason in verdict.reasons:
        assert reason in text
    assert "No trading signal. No live trading exists." in text
