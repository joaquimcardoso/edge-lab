"""Point-in-time feature math: Wilder ATR / ATR%, average dollar
volume, and zero-intercept beta.

Formulas are not invented here -- they are already frozen in this
repository's experiment specs and matched exactly:
- ATRpct20 = ATR20(t-1) / close(t-1), Wilder's ATR specifically
  (docs/experiments/daily/EXP-002-intraday-continuation.md).
- ADV20 = 20-session trailing average DOLLAR volume
  (docs/strategies/swing.md, docs/experiments/swing/EXP-001-analyst-drift.md).
- beta: zero-intercept ("zero-alpha") market model,
  AR = R_stock - beta * R_market, 252-day window, minimum 60
  observations (docs/01-point-in-time-rules.md §5,
  docs/05-experiment-protocol.md).

Every rolling function here is pure (no I/O, no database access) --
build_features_as_of, the only function that touches the price
store, is what enforces "point-in-time only" by never reading a
price_daily row on or after as_of_date in the first place, not just
excluding it from the final number after the fact.

Story: stories/STORY-006-feature-builder.md
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Union
from pathlib import Path

from edgelab.storage.price_store import read_price_bars_for_security

PathLike = Union[str, "Path"]

ATR_WINDOW = 20
ADV_WINDOW = 20
BETA_WINDOW = 252
BETA_MIN_OBSERVATIONS = 60


def true_range(high: float, low: float, prev_close: float) -> float:
    """max(high-low, |high-prev_close|, |low-prev_close|)."""
    return max(high - low, abs(high - prev_close), abs(low - prev_close))


def wilder_atr(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    *,
    window: int = ATR_WINDOW,
) -> List[Optional[float]]:
    """Wilder's ATR, aligned to the input series (same length).

    The first True Range needs a previous close, so index 0 is always
    None. The first `window` True Ranges (indices 1..window) are
    needed before the first ATR value exists (simple average of
    those); every value after that uses Wilder's smoothing:
    ATR_t = (ATR_{t-1} * (window - 1) + TR_t) / window.
    """
    n = len(highs)
    if not (n == len(lows) == len(closes)):
        raise ValueError("highs, lows and closes must be the same length")

    true_ranges: List[Optional[float]] = [None] * n
    for i in range(1, n):
        true_ranges[i] = true_range(highs[i], lows[i], closes[i - 1])

    atr: List[Optional[float]] = [None] * n
    first_atr_index = window  # need TR[1..window] = window values
    if n > first_atr_index:
        window_trs = true_ranges[1 : first_atr_index + 1]
        if all(tr is not None for tr in window_trs):
            atr[first_atr_index] = sum(window_trs) / window  # type: ignore[arg-type]

        for i in range(first_atr_index + 1, n):
            prev_atr = atr[i - 1]
            tr = true_ranges[i]
            if prev_atr is None or tr is None:
                continue
            atr[i] = (prev_atr * (window - 1) + tr) / window

    return atr


def atr_pct(
    atr_values: Sequence[Optional[float]], closes: Sequence[float]
) -> List[Optional[float]]:
    """atr / close, element-wise; None where atr is None."""
    if len(atr_values) != len(closes):
        raise ValueError("atr_values and closes must be the same length")
    return [
        (atr / close if atr is not None and close else None)
        for atr, close in zip(atr_values, closes)
    ]


def average_dollar_volume(
    closes: Sequence[float], volumes: Sequence[float], *, window: int = ADV_WINDOW
) -> List[Optional[float]]:
    """Trailing `window`-session mean of close * volume, None until
    `window` observations exist.
    """
    if len(closes) != len(volumes):
        raise ValueError("closes and volumes must be the same length")
    dollar_volume = [c * v for c, v in zip(closes, volumes)]
    n = len(dollar_volume)
    result: List[Optional[float]] = [None] * n
    for i in range(window - 1, n):
        window_slice = dollar_volume[i - window + 1 : i + 1]
        result[i] = sum(window_slice) / window
    return result


def zero_intercept_beta(
    stock_returns: Sequence[float],
    market_returns: Sequence[float],
    *,
    window: int = BETA_WINDOW,
    min_observations: int = BETA_MIN_OBSERVATIONS,
) -> Optional[float]:
    """beta = sum(R_market * R_stock) / sum(R_market^2) over the most
    recent `window` paired returns (or fewer, down to
    min_observations) -- the OLS estimator for a no-intercept
    (zero-alpha) regression, deliberately not cov/var, which assumes
    a model with an intercept this one doesn't have.

    Returns None if fewer than min_observations paired returns exist.
    """
    if len(stock_returns) != len(market_returns):
        raise ValueError("stock_returns and market_returns must be the same length")

    paired = list(zip(stock_returns, market_returns))[-window:]
    if len(paired) < min_observations:
        return None

    numerator = sum(r_m * r_s for r_s, r_m in paired)
    denominator = sum(r_m * r_m for _r_s, r_m in paired)
    if denominator == 0:
        return None
    return numerator / denominator


@dataclass(frozen=True)
class PointInTimeFeatures:
    security_id: str
    as_of_date: str
    atr20: Optional[float]
    atr_pct20: Optional[float]
    adv20: Optional[float]
    beta252: Optional[float]


def build_features_as_of(
    security_id: str,
    market_security_id: str,
    as_of_date: str,
    *,
    price_db_path: PathLike,
) -> PointInTimeFeatures:
    """Compute ATR20 / ATRpct20 / ADV20 / beta252 for `security_id` as
    of `as_of_date`, using ONLY price_daily rows with date < as_of_date
    -- the cutoff is enforced at the read, so a caller cannot
    accidentally leak a same-day or future row into the computation.
    """
    security_bars = [
        bar
        for bar in read_price_bars_for_security(security_id, db_path=price_db_path)
        if bar.date < as_of_date
    ]
    market_bars = [
        bar
        for bar in read_price_bars_for_security(market_security_id, db_path=price_db_path)
        if bar.date < as_of_date
    ]

    highs = [bar.high for bar in security_bars]
    lows = [bar.low for bar in security_bars]
    closes = [bar.close for bar in security_bars]
    volumes = [bar.volume for bar in security_bars]

    atr_series = wilder_atr(highs, lows, closes)
    atr_pct_series = atr_pct(atr_series, closes)
    adv_series = average_dollar_volume(closes, volumes)

    atr20 = atr_series[-1] if atr_series else None
    atr_pct20 = atr_pct_series[-1] if atr_pct_series else None
    adv20 = adv_series[-1] if adv_series else None

    stock_returns, market_returns = _date_aligned_returns(
        security_bars, market_bars, window=BETA_WINDOW
    )
    beta252 = zero_intercept_beta(stock_returns, market_returns)

    return PointInTimeFeatures(
        security_id=security_id,
        as_of_date=as_of_date,
        atr20=atr20,
        atr_pct20=atr_pct20,
        adv20=adv20,
        beta252=beta252,
    )


def _simple_returns(prices: Sequence[float]) -> List[float]:
    return [
        (prices[i] / prices[i - 1]) - 1.0
        for i in range(1, len(prices))
        if prices[i - 1] != 0
    ]


def _date_aligned_returns(security_bars, market_bars, *, window: int):
    """Pair stock and market returns by actual trading date, not by
    trailing list position -- caught during review: truncating each
    return series to the same LENGTH from the end silently misaligns
    the pairs whenever one series has a gap the other doesn't (a
    delisting, a missing bar), which zero_intercept_beta cannot
    detect on its own since it only sees two same-length sequences.
    """
    security_by_date = {bar.date: bar.adj_close for bar in security_bars}
    market_by_date = {bar.date: bar.adj_close for bar in market_bars}
    common_dates = sorted(set(security_by_date) & set(market_by_date))
    # window+1 prices are needed to derive `window` returns.
    common_dates = common_dates[-(window + 1) :]

    stock_prices = [security_by_date[d] for d in common_dates]
    market_prices = [market_by_date[d] for d in common_dates]
    return _simple_returns(stock_prices), _simple_returns(market_prices)
