"""Entrypoint: one-time historical backfill, run by hand, never on a
schedule -- unlike scripts/collect_premarket_8k.py and
scripts/build_daily_report.py, which STORY-008/010 install as
systemd timers.

Two independent halves, because they have genuinely different
point-in-time safety properties (discovered while designing this
story, not assumed going in):

  - 8-K: RAW SNAPSHOTS ONLY. Reuses collect_8k_for_cik as-is to pull
    whatever SEC EDGAR's `filings.recent` window currently returns
    (documented gap: roughly the last year; older history needs
    `filings.files` pagination, not implemented here -- a named
    follow-on). These snapshots are deliberately never passed to
    normalise_snapshot: that normaliser sets
    known_at = first_seen_at (01-point-in-time-rules.md Sec.2,
    the "live-collected" rule) -- correct when first_seen_at is a
    real-time collection timestamp, but wrong for a backfilled
    snapshot, where first_seen_at is today's backfill run time, not
    when the filing was actually knowable historically. Every
    CikOutcome this half returns has events_written == 0 -- that is
    this function's whole point, not a bug.
  - Prices: collected AND normalised, fully safe today. PriceBar
    (src/edgelab/storage/price_store.py) has no known_at/first_seen_at
    field at all -- daily OHLCV bars carry no live-vs-historical
    timing ambiguity this repository tracks -- so backfilled price
    history is immediately usable, unlike the 8-K half above.

Story: stories/STORY-014-historical-backfill.md
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple

from collect_premarket_8k import CikOutcome, RunSummary, append_failure_log, load_universe

from edgelab.collectors.edgar_8k import CollectionFailure, HttpClient, collect_8k_for_cik
from edgelab.collectors.prices_daily import HistoryFetcher, PricesDailyError, collect_prices_daily
from edgelab.config import CollectorConfig, load_collector_config
from edgelab.normalisers.prices_daily import normalise_prices_daily_snapshot

logger = logging.getLogger("edgelab.backfill_historical")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def backfill_8k(
    cik_ticker_pairs: Sequence[Tuple[str, str]],
    *,
    http_client: HttpClient,
    config: CollectorConfig,
) -> RunSummary:
    """Collect raw 8-K snapshots for the SEC "recent filings" window --
    raw only, see module docstring for why normalise_snapshot is
    deliberately never called here.
    """
    outcomes: List[CikOutcome] = []
    for ticker, cik in cik_ticker_pairs:
        try:
            result = collect_8k_for_cik(
                cik,
                http_client=http_client,
                user_agent=config.sec_user_agent,
                db_path=config.raw_db_path,
                data_dir=config.data_dir,
            )
        except Exception as exc:  # noqa: BLE001 -- logged and recorded, never swallowed
            logger.error("8-K backfill failed for %s (cik=%s): %s", ticker, cik, exc)
            outcomes.append(
                CikOutcome(
                    ticker=ticker,
                    cik=cik,
                    snapshots_written=0,
                    events_written=0,
                    failures=(CollectionFailure(accession_number="", url="", reason=str(exc)),),
                )
            )
            continue

        outcomes.append(
            CikOutcome(
                ticker=ticker,
                cik=cik,
                snapshots_written=len(result.snapshots),
                events_written=0,  # deliberate: raw only, see module docstring
                failures=result.failures,
            )
        )

    return RunSummary(outcomes=tuple(outcomes))


@dataclass(frozen=True)
class PriceFailure:
    ticker: str
    reason: str


@dataclass(frozen=True)
class PriceOutcome:
    ticker: str
    cik: str
    bars_written: int
    failure: Optional[PriceFailure] = None


@dataclass(frozen=True)
class PriceRunSummary:
    outcomes: Tuple[PriceOutcome, ...] = field(default_factory=tuple)

    @property
    def total_bars(self) -> int:
        return sum(o.bars_written for o in self.outcomes)

    @property
    def tickers_with_failures(self) -> Tuple[str, ...]:
        return tuple(o.ticker for o in self.outcomes if o.failure is not None)


def backfill_prices(
    cik_ticker_pairs: Sequence[Tuple[str, str]],
    *,
    history_fetcher: HistoryFetcher,
    config: CollectorConfig,
    start: str,
    end: str,
) -> PriceRunSummary:
    """Collect and normalise daily price history for every (ticker,
    cik) pair over [start, end). A single ticker's failure never
    stops the rest of the universe -- same isolation principle as
    backfill_8k and STORY-008's run().
    """
    outcomes: List[PriceOutcome] = []
    for ticker, cik in cik_ticker_pairs:
        try:
            snapshot = collect_prices_daily(
                ticker,
                start=start,
                end=end,
                history_fetcher=history_fetcher,
                db_path=config.raw_db_path,
                data_dir=config.data_dir,
            )
        except PricesDailyError as exc:
            logger.error("price backfill failed for %s (cik=%s): %s", ticker, cik, exc)
            outcomes.append(
                PriceOutcome(
                    ticker=ticker, cik=cik, bars_written=0,
                    failure=PriceFailure(ticker=ticker, reason=str(exc)),
                )
            )
            continue

        result = normalise_prices_daily_snapshot(
            snapshot.id, cik, raw_db_path=config.raw_db_path, price_db_path=config.price_db_path
        )
        outcomes.append(
            PriceOutcome(ticker=ticker, cik=cik, bars_written=len(result.bars_written))
        )

    return PriceRunSummary(outcomes=tuple(outcomes))


def append_price_failure_log(
    summary: PriceRunSummary, *, log_dir: Path, now: Callable[[], str] = _utc_now_iso
) -> int:
    """Same append-only JSONL failure-log pattern as
    collect_premarket_8k.append_failure_log, sized to PriceFailure's
    simpler (ticker, reason) shape rather than CollectionFailure's
    (accession_number, url, reason) -- the two failure shapes don't
    match closely enough to reuse the same writer.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "price_backfill_failures.jsonl"
    timestamp = now()
    written = 0
    with log_path.open("a") as fh:
        for outcome in summary.outcomes:
            if outcome.failure is None:
                continue
            fh.write(
                json.dumps(
                    {
                        "timestamp": timestamp,
                        "ticker": outcome.failure.ticker,
                        "cik": outcome.cik,
                        "reason": outcome.failure.reason,
                    }
                )
                + "\n"
            )
            written += 1
    return written


def _default_price_start(today: Optional[datetime] = None) -> str:
    reference = today or datetime.now(timezone.utc)
    return (reference - timedelta(days=5 * 365)).date().isoformat()


def _default_price_end(today: Optional[datetime] = None) -> str:
    # yfinance's `end` is exclusive; default to yesterday so a run on
    # any given day never asks for a day that hasn't closed yet.
    reference = today or datetime.now(timezone.utc)
    return (reference - timedelta(days=1)).date().isoformat()


def main(argv: Optional[Sequence[str]] = None) -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=["8k", "prices", "both"], default="both")
    parser.add_argument(
        "--start", default=None,
        help="Prices backfill start date YYYY-MM-DD (default: ~5 years back)",
    )
    parser.add_argument(
        "--end", default=None,
        help="Prices backfill end date YYYY-MM-DD, exclusive (default: yesterday)",
    )
    args = parser.parse_args(argv)

    config = load_collector_config()
    config.data_dir.mkdir(parents=True, exist_ok=True)
    universe = load_universe(config.universe_path)

    if args.kind in ("8k", "both"):
        from edgelab.net.requests_http_client import RequestsHttpClient

        summary = backfill_8k(universe, http_client=RequestsHttpClient(), config=config)
        append_failure_log(summary, log_dir=config.log_dir)
        logger.info(
            "8-K backfill complete: %d raw snapshots written (0 events -- raw only, "
            "see module docstring), %d CIKs with failures",
            summary.total_snapshots,
            len(summary.ciks_with_failures),
        )

    if args.kind in ("prices", "both"):
        from edgelab.collectors.prices_daily import YFinanceHistoryFetcher

        start = args.start or _default_price_start()
        end = args.end or _default_price_end()
        price_summary = backfill_prices(
            universe,
            history_fetcher=YFinanceHistoryFetcher(),
            config=config,
            start=start,
            end=end,
        )
        append_price_failure_log(price_summary, log_dir=config.log_dir)
        logger.info(
            "price backfill complete [%s, %s): %d bars written, %d tickers with failures",
            start,
            end,
            price_summary.total_bars,
            len(price_summary.tickers_with_failures),
        )


if __name__ == "__main__":
    main()
