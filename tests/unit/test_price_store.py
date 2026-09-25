"""Unit tests for src/edgelab/storage/price_store.py."""

from __future__ import annotations

from edgelab.storage import price_store as ps


def make_bar(**overrides):
    defaults = dict(
        security_id="0000320193",
        date="2026-09-20",
        open=225.0,
        high=228.5,
        low=224.1,
        close=227.0,
        adj_close=227.0,
        volume=54_000_000,
        snapshot_id=1,
    )
    defaults.update(overrides)
    return ps.PriceBar(**defaults)


def test_write_and_read_round_trip(tmp_path):
    db_path = tmp_path / "prices.sqlite3"
    written = ps.write_price_bar(make_bar(), db_path=db_path)

    assert written.price_id is not None
    read_back = ps.read_price_bar(written.price_id, db_path=db_path)
    assert read_back == written


def test_write_is_deduplicated_on_security_and_date(tmp_path):
    db_path = tmp_path / "prices.sqlite3"
    first = ps.write_price_bar(make_bar(), db_path=db_path)
    second = ps.write_price_bar(make_bar(), db_path=db_path)

    assert first.price_id == second.price_id
    assert len(ps.read_price_bars_for_security("0000320193", db_path=db_path)) == 1


def test_different_date_same_security_is_not_deduplicated(tmp_path):
    db_path = tmp_path / "prices.sqlite3"
    ps.write_price_bar(make_bar(date="2026-09-20"), db_path=db_path)
    ps.write_price_bar(make_bar(date="2026-09-21"), db_path=db_path)

    assert len(ps.read_price_bars_for_security("0000320193", db_path=db_path)) == 2


def test_read_price_bars_for_security_is_sorted_by_date(tmp_path):
    db_path = tmp_path / "prices.sqlite3"
    ps.write_price_bar(make_bar(date="2026-09-22"), db_path=db_path)
    ps.write_price_bar(make_bar(date="2026-09-20"), db_path=db_path)
    ps.write_price_bar(make_bar(date="2026-09-21"), db_path=db_path)

    dates = [bar.date for bar in ps.read_price_bars_for_security("0000320193", db_path=db_path)]
    assert dates == ["2026-09-20", "2026-09-21", "2026-09-22"]


def test_reading_unknown_price_id_raises_key_error(tmp_path):
    db_path = tmp_path / "prices.sqlite3"
    ps._connect(db_path).close()
    try:
        ps.read_price_bar(9999, db_path=db_path)
        raise AssertionError("expected KeyError")
    except KeyError:
        pass
