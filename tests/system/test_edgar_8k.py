"""System-level test for the EDGAR 8-K collector (STORY-002).

Runs collect_8k_for_cik end-to-end against a fake HTTP transport that
serves a realistic submissions.json plus complete-submission .txt
bodies, and verifies the result lands correctly in STORY-001's raw
snapshot store -- including that a single failed document fetch is
recorded as a failure rather than silently dropped or crashing the
whole run (docs/04-infrastructure.md: never converted into "no
event"). No real network call is made.

Regression fixture set: still vacuous, as in STORY-001 -- no
experiment is FROZEN yet.
"""

from __future__ import annotations

from edgelab.collectors import edgar_8k as ec
from edgelab.storage.raw_snapshot import read_raw_snapshot
from tests.unit.test_edgar_8k import FakeHttpClient, FakeResponse, make_submissions_fixture


def _submission_txt(accession_number: str, acceptance_datetime: str) -> bytes:
    """A minimal but realistic complete-submission .txt body: an SGML
    header carrying ACCEPTANCE-DATETIME, followed by a document body.
    Real files are much larger; this is enough to exercise storage
    and round-trip, and to show the header data really is inside the
    stored bytes (the reconstructability property the Reviewer stage
    caught).
    """
    return (
        f"<SEC-HEADER>{accession_number}.hdr.sgml : {acceptance_datetime}\n"
        f"ACCESSION NUMBER:\t\t{accession_number}\n"
        f"CONFORMED SUBMISSION TYPE:\t8-K\n"
        f"ACCEPTANCE-DATETIME:\t\t{acceptance_datetime.replace('-', '').replace(':', '').replace('T', '').replace('Z', '').split('.')[0]}\n"
        f"</SEC-HEADER>\n"
        f"<DOCUMENT>...body...</DOCUMENT>\n"
    ).encode("utf-8")


def test_collect_8k_for_cik_end_to_end(tmp_path):
    db_path = tmp_path / "raw.sqlite3"
    data_dir = tmp_path / "data"

    fixture = make_submissions_fixture()
    submissions_url = ec.SEC_SUBMISSIONS_URL.format(cik10="0000320193")

    in_scope = ["0000320193-26-000050", "0000320193-26-000053", "0000320193-26-000054"]
    doc_urls = {
        acc: f"https://www.sec.gov/Archives/edgar/data/320193/{acc}.txt" for acc in in_scope
    }

    responses = {
        submissions_url: FakeResponse(200, json_body=fixture),
        doc_urls["0000320193-26-000050"]: FakeResponse(
            200, content=_submission_txt("0000320193-26-000050", "2026-09-20T16:32:11.000Z")
        ),
        # Simulate one document fetch failing (e.g. a transient 503)
        # while the other two succeed.
        doc_urls["0000320193-26-000053"]: FakeResponse(503, content=b""),
        doc_urls["0000320193-26-000054"]: FakeResponse(
            200, content=_submission_txt("0000320193-26-000054", "2026-09-24T07:45:00.000Z")
        ),
    }
    client = FakeHttpClient(responses)

    result = ec.collect_8k_for_cik(
        320193,
        http_client=client,
        user_agent="edge-lab system test contact@example.com",
        db_path=db_path,
        data_dir=data_dir,
        sleep=lambda seconds: None,  # no real waiting in tests
        now=lambda: "2026-09-25T12:00:00Z",
    )

    # 2 successes, 1 recorded failure -- not silently dropped, not
    # fabricated into a fake snapshot, and the run as a whole did not
    # crash on the one bad filing.
    assert len(result.snapshots) == 2
    assert len(result.failures) == 1
    assert result.failures[0].accession_number == "0000320193-26-000053"
    assert "503" in result.failures[0].reason

    # Every successful snapshot reads back cleanly from STORY-001's
    # store, with the filing's own ACCEPTANCE-DATETIME actually
    # present in the stored bytes (not just in the ephemeral
    # submissions response this run happened to see).
    for snapshot in result.snapshots:
        _, payload = read_raw_snapshot(snapshot.id, db_path=db_path)
        assert snapshot.source == "edgar_8k"
        assert b"ACCEPTANCE-DATETIME" in payload

    # The rate limiter was invoked once for the submissions call and
    # once per document fetch attempted (including the one that failed).
    assert client.calls[0] == submissions_url
    assert len(client.calls) == 1 + 3


def test_collect_8k_for_cik_raises_on_submissions_failure(tmp_path):
    """A submissions-listing failure must propagate -- per
    docs/04-infrastructure.md, never silently read as "no filings
    today."
    """
    submissions_url = ec.SEC_SUBMISSIONS_URL.format(cik10="0000320193")
    client = FakeHttpClient({submissions_url: FakeResponse(500)})

    try:
        ec.collect_8k_for_cik(
            320193,
            http_client=client,
            user_agent="edge-lab system test contact@example.com",
            db_path=tmp_path / "raw.sqlite3",
            data_dir=tmp_path / "data",
            sleep=lambda seconds: None,
        )
        raise AssertionError("expected SecEdgarError to propagate")
    except ec.SecEdgarError:
        pass
