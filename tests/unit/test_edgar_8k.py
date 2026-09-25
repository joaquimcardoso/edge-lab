"""Unit tests for src/edgelab/collectors/edgar_8k.py.

All fixtures below follow SEC EDGAR's documented, stable submissions-
API schema (see the module's own docstring for the caveat that this
schema has not been checked against one live response in this
sandbox). No test in this file makes a network call -- http_client is
always a fake object, per STORY-002's acceptance criteria.
"""

from __future__ import annotations

import pytest

from edgelab.collectors import edgar_8k as ec


def make_submissions_fixture():
    """A representative submissions.json 'filings.recent' block: two
    in-scope 8-Ks (2.02, 1.01), one out-of-scope 8-K (5.02 only, not
    in DEFAULT_ITEMS_OF_INTEREST), one non-8-K form, and one in-scope
    8-K with a different single item (8.01).
    """
    return {
        "cik": 320193,
        "filings": {
            "recent": {
                "form": ["8-K", "8-K", "10-Q", "8-K", "8-K"],
                "accessionNumber": [
                    "0000320193-26-000050",
                    "0000320193-26-000051",
                    "0000320193-26-000052",
                    "0000320193-26-000053",
                    "0000320193-26-000054",
                ],
                "filingDate": [
                    "2026-09-20",
                    "2026-09-21",
                    "2026-09-22",
                    "2026-09-23",
                    "2026-09-24",
                ],
                "acceptanceDateTime": [
                    "2026-09-20T16:32:11.000Z",
                    "2026-09-21T08:05:00.000Z",
                    "2026-09-22T20:00:00.000Z",
                    "2026-09-23T09:01:00.000Z",
                    "2026-09-24T07:45:00.000Z",
                ],
                "items": ["2.02,9.01", "5.02", "", "1.01", "8.01"],
                "primaryDocument": [
                    "ex-8k20260920.htm",
                    "ex-8k20260921.htm",
                    "aapl-10q.htm",
                    "ex-8k20260923.htm",
                    "ex-8k20260924.htm",
                ],
            }
        },
    }


class FakeResponse:
    def __init__(self, status_code, json_body=None, content=b""):
        self.status_code = status_code
        self._json_body = json_body
        self.content = content

    def json(self):
        return self._json_body


class FakeHttpClient:
    def __init__(self, responses_by_url):
        self.responses_by_url = responses_by_url
        self.calls = []

    def get(self, url, *, headers, timeout):
        self.calls.append(url)
        assert "User-Agent" in headers
        return self.responses_by_url[url]


def test_parse_8k_filings_keeps_only_in_scope_8ks():
    filings = ec.parse_8k_filings(make_submissions_fixture())
    accession_numbers = [f.accession_number for f in filings]

    # In scope: 2.02 (idx 0), 1.01 (idx 3), 8.01 (idx 4).
    assert accession_numbers == [
        "0000320193-26-000050",
        "0000320193-26-000053",
        "0000320193-26-000054",
    ]
    # Out of scope: 5.02-only 8-K (idx 1) and the 10-Q (idx 2) are both absent.
    assert "0000320193-26-000051" not in accession_numbers
    assert "0000320193-26-000052" not in accession_numbers


def test_parse_8k_filings_cik_is_zero_padded():
    filings = ec.parse_8k_filings(make_submissions_fixture())
    assert all(f.cik == "0000320193" for f in filings)


def test_parse_8k_filings_items_are_split_and_stripped():
    filings = ec.parse_8k_filings(make_submissions_fixture())
    first = next(f for f in filings if f.accession_number == "0000320193-26-000050")
    assert first.items == ("2.02", "9.01")


def test_parse_8k_filings_empty_items_field_excludes_entry():
    submissions = make_submissions_fixture()
    # idx 2 (the 10-Q) already has items="" and is excluded by form
    # anyway; force an 8-K with empty items to isolate the items check.
    submissions["filings"]["recent"]["form"][2] = "8-K"
    filings = ec.parse_8k_filings(submissions)
    assert "0000320193-26-000052" not in [f.accession_number for f in filings]


def test_parse_8k_filings_skips_malformed_entry_without_raising():
    submissions = make_submissions_fixture()
    # Truncate accessionNumber so the last index (an in-scope 8-K) is
    # missing its accession number -- must be skipped, not fatal.
    submissions["filings"]["recent"]["accessionNumber"] = submissions["filings"]["recent"][
        "accessionNumber"
    ][:-1]

    filings = ec.parse_8k_filings(submissions)  # must not raise
    accession_numbers = [f.accession_number for f in filings]
    assert "0000320193-26-000054" not in accession_numbers
    # The earlier, well-formed in-scope entries are unaffected.
    assert "0000320193-26-000050" in accession_numbers
    assert "0000320193-26-000053" in accession_numbers


def test_parse_8k_filings_custom_items_of_interest():
    filings = ec.parse_8k_filings(
        make_submissions_fixture(), items_of_interest=frozenset({"5.02"})
    )
    assert [f.accession_number for f in filings] == ["0000320193-26-000051"]


def test_filing_document_url_uses_complete_submission_txt():
    filing = ec.EightKFiling(
        cik="0000320193",
        accession_number="0000320193-26-000050",
        filing_date="2026-09-20",
        acceptance_datetime="2026-09-20T16:32:11.000Z",
        items=("2.02",),
        primary_document="ex-8k20260920.htm",
        form="8-K",
    )
    url = ec.filing_document_url(filing)
    assert url == "https://www.sec.gov/Archives/edgar/data/320193/0000320193-26-000050.txt"


def test_fetch_submissions_returns_json_on_200():
    fixture = make_submissions_fixture()
    url = ec.SEC_SUBMISSIONS_URL.format(cik10="0000320193")
    client = FakeHttpClient({url: FakeResponse(200, json_body=fixture)})

    result = ec.fetch_submissions(320193, http_client=client, user_agent="edge-lab test a@b.com")

    assert result == fixture
    assert client.calls == [url]


def test_fetch_submissions_raises_sec_edgar_error_on_non_200():
    url = ec.SEC_SUBMISSIONS_URL.format(cik10="0000320193")
    client = FakeHttpClient({url: FakeResponse(404)})

    with pytest.raises(ec.SecEdgarError):
        ec.fetch_submissions(320193, http_client=client, user_agent="edge-lab test a@b.com")


def test_format_cik_rejects_non_numeric():
    with pytest.raises(ValueError):
        ec._format_cik("not-a-cik")
