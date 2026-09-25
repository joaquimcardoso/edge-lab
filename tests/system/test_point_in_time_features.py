"""System-level test for the point-in-time feature builder (STORY-006).

Writes price_daily rows through STORY-004's real store for both a
security and a market benchmark, then runs build_features_as_of
end-to-end, verifying it composes correctly with the real store (not
just with a hand-built PriceBar list in the unit test).

Regression fixture set: still vacuous -- no experiment is FROZEN yet.
"""

from __future__ import annotations

from edgelab.features.point_in_time import build_features_as_of
from edgelab.storage.price_store import PriceBar, write_price_bar


def test_build_features_as_of_end_to_end_through_real_price_store(tmp_path):
    price_db_path = tmp_path / "prices.sqlite3"

    dates = [f"2026-08-{d:02d}" for d in range(1, 26)]  # 25 trading days
    as_of_date = "2026-08-26"

    for i, d in enumerate(dates):
        write_price_bar(
            PriceBar(
                security_id="AAPL_CIK",
                date=d,
                open=200 + i * 0.5,
                high=202 + i * 0.5,
                low=198 + i * 0.5,
                close=200 + i * 0.5,
                adj_close=200 + i * 0.5,
                volume=50_000_000 + i * 100_000,
                snapshot_id=1,
            ),
            db_path=price_db_path,
        )
        write_price_bar(
            PriceBar(
                security_id="SPY",
                date=d,
                open=500 + i * 0.3,
                high=502 + i * 0.3,
                low=498 + i * 0.3,
                close=500 + i * 0.3,
                adj_close=500 + i * 0.3,
                volume=80_000_000,
                snapshot_id=1,
            ),
            db_path=price_db_path,
        )

    features = build_features_as_of(
        "AAPL_CIK", "SPY", as_of_date, price_db_path=price_db_path
    )

    assert features.security_id == "AAPL_CIK"
    assert features.as_of_date == as_of_date
    assert features.atr20 is not None
    assert features.atr_pct20 is not None
    assert features.adv20 is not None
    # 25 bars < 60 observations required for beta -> None, correctly,
    # not a crash and not a fabricated number from too little data.
    assert features.beta252 is None


def test_build_features_as_of_computes_beta_once_enough_history_exists(tmp_path):
    price_db_path = tmp_path / "prices.sqlite3"

    dates = [f"2026-{7 + (d // 28):02d}-{(d % 28) + 1:02d}" for d in range(65)]
    as_of_date = "2026-10-10"

    for i, d in enumerate(dates):
        # Market moves by a clean pattern; security tracks it at 1.5x,
        # so beta should recover close to 1.5.
        market_close = 500 + i * 0.2 * (-1 if i % 2 else 1)
        security_close = 200 + i * 0.3 * (-1 if i % 2 else 1)
        write_price_bar(
            PriceBar(
                security_id="SEC",
                date=d,
                open=security_close,
                high=security_close + 1,
                low=security_close - 1,
                close=security_close,
                adj_close=security_close,
                volume=10_000_000,
                snapshot_id=1,
            ),
            db_path=price_db_path,
        )
        write_price_bar(
            PriceBar(
                security_id="MKT",
                date=d,
                open=market_close,
                high=market_close + 1,
                low=market_close - 1,
                close=market_close,
                adj_close=market_close,
                volume=20_000_000,
                snapshot_id=1,
            ),
            db_path=price_db_path,
        )

    features = build_features_as_of("SEC", "MKT", as_of_date, price_db_path=price_db_path)
    assert features.beta252 is not None
