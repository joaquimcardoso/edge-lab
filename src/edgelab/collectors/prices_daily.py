"""`prices_daily` collector.

Fetches one security's daily OHLCV history from yfinance for a date
range and persists it as an immutable raw snapshot
(src/edgelab/storage/raw_snapshot.py).

Schema/behaviour note: yfinance is explicitly unofficial and fragile
(docs/02-data-sources.md#yfinance) -- every call here is wrapped, and
a failure (an exception, or a zero-row result, which yfinance can
return instead of raising) is surfaced as PricesDailyError rather
than silently treated as "no prices for this range"
(docs/04-infrastructure.md: never converted into "no event").

The HTTP/yfinance call is injected (a HistoryFetcher protocol) so
tests never touch the network -- this sandbox's egress does not
reach Yahoo Finance (verified during STORY-002), and a live call in
an automated suite would be flaky regardless.

What gets stored as "raw" here is yfinance's own parsed result,
serialised to CSV -- not Yahoo's original wire bytes. See STORY-004's
explicit scope boundary for why: reimplementing yfinance's own
cookie/crumb HTTP layer to capture truly raw bytes would be a worse
trade than accepting this one processing layer's remove.

Story: stories/STORY-004-prices-daily-collector.md
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Protocol, Union

from edgelab.storage.raw_snapshot import RawSnapshot, write_raw_snapshot

PathLike = Union[str, "Path"]


class PricesDailyError(RuntimeError):
    """Raised when yfinance fails or returns nothing usable.

    Deliberately not caught anywhere in this module -- per
    docs/04-infrastructure.md, a collector failure must be logged and
    alerted by the caller, never silently read as "no prices today."
    """


class HistoryFetcher(Protocol):
    def fetch(self, ticker: str, *, start: str, end: str):  # -> pandas.DataFrame-like
        ...


class YFinanceHistoryFetcher:
    """Default HistoryFetcher, wrapping the yfinance library.

    auto_adjust=False and actions=False so the result carries both
    raw Close and a separate Adj Close column (01-point-in-time-rules.md
    §12: adjusted close for returns/rolling stats, raw close for gaps)
    without extra Dividends/Stock Splits columns this story doesn't use.
    """

    def fetch(self, ticker: str, *, start: str, end: str):
        import yfinance as yf  # imported lazily: only the real fetcher needs it

        return yf.Ticker(ticker).history(
            start=start,
            end=end,
            interval="1d",
            auto_adjust=False,
            actions=False,
            raise_errors=True,
        )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _dataframe_to_csv_bytes(df) -> bytes:
    """Serialise a yfinance-shaped DataFrame (DatetimeIndex named
    'Date', columns Open/High/Low/Close/'Adj Close'/Volume) to CSV
    bytes with a plain 'date' column, ready for parse_price_csv.
    """
    reset = df.reset_index()
    date_column = reset.columns[0]  # "Date" (or "Datetime" for intraday, unused here)
    reset = reset.rename(columns={date_column: "date"})
    reset["date"] = reset["date"].astype(str).str.slice(0, 10)  # YYYY-MM-DD, tz-agnostic
    buffer = io.StringIO()
    reset.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")


def collect_prices_daily(
    ticker: str,
    *,
    start: str,
    end: str,
    history_fetcher: HistoryFetcher,
    db_path: PathLike,
    data_dir: PathLike,
    now: Callable[[], str] = _utc_now_iso,
) -> RawSnapshot:
    """Fetch one ticker's daily OHLCV for [start, end) and persist it
    as a single raw snapshot. Raises PricesDailyError on any fetch
    failure or an empty result -- never silently a no-op.
    """
    try:
        df = history_fetcher.fetch(ticker, start=start, end=end)
    except Exception as exc:  # yfinance's own exception types vary by failure mode
        raise PricesDailyError(
            f"yfinance fetch failed for {ticker} [{start}, {end}): {exc}"
        ) from exc

    if df is None or len(df) == 0:
        raise PricesDailyError(
            f"yfinance returned no rows for {ticker} [{start}, {end}) "
            "-- treated as a failure, not 'no prices', per docs/02-data-sources.md"
        )

    payload = _dataframe_to_csv_bytes(df)
    return write_raw_snapshot(
        "prices_daily",
        now(),
        payload,
        db_path=db_path,
        data_dir=data_dir,
        url=f"yfinance:{ticker}:{start}:{end}",
    )


@dataclass(frozen=True)
class PriceRow:
    date: str
    open: float
    high: float
    low: float
    close: float
    adj_close: float
    volume: int


def parse_price_csv(raw_csv: bytes) -> "list[PriceRow]":
    """Parse a prices_daily raw snapshot's CSV bytes into typed rows.

    Deliberately independent of pandas/yfinance -- raw bytes in,
    plain rows out -- so a snapshot stored years ago can still be
    re-parsed after the fetch-time library has changed or is gone.
    A row missing a required numeric field is skipped, not fatal to
    the rest of the file (consistent with STORY-002/003's "one bad
    record never blocks the rest").
    """
    text = raw_csv.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    total_seen = 0
    for record in reader:
        total_seen += 1
        try:
            rows.append(
                PriceRow(
                    date=record["date"][:10],
                    open=float(record["Open"]),
                    high=float(record["High"]),
                    low=float(record["Low"]),
                    close=float(record["Close"]),
                    adj_close=float(record["Adj Close"]),
                    volume=int(float(record["Volume"])),
                )
            )
        except (KeyError, ValueError):
            continue

    if total_seen > 0 and not rows:
        # Every row failed to parse -- almost certainly a column-schema
        # mismatch (e.g. yfinance renamed "Adj Close"), not "no prices
        # for this range." Silently returning [] here would be exactly
        # the "failure converted into no event" docs/04-infrastructure.md
        # forbids -- caught during review, before any test was written.
        raise PricesDailyError(
            f"found {total_seen} CSV row(s) in the raw snapshot but parsed 0 -- "
            "likely a column-schema mismatch, not an empty result"
        )
    return rows
