"""Entrypoint: poll EDGAR 8-K for a universe of companies and
normalise whatever raw snapshots that produces into the event store.

This is the script systemd invokes (deploy/edgelab-8k-poll.service).
All the actual logic already exists as tested library code
(collectors/edgar_8k.py, normalisers/edgar_8k.py) -- this module's
only job is wiring: read config and the universe file, call the
collector once per CIK, normalise every snapshot it wrote, and return
a summary that tells three outcomes apart instead of collapsing them:

  - a CIK with new filings, collected and normalised successfully
  - a CIK whose collection failed (network/SEC error) -- logged,
    never silently treated as "no filings today" (04-infrastructure's
    failure-handling rule)
  - a CIK with zero matching filings today -- a legitimate, distinct
    outcome, not an error

Story: stories/STORY-008-pi-collector-entrypoint.md
"""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Sequence, Tuple

from edgelab.collectors.edgar_8k import CollectionFailure, HttpClient, collect_8k_for_cik
from edgelab.config import CollectorConfig, load_collector_config
from edgelab.normalisers.edgar_8k import normalise_snapshot

logger = logging.getLogger("edgelab.collect_premarket_8k")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class UniverseError(RuntimeError):
    """The universe file is missing, empty, or malformed."""


@dataclass(frozen=True)
class CikOutcome:
    ticker: str
    cik: str
    snapshots_written: int
    events_written: int
    failures: Tuple[CollectionFailure, ...] = ()


@dataclass(frozen=True)
class RunSummary:
    outcomes: Tuple[CikOutcome, ...] = field(default_factory=tuple)

    @property
    def total_snapshots(self) -> int:
        return sum(o.snapshots_written for o in self.outcomes)

    @property
    def total_events(self) -> int:
        return sum(o.events_written for o in self.outcomes)

    @property
    def ciks_with_failures(self) -> Tuple[str, ...]:
        return tuple(o.cik for o in self.outcomes if o.failures)


def load_universe(universe_path: Path) -> List[Tuple[str, str]]:
    """Read (ticker, cik) pairs from a CSV with a `ticker,cik` header.

    Raises UniverseError -- never returns an empty list silently --
    for a missing file, a missing/wrong header, or a file with a
    header but zero data rows, since a run(...) call with no CIKs to
    poll must never be mistaken for "polled everything, found
    nothing today."
    """
    if not universe_path.exists():
        raise UniverseError(
            f"universe file not found: {universe_path} "
            "(see config/universe.csv and docs/08-credentials.md)"
        )
    with universe_path.open(newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None or not {"ticker", "cik"}.issubset(reader.fieldnames):
            raise UniverseError(
                f"{universe_path} must have a header with at least 'ticker,cik' columns"
            )
        pairs = [
            (row["ticker"].strip(), row["cik"].strip())
            for row in reader
            if row.get("ticker", "").strip() and row.get("cik", "").strip()
        ]
    if not pairs:
        raise UniverseError(f"{universe_path} has a header but no data rows")
    return pairs


def run(
    cik_ticker_pairs: Sequence[Tuple[str, str]],
    *,
    http_client: HttpClient,
    config: CollectorConfig,
) -> RunSummary:
    """Collect and normalise 8-K filings for every (ticker, cik) pair.

    A single CIK's collection failure never stops the run for the
    remaining CIKs -- one company's outage must not blind the whole
    universe for that poll.
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
            logger.error("collection failed for %s (cik=%s): %s", ticker, cik, exc)
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

        events_written = 0
        normalise_failures: List[CollectionFailure] = []
        for snapshot in result.snapshots:
            try:
                normalise_result = normalise_snapshot(
                    snapshot.id,
                    raw_db_path=config.raw_db_path,
                    event_db_path=config.event_db_path,
                )
            except Exception as exc:  # noqa: BLE001 -- one bad snapshot must not
                # stop normalisation of the rest, or collection of the next CIK.
                logger.error(
                    "normalisation failed for %s (cik=%s, snapshot_id=%s): %s",
                    ticker, cik, snapshot.id, exc,
                )
                normalise_failures.append(
                    CollectionFailure(
                        accession_number="", url="", reason=f"normalise snapshot {snapshot.id}: {exc}"
                    )
                )
                continue
            events_written += len(normalise_result.events_written)

        outcomes.append(
            CikOutcome(
                ticker=ticker,
                cik=cik,
                snapshots_written=len(result.snapshots),
                events_written=events_written,
                failures=result.failures + tuple(normalise_failures),
            )
        )

    return RunSummary(outcomes=tuple(outcomes))


def append_failure_log(
    summary: RunSummary, *, log_dir: Path, now: Callable[[], str] = _utc_now_iso
) -> int:
    """Append one JSON line per recorded failure to
    <log_dir>/collector_failures.jsonl, so a day's failures survive
    past the in-memory RunSummary a systemd oneshot run does not
    otherwise persist anywhere -- STORY-009's daily ops report reads
    this file back. Append-only, matching this repository's raw-store
    precedent: a run's own failures are never edited after the fact,
    only ever added to.

    Story: stories/STORY-009-daily-ops-report.md
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "collector_failures.jsonl"
    timestamp = now()
    written = 0
    with log_path.open("a") as fh:
        for outcome in summary.outcomes:
            for failure in outcome.failures:
                fh.write(
                    json.dumps(
                        {
                            "timestamp": timestamp,
                            "ticker": outcome.ticker,
                            "cik": outcome.cik,
                            "accession_number": failure.accession_number,
                            "url": failure.url,
                            "reason": failure.reason,
                        }
                    )
                    + "\n"
                )
                written += 1
    return written


def main() -> RunSummary:
    logging.basicConfig(level=logging.INFO)
    config = load_collector_config()
    config.data_dir.mkdir(parents=True, exist_ok=True)
    universe = load_universe(config.universe_path)

    from edgelab.net.requests_http_client import RequestsHttpClient

    summary = run(universe, http_client=RequestsHttpClient(), config=config)
    append_failure_log(summary, log_dir=config.log_dir)
    logger.info(
        "run complete: %d snapshots, %d events, %d CIKs with failures",
        summary.total_snapshots,
        summary.total_events,
        len(summary.ciks_with_failures),
    )
    return summary


if __name__ == "__main__":
    main()
