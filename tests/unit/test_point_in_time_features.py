"""Unit tests for src/edgelab/features/point_in_time.py.

Wilder ATR and average-dollar-volume expectations below are
hand-computed (see the story's dev notes) and cross-checked by
running the implementation once and reading off its own output --
this file pins those numbers so a later change can't silently drift
the formula.
"""

from __future__ import annotations

import pytest

from edgelab.features import point_in_time as feat
from edgelab.storage.price_store import PriceBar, write_price_bar


def test_true_range_normal_day():
    # No gap: the day's own range dominates.
    assert feat.true_range(high=12, low=10, prev_close=11) == 2


def test_true_range_gap_up():
    # Gap up through the prior close: |high - prev_close| dominates.
    assert feat.true_range(high=15, low=13, prev_close=10) == 5


def test_true_range_gap_down():
    # Gap down through the prior close: |low - prev_close| dominates.
    assert feat.true_range(high=9, low=7, prev_close=12) == 5


def test_wilder_atr_hand_computed_series():
    highs = [10, 11, 12, 11, 13, 14]
    lows = [8, 9, 10, 9, 11, 12]
    closes = [9, 10, 11, 10, 12, 13]

    atr = feat.wilder_atr(highs, lows, closes, window=3)

    assert atr[0] is None
    assert atr[1] is None
    assert atr[2] is None
    assert atr[3] == pytest.approx(2.0)
    assert atr[4] == pytest.approx(7 / 3)
    assert atr[5] == pytest.approx(20 / 9)  # Wilder smoothing, not a simple mean of TR[3:6]


def test_wilder_atr_is_not_a_simple_moving_average():
    # If this were a plain SMA of the last `window` True Ranges, atr[5]
    # would equal mean(TR[3], TR[4], TR[5]) = mean(2, 3, 2) = 2.3333...
    # Wilder's smoothing gives a different number (20/9 ~= 2.2222) because
    # it carries forward the prior ATR rather than re-averaging a window.
    highs = [10, 11, 12, 11, 13, 14]
    lows = [8, 9, 10, 9, 11, 12]
    closes = [9, 10, 11, 10, 12, 13]
    atr = feat.wilder_atr(highs, lows, closes, window=3)
    simple_mean_of_last_three_tr = (2 + 3 + 2) / 3
    assert atr[5] != pytest.approx(simple_mean_of_last_three_tr)


def test_wilder_atr_insufficient_data_is_all_none():
    atr = feat.wilder_atr([10, 11], [8, 9], [9, 10], window=20)
    assert atr == [None, None]


def test_wilder_atr_default_window_is_twenty():
    # 22 bars: exactly enough for one ATR20 value using the default window.
    highs = [10 + i * 0.1 for i in range(22)]
    lows = [8 + i * 0.1 for i in range(22)]
    closes = [9 + i * 0.1 for i in range(22)]
    atr = feat.wilder_atr(highs, lows, closes)
    assert atr[19] is None
    assert atr[20] is not None
    assert atr[21] is not None


def test_atr_pct_divides_elementwise_and_handles_none():
    atr_values = [None, 2.0, 4.0]
    closes = [10.0, 20.0, 40.0]
    assert feat.atr_pct(atr_values, closes) == [None, pytest.approx(0.1), pytest.approx(0.1)]


def test_average_dollar_volume_hand_computed():
    closes = [10, 11, 12, 10, 12, 13]
    volumes = [100, 200, 150, 300, 250, 400]

    adv = feat.average_dollar_volume(closes, volumes, window=3)

    assert adv[0] is None
    assert adv[1] is None
    assert adv[2] == pytest.approx(5000 / 3)
    assert adv[3] == pytest.approx(7000 / 3)
    assert adv[4] == pytest.approx(2600.0)
    assert adv[5] == pytest.approx(11200 / 3)


def test_zero_intercept_beta_recovers_exact_known_beta_with_no_noise():
    market_returns = [0.001 * i * (-1 if i % 2 else 1) for i in range(1, 61)]
    stock_returns = [2.5 * r for r in market_returns]  # exact beta = 2.5, no noise

    beta = feat.zero_intercept_beta(stock_returns, market_returns, min_observations=60)
    assert beta == pytest.approx(2.5)


def test_zero_intercept_beta_is_not_cov_over_var():
    # A constructed case where a nonzero mean makes cov/var and the
    # zero-intercept estimator genuinely differ, to prove this isn't
    # accidentally computing the with-intercept formula.
    market_returns = [0.02] * 59 + [0.03]
    stock_returns = [0.01] * 59 + [0.09]

    beta = feat.zero_intercept_beta(stock_returns, market_returns, min_observations=60)
    numerator = sum(m * s for s, m in zip(stock_returns, market_returns))
    denominator = sum(m * m for m in market_returns)
    assert beta == pytest.approx(numerator / denominator)

    # cov/var would give a different number here -- sanity-check they diverge.
    import statistics

    cov = statistics.covariance(market_returns, stock_returns)
    var = statistics.variance(market_returns)
    cov_over_var_beta = cov / var
    assert beta != pytest.approx(cov_over_var_beta)


def test_zero_intercept_beta_returns_none_below_min_observations():
    market_returns = [0.01] * 30
    stock_returns = [0.02] * 30
    assert feat.zero_intercept_beta(stock_returns, market_returns, min_observations=60) is None


def test_zero_intercept_beta_uses_trailing_window_only():
    # An outlier far in the past (outside the window) must not affect beta.
    old_outliers_market = [10.0] * 5
    old_outliers_stock = [-500.0] * 5  # would badly distort beta if included
    recent_market = [0.001 * i for i in range(1, 61)]
    recent_stock = [3.0 * r for r in recent_market]

    market_returns = old_outliers_market + recent_market
    stock_returns = old_outliers_stock + recent_stock

    beta = feat.zero_intercept_beta(stock_returns, market_returns, window=60, min_observations=60)
    assert beta == pytest.approx(3.0)


def _write_bars(bars, *, db_path):
    for bar in bars:
        write_price_bar(bar, db_path=db_path)


def test_build_features_as_of_never_reads_same_day_or_future_rows(tmp_path):
    price_db_path = tmp_path / "prices.sqlite3"

    # 22 trading days of clean data for both the security and the
    # market benchmark, PLUS a same-day row for as_of_date with an
    # absurd price that would obviously corrupt every feature if it
    # leaked into the computation.
    dates = [f"2026-08-{d:02d}" for d in range(1, 23)]  # 22 days
    as_of_date = "2026-09-01"

    security_bars = [
        PriceBar(
            security_id="SEC",
            date=d,
            open=100 + i,
            high=101 + i,
            low=99 + i,
            close=100 + i,
            adj_close=100 + i,
            volume=1_000_000,
            snapshot_id=1,
        )
        for i, d in enumerate(dates)
    ]
    market_bars = [
        PriceBar(
            security_id="MKT",
            date=d,
            open=200 + i,
            high=201 + i,
            low=199 + i,
            close=200 + i,
            adj_close=200 + i,
            volume=2_000_000,
            snapshot_id=1,
        )
        for i, d in enumerate(dates)
    ]
    # The trap: a same-day row with a wild price, present in the store.
    poison_bar = PriceBar(
        security_id="SEC",
        date=as_of_date,
        open=999999,
        high=999999,
        low=1,
        close=999999,
        adj_close=999999,
        volume=1,
        snapshot_id=1,
    )

    _write_bars(security_bars + [poison_bar], db_path=price_db_path)
    _write_bars(market_bars, db_path=price_db_path)

    features = feat.build_features_as_of("SEC", "MKT", as_of_date, price_db_path=price_db_path)

    # If the poison row had leaked in, ATR/ADV would be enormous.
    assert features.atr20 is not None
    assert features.atr20 < 100
    assert features.adv20 is not None
    assert features.adv20 < 1e10
