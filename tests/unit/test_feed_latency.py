"""Unit tests for src/edgelab/audit/feed_latency.py."""

from __future__ import annotations

import pytest

from edgelab.audit import feed_latency as fl
from edgelab.storage.event_store import Event


def make_event(**overrides):
    defaults = dict(
        security_id="0000320193",
        type="earnings_release",
        direction=None,
        published_at="2026-09-21T12:00:00Z",  # 08:00 ET, pre-market Monday
        first_seen_at="2026-09-21T12:00:20Z",  # 20s lag, still pre-market
        known_at="2026-09-21T12:00:20Z",
        session_date="2026-09-21",
        source="edgar_8k",
        source_id="acc-1",
        snapshot_id=1,
        classifier_version="rules-v1-8k-item-code",
    )
    defaults.update(overrides)
    return Event(**defaults)


def test_is_premarket_event_true_for_weekday_before_open():
    assert fl.is_premarket_event("2026-09-21T12:00:00Z") is True  # 08:00 ET Monday


def test_is_premarket_event_false_for_intraday():
    assert fl.is_premarket_event("2026-09-21T15:00:00Z") is False  # 11:00 ET


def test_is_premarket_event_false_for_post_close():
    assert fl.is_premarket_event("2026-09-21T21:30:00Z") is False  # 17:30 ET


def test_is_premarket_event_false_for_weekend():
    assert fl.is_premarket_event("2026-09-19T12:00:00Z") is False  # Saturday


def test_lag_seconds_computes_difference():
    assert fl.lag_seconds("2026-09-21T12:00:00Z", "2026-09-21T12:00:25Z") == pytest.approx(25.0)


def test_percentile_hand_computed():
    values = [10.0, 20.0, 30.0, 40.0, 50.0]
    assert fl._percentile(values, 50) == pytest.approx(30.0)
    assert fl._percentile(values, 90) == pytest.approx(46.0)
    assert fl._percentile(values, 95) == pytest.approx(48.0)


def test_seen_before_same_day_open_false_when_seen_next_day():
    # Caught during review: published pre-market Monday, but not seen
    # by the collector until 06:00 ET Tuesday -- Tuesday's own 09:30
    # boundary must NOT make this look like "seen before open."
    assert (
        fl._seen_before_same_day_open("2026-09-21T12:00:00Z", "2026-09-22T10:00:00Z") is False
    )


def test_seen_before_same_day_open_true_for_genuine_same_day_early_pickup():
    assert (
        fl._seen_before_same_day_open("2026-09-21T12:00:00Z", "2026-09-21T12:00:20Z") is True
    )


def test_compute_latency_stats_raises_on_zero_events():
    with pytest.raises(fl.FeedLatencyAuditError):
        fl.compute_latency_stats([], source="edgar_8k")


def test_compute_latency_stats_filters_by_source_and_event_type():
    events = [
        make_event(source="edgar_8k", type="earnings_release"),
        make_event(source="rss_news", type="earnings_release", source_id="acc-2"),
        make_event(source="edgar_8k", type="material_agreement", source_id="acc-3"),
    ]
    stats = fl.compute_latency_stats(events, source="edgar_8k", event_type="earnings_release")
    assert stats.total_premarket_events == 1


def test_compute_latency_stats_passes_when_both_bars_met():
    events = [
        make_event(
            source_id=f"acc-{i}",
            published_at="2026-09-21T12:00:00Z",
            first_seen_at="2026-09-21T12:00:10Z",  # 10s lag, well under 30s bar
        )
        for i in range(10)
    ]
    stats = fl.compute_latency_stats(events, source="edgar_8k")
    assert stats.share_seen_before_open == pytest.approx(1.0)
    assert stats.lag_seconds_p50 == pytest.approx(10.0)
    assert stats.passed is True


def test_compute_latency_stats_fails_on_share_even_if_lag_is_fast():
    # 5 of 10 seen before open (50% < 80% bar), but the ones that ARE
    # seen have a fast 5s lag -- must still fail, both bars required.
    fast_and_seen = [
        make_event(
            source_id=f"acc-seen-{i}",
            published_at="2026-09-21T12:00:00Z",
            first_seen_at="2026-09-21T12:00:05Z",
        )
        for i in range(5)
    ]
    fast_but_missed = [
        make_event(
            source_id=f"acc-missed-{i}",
            published_at="2026-09-21T12:00:00Z",
            first_seen_at="2026-09-22T10:00:00Z",  # next day -- not before open
        )
        for i in range(5)
    ]
    stats = fl.compute_latency_stats(fast_and_seen + fast_but_missed, source="edgar_8k")
    assert stats.share_seen_before_open == pytest.approx(0.5)
    assert stats.passed is False


def test_compute_latency_stats_fails_on_lag_even_if_share_is_high():
    # All 10 seen before open (100% >= 80% bar), but with a 45s lag,
    # over the 30s bar -- must still fail.
    events = [
        make_event(
            source_id=f"acc-{i}",
            published_at="2026-09-21T12:00:00Z",
            first_seen_at="2026-09-21T12:00:45Z",
        )
        for i in range(10)
    ]
    stats = fl.compute_latency_stats(events, source="edgar_8k")
    assert stats.share_seen_before_open == pytest.approx(1.0)
    assert stats.lag_seconds_p50 == pytest.approx(45.0)
    assert stats.passed is False


def test_render_report_includes_pass_and_fail_rows():
    events_pass = [
        make_event(
            source_id=f"acc-p-{i}",
            published_at="2026-09-21T12:00:00Z",
            first_seen_at="2026-09-21T12:00:10Z",
        )
        for i in range(5)
    ]
    events_fail = [
        make_event(
            source="rss_news",
            source_id=f"acc-f-{i}",
            published_at="2026-09-21T12:00:00Z",
            first_seen_at="2026-09-21T12:01:10Z",
        )
        for i in range(5)
    ]
    pass_stats = fl.compute_latency_stats(events_pass, source="edgar_8k")
    fail_stats = fl.compute_latency_stats(events_fail, source="rss_news")

    report = fl.render_report([pass_stats, fail_stats])
    assert "edgar_8k" in report
    assert "rss_news" in report
    assert "PASS" in report
    assert "FAIL" in report
