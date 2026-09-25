"""8-K normaliser: raw submission -> typed event records.

Parses the SGML header of a complete-submission .txt raw snapshot
(STORY-002) to derive published_at (from the <ACCEPTANCE-DATETIME>
tag), accession number, CIK, and every "ITEM INFORMATION:" line --
mapped to the closed event taxonomy in docs/03-architecture.md
("Closed event taxonomy (V1)") via ITEM_DESCRIPTION_TO_CODE and
ITEM_CODE_TO_EVENT_TYPE. Classification is keyed off SEC's own
standard Item Information wording in the stored header, not the
ephemeral submissions-API `items` field STORY-002 used only to decide
which filings to fetch -- so an event is fully rebuildable from the
raw snapshot alone, per the point-in-time checklist.

known_at is computed per 01-point-in-time-rules.md §2's live-collected
rule: known_at = first_seen_at (never published_at + a lag estimate,
which needs STORY-006's not-yet-built latency audit). published_at is
still stored on every event -- it is exactly the input STORY-006 will
need later.

Direction is not inferred from 8-K text in V1 (03-architecture.md);
every event this module produces carries direction=None (UNKNOWN).

session_date is computed via src/edgelab/calendar/trading_calendar.py
(STORY-005) from published_at -- backed by a real NYSE trading
calendar, not a hard-coded weekday check. STORY-003 originally left
this field None rather than fake it; STORY-005 backfilled it once
the calendar dependency existed.

Story: stories/STORY-003-normaliser-event-store.md, STORY-005 (session_date)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from edgelab.calendar.trading_calendar import compute_session_date
from edgelab.storage.event_store import Event, write_event
from edgelab.storage.raw_snapshot import read_raw_snapshot

CLASSIFIER_VERSION = "rules-v1-8k-item-code"

# SEC's own standard "ITEM INFORMATION:" wording, current as of
# 2026-09-25 (https://www.sec.gov/ -- Form 8-K item list). Only the
# items this repository collects (docs/02-data-sources.md's items of
# interest) map to a closed-taxonomy type; others are recognised
# (so they don't show up as "unmapped") but deliberately produce no
# event, since they are out of this repository's collection scope.
ITEM_DESCRIPTION_TO_CODE = {
    "Entry into a Material Definitive Agreement": "1.01",
    "Termination of a Material Definitive Agreement": "1.02",
    "Completion of Acquisition or Disposition of Assets": "2.01",
    "Results of Operations and Financial Condition": "2.02",
    "Departure of Directors or Certain Officers; Election of Directors; "
    "Appointment of Certain Officers; Compensatory Arrangements of Certain Officers": "5.02",
    "Regulation FD Disclosure": "7.01",
    "Other Events": "8.01",
    "Financial Statements and Exhibits": "9.01",
}

# Only these item codes produce a taxonomy event -- see
# docs/02-data-sources.md's items of interest and
# docs/03-architecture.md's closed taxonomy.
ITEM_CODE_TO_EVENT_TYPE = {
    "2.02": "earnings_release",
    "1.01": "material_agreement",
    "2.01": "acquisition_disposition",
    "8.01": "other_verified",
}

_ACCEPTANCE_DATETIME_RE = re.compile(r"<ACCEPTANCE-DATETIME>(\d{14})")
_ACCESSION_NUMBER_RE = re.compile(r"ACCESSION NUMBER:\s*(\S+)")
_SUBMISSION_TYPE_RE = re.compile(r"CONFORMED SUBMISSION TYPE:\s*(\S+)")
_CIK_RE = re.compile(r"CENTRAL INDEX KEY:\s*(\d+)")
_ITEM_INFORMATION_RE = re.compile(r"ITEM INFORMATION:\s*(.+)")


class HeaderParseError(RuntimeError):
    """Raised when a raw payload is missing a field this module cannot
    proceed without (accession number or acceptance datetime) -- the
    two fields every event's identity and known_at depend on.
    """


@dataclass(frozen=True)
class HeaderFields:
    accession_number: str
    acceptance_datetime: str  # ISO-8601 UTC
    cik: str
    submission_type: str
    item_descriptions: Tuple[str, ...]


@dataclass(frozen=True)
class NormaliseResult:
    events_written: Tuple[Event, ...]
    unmapped_item_descriptions: Tuple[str, ...]


def _to_iso8601(raw_datetime: str) -> str:
    """Convert SEC's ACCEPTANCE-DATETIME (YYYYMMDDHHMMSS) to ISO-8601 UTC."""
    return (
        f"{raw_datetime[0:4]}-{raw_datetime[4:6]}-{raw_datetime[6:8]}T"
        f"{raw_datetime[8:10]}:{raw_datetime[10:12]}:{raw_datetime[12:14]}Z"
    )


def parse_header_fields(raw_text: bytes) -> HeaderFields:
    """Parse the SGML header of a complete-submission .txt payload.

    Raises HeaderParseError if the accession number or acceptance
    datetime is missing -- every other field degrades gracefully
    (empty string / no items), but those two are load-bearing for
    every event this filing could produce.
    """
    text = raw_text.decode("utf-8", errors="replace")

    accession_match = _ACCESSION_NUMBER_RE.search(text)
    acceptance_match = _ACCEPTANCE_DATETIME_RE.search(text)
    if accession_match is None:
        raise HeaderParseError("no ACCESSION NUMBER found in raw payload")
    if acceptance_match is None:
        raise HeaderParseError("no <ACCEPTANCE-DATETIME> tag found in raw payload")

    submission_type_match = _SUBMISSION_TYPE_RE.search(text)
    cik_match = _CIK_RE.search(text)
    item_descriptions = tuple(m.group(1).strip() for m in _ITEM_INFORMATION_RE.finditer(text))

    return HeaderFields(
        accession_number=accession_match.group(1),
        acceptance_datetime=_to_iso8601(acceptance_match.group(1)),
        cik=cik_match.group(1).zfill(10) if cik_match else "",
        submission_type=submission_type_match.group(1) if submission_type_match else "",
        item_descriptions=item_descriptions,
    )


def classify_items(
    item_descriptions: Tuple[str, ...],
) -> Tuple[List[Tuple[str, str]], List[str]]:
    """Map item descriptions to (item_code, event_type) pairs.

    Returns (classified, unmapped). An item recognised but out of
    collection scope (e.g. "9.01") is silently excluded from both
    lists -- it is not an error, just not something this repository
    turns into an event. Only a description SEC's own standard
    wording doesn't recognise at all lands in `unmapped`.
    """
    classified: List[Tuple[str, str]] = []
    unmapped: List[str] = []
    for description in item_descriptions:
        code = ITEM_DESCRIPTION_TO_CODE.get(description)
        if code is None:
            unmapped.append(description)
            continue
        event_type = ITEM_CODE_TO_EVENT_TYPE.get(code)
        if event_type is None:
            continue  # recognised item, out of collection scope (e.g. 9.01)
        classified.append((code, event_type))
    return classified, unmapped


def build_events(
    header: HeaderFields,
    *,
    first_seen_at: str,
    snapshot_id: int,
    source: str = "edgar_8k",
) -> NormaliseResult:
    """Build (not yet persisted) Event records for one parsed filing."""
    classified, unmapped = classify_items(header.item_descriptions)

    events = tuple(
        Event(
            security_id=header.cik,
            type=event_type,
            direction=None,  # UNKNOWN: 8-K direction not inferred from text in V1
            published_at=header.acceptance_datetime,
            first_seen_at=first_seen_at,
            known_at=first_seen_at,  # live-collected rule, 01-point-in-time-rules.md §2
            session_date=compute_session_date(header.acceptance_datetime),  # 01-point-in-time-rules.md §3, via STORY-005
            source=source,
            source_id=header.accession_number,
            snapshot_id=snapshot_id,
            classifier_version=CLASSIFIER_VERSION,
        )
        for _, event_type in classified
    )
    return NormaliseResult(events_written=events, unmapped_item_descriptions=tuple(unmapped))


def normalise_snapshot(
    snapshot_id: int,
    *,
    raw_db_path,
    event_db_path,
) -> NormaliseResult:
    """Read one raw snapshot, parse and classify it, and persist its
    resulting events -- idempotently: running this twice on the same
    snapshot_id writes no duplicate events (event_store's own
    dedup on (source, source_id, type)).
    """
    snapshot, payload = read_raw_snapshot(snapshot_id, db_path=raw_db_path)
    header = parse_header_fields(payload)
    built = build_events(
        header,
        first_seen_at=snapshot.first_seen_at,
        snapshot_id=snapshot_id,
        source=snapshot.source,
    )

    written = tuple(
        write_event(event, db_path=event_db_path) for event in built.events_written
    )
    return NormaliseResult(
        events_written=written, unmapped_item_descriptions=built.unmapped_item_descriptions
    )
