"""EDGAR 8-K collector.

Fetches a company's recent 8-K filings from SEC EDGAR's public
submissions API, keeps only filings whose item codes match the items
of interest (docs/02-data-sources.md), and persists each matching
filing's *complete submission text file* (the SGML-headed .txt at
/Archives/edgar/data/{cik}/{accession-with-dashes}.txt, not just the
primary document HTML) as an immutable raw snapshot via
src/edgelab/storage/raw_snapshot.py.

Storing the complete submission rather than only the primary document
is a deliberate choice, caught during review: SEC embeds the filing's
own ACCEPTANCE-DATETIME, ACCESSION-NUMBER and ITEMS in that file's
SGML header, so the raw snapshot alone is enough for the normaliser
(STORY-003) to derive known_at -- satisfying the point-in-time
checklist's "can it be rebuilt from raw snapshots?" question, which
storing only the rendered primary-document HTML would not have.

Schema note: the "filings.recent" parallel-array field names used
below (accessionNumber, filingDate, acceptanceDateTime, form, items,
primaryDocument) are SEC EDGAR's documented, stable submissions-API
schema as of 2026-09-25. This development sandbox's network egress
does not reach data.sec.gov, so this module has not been exercised
against one live response -- parse_8k_filings is tested against a
fixture built from that documented schema instead. Re-verify field
names against one real response the first time this collector runs
with real network access (the Pi, per docs/04-infrastructure.md),
before trusting it unattended.

Failure handling follows docs/04-infrastructure.md: a submissions-
fetch failure raises (propagates to the caller to log and alert,
never silently read as "no filings today"); a per-filing document
fetch failure is skipped and recorded in CollectionResult.failures,
never silently dropped and never turned into a fabricated snapshot.

Story: stories/STORY-002-edgar-8k-collector.md
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, FrozenSet, List, Optional, Protocol, Tuple, Union

from edgelab.storage.raw_snapshot import EmptyPayloadError, RawSnapshot, write_raw_snapshot

PathLike = Union[str, "Path"]

SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik10}.json"

# SEC's fair-access limit is 10 requests/second; stay well under it.
SEC_RATE_LIMIT_MIN_INTERVAL_SECONDS = 0.2

DEFAULT_ITEMS_OF_INTEREST: FrozenSet[str] = frozenset({"2.02", "1.01", "2.01", "8.01"})


class SecEdgarError(RuntimeError):
    """Raised when SEC EDGAR returns something this collector can't use.

    Deliberately NOT caught anywhere inside this module for the
    submissions-listing call -- per docs/04-infrastructure.md, a
    collector failure must be logged and alerted, never silently
    converted into "no filings today."
    """


class HttpResponse(Protocol):
    status_code: int
    content: bytes

    def json(self) -> dict: ...


class HttpClient(Protocol):
    def get(self, url: str, *, headers: dict, timeout: float) -> HttpResponse: ...


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _format_cik(cik: Union[str, int]) -> str:
    digits = "".join(ch for ch in str(cik) if ch.isdigit())
    if not digits:
        raise ValueError(f"cik must contain digits, got {cik!r}")
    return digits.zfill(10)


@dataclass(frozen=True)
class EightKFiling:
    cik: str
    accession_number: str
    filing_date: str
    acceptance_datetime: Optional[str]
    items: Tuple[str, ...]
    primary_document: str
    form: str


@dataclass(frozen=True)
class CollectionFailure:
    accession_number: str
    url: str
    reason: str


@dataclass(frozen=True)
class CollectionResult:
    snapshots: Tuple[RawSnapshot, ...] = ()
    failures: Tuple[CollectionFailure, ...] = ()


def fetch_submissions(
    cik: Union[str, int],
    *,
    http_client: HttpClient,
    user_agent: str,
    timeout: float = 10.0,
) -> dict:
    """Fetch and return the raw submissions JSON for one company.

    Raises SecEdgarError on any non-200 response. Never catches or
    retries here -- retry/backoff policy belongs to the scheduler
    that calls this, not to the parsing logic.
    """
    url = SEC_SUBMISSIONS_URL.format(cik10=_format_cik(cik))
    response = http_client.get(url, headers={"User-Agent": user_agent}, timeout=timeout)
    if response.status_code != 200:
        raise SecEdgarError(
            f"SEC EDGAR returned HTTP {response.status_code} for {url}"
        )
    return response.json()


def parse_8k_filings(
    submissions: dict,
    *,
    items_of_interest: FrozenSet[str] = DEFAULT_ITEMS_OF_INTEREST,
) -> List[EightKFiling]:
    """Parse a submissions JSON payload into 8-K filings of interest.

    A malformed individual entry (a field missing or short for its
    index) is skipped rather than raised on -- one bad record in a
    company's filing history must never take down the whole parse.
    """
    raw_cik = submissions.get("cik")
    cik = _format_cik(raw_cik) if raw_cik not in (None, "") else ""

    recent = (submissions.get("filings") or {}).get("recent") or {}
    forms = recent.get("form") or []
    accession_numbers = recent.get("accessionNumber") or []
    filing_dates = recent.get("filingDate") or []
    acceptance_datetimes = recent.get("acceptanceDateTime") or []
    items_field = recent.get("items") or []
    primary_documents = recent.get("primaryDocument") or []

    results: List[EightKFiling] = []
    for i, form in enumerate(forms):
        if form != "8-K":
            continue
        try:
            raw_items = items_field[i] if i < len(items_field) else ""
            item_codes = tuple(
                code.strip() for code in (raw_items or "").split(",") if code.strip()
            )
            if items_of_interest and not (set(item_codes) & items_of_interest):
                continue
            results.append(
                EightKFiling(
                    cik=cik,
                    accession_number=accession_numbers[i],
                    filing_date=filing_dates[i] if i < len(filing_dates) else "",
                    acceptance_datetime=(
                        acceptance_datetimes[i] if i < len(acceptance_datetimes) else None
                    ),
                    items=item_codes,
                    primary_document=(
                        primary_documents[i] if i < len(primary_documents) else ""
                    ),
                    form=form,
                )
            )
        except IndexError:
            # accessionNumber (the one field with no fallback above) is
            # shorter than forms for this index -- skip this entry.
            continue
    return results


def filing_document_url(filing: EightKFiling) -> str:
    """URL of the filing's complete submission text file (SGML header
    + every embedded document), not just the rendered primary
    document -- see the module docstring for why.
    """
    if not filing.accession_number:
        raise ValueError("filing has no accession_number; cannot build a document URL")
    cik_int = int(filing.cik) if filing.cik else 0
    return (
        f"https://www.sec.gov/Archives/edgar/data/{cik_int}/"
        f"{filing.accession_number}.txt"
    )


def collect_8k_for_cik(
    cik: Union[str, int],
    *,
    http_client: HttpClient,
    user_agent: str,
    db_path: PathLike,
    data_dir: PathLike,
    items_of_interest: FrozenSet[str] = DEFAULT_ITEMS_OF_INTEREST,
    min_interval_seconds: float = SEC_RATE_LIMIT_MIN_INTERVAL_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], str] = _utc_now_iso,
) -> CollectionResult:
    """Fetch one company's recent 8-K filings of interest and persist
    each filing's complete submission text file as an immutable raw
    snapshot (see the module docstring for why the complete
    submission, not just the primary document, is what gets stored).

    Returns a CollectionResult so the caller can tell "zero filings
    of interest today" (empty snapshots, empty failures) apart from
    "N filings, M failed to fetch" (failures non-empty) -- a failure
    is never silently absorbed into a result that looks identical to
    a quiet day.
    """
    # Rate-limit every external GET this function makes, including the
    # submissions call itself -- so calling this in a tight loop across
    # many CIKs (a universe scan) stays well under SEC's 10 req/s limit
    # without the caller having to add its own throttling.
    sleep(min_interval_seconds)
    submissions = fetch_submissions(cik, http_client=http_client, user_agent=user_agent)
    filings = parse_8k_filings(submissions, items_of_interest=items_of_interest)

    snapshots: List[RawSnapshot] = []
    failures: List[CollectionFailure] = []

    for filing in filings:
        try:
            url = filing_document_url(filing)
        except ValueError as exc:
            failures.append(
                CollectionFailure(
                    accession_number=filing.accession_number, url="", reason=str(exc)
                )
            )
            continue

        sleep(min_interval_seconds)
        response = http_client.get(url, headers={"User-Agent": user_agent}, timeout=10.0)
        if response.status_code != 200:
            failures.append(
                CollectionFailure(
                    accession_number=filing.accession_number,
                    url=url,
                    reason=f"HTTP {response.status_code}",
                )
            )
            continue

        payload = response.content
        try:
            snapshot = write_raw_snapshot(
                "edgar_8k",
                now(),
                payload,
                db_path=db_path,
                data_dir=data_dir,
                url=url,
            )
        except EmptyPayloadError as exc:
            failures.append(
                CollectionFailure(
                    accession_number=filing.accession_number, url=url, reason=str(exc)
                )
            )
            continue

        snapshots.append(snapshot)

    return CollectionResult(snapshots=tuple(snapshots), failures=tuple(failures))
