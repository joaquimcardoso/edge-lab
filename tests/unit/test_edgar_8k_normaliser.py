"""Unit tests for src/edgelab/normalisers/edgar_8k.py."""

from __future__ import annotations

import pytest

from edgelab.normalisers import edgar_8k as norm


def make_header_text(
    accession="0000320193-26-000050",
    acceptance="20260920163211",
    cik="320193",
    submission_type="8-K",
    items=("Results of Operations and Financial Condition", "Financial Statements and Exhibits"),
    extra_lines="",
):
    item_lines = "\n".join(f"ITEM INFORMATION:\t\t{item}" for item in items)
    return (
        f"<SEC-DOCUMENT>{accession}.txt : {acceptance}\n"
        f"<SEC-HEADER>{accession}.hdr.sgml : {acceptance}\n"
        f"<ACCEPTANCE-DATETIME>{acceptance}\n"
        f"ACCESSION NUMBER:\t\t{accession}\n"
        f"CONFORMED SUBMISSION TYPE:\t{submission_type}\n"
        f"PUBLIC DOCUMENT COUNT:\t\t3\n"
        f"CONFORMED PERIOD OF REPORT:\t20260920\n"
        f"{item_lines}\n"
        f"FILED AS OF DATE:\t\t20260920\n"
        f"{extra_lines}"
        f"FILER:\n"
        f"\tCOMPANY DATA:\n"
        f"\t\tCOMPANY CONFORMED NAME:\t\tApple Inc.\n"
        f"\t\tCENTRAL INDEX KEY:\t\t{cik}\n"
        f"</SEC-HEADER>\n"
        f"<DOCUMENT>\n<TYPE>8-K\n<TEXT>...body...</TEXT>\n</DOCUMENT>\n"
    ).encode("utf-8")


def test_parse_header_fields_happy_path():
    header = norm.parse_header_fields(make_header_text())

    assert header.accession_number == "0000320193-26-000050"
    assert header.acceptance_datetime == "2026-09-20T16:32:11Z"
    assert header.cik == "0000320193"
    assert header.submission_type == "8-K"
    assert header.item_descriptions == (
        "Results of Operations and Financial Condition",
        "Financial Statements and Exhibits",
    )


def test_parse_header_fields_raises_on_missing_accession_number():
    text = make_header_text().replace(b"ACCESSION NUMBER:", b"IRRELEVANT-FIELD:")
    with pytest.raises(norm.HeaderParseError):
        norm.parse_header_fields(text)


def test_parse_header_fields_raises_on_missing_acceptance_datetime():
    text = make_header_text().replace(b"<ACCEPTANCE-DATETIME>", b"<IRRELEVANT-TAG>")
    with pytest.raises(norm.HeaderParseError):
        norm.parse_header_fields(text)


def test_parse_header_fields_tolerates_missing_cik():
    text = make_header_text().replace(b"CENTRAL INDEX KEY:", b"IRRELEVANT:")
    header = norm.parse_header_fields(text)
    assert header.cik == ""  # degrades gracefully, does not raise


@pytest.mark.parametrize(
    "description,expected_code,expected_type",
    [
        ("Results of Operations and Financial Condition", "2.02", "earnings_release"),
        ("Entry into a Material Definitive Agreement", "1.01", "material_agreement"),
        ("Completion of Acquisition or Disposition of Assets", "2.01", "acquisition_disposition"),
        ("Other Events", "8.01", "other_verified"),
    ],
)
def test_classify_items_maps_in_scope_items(description, expected_code, expected_type):
    classified, unmapped = norm.classify_items((description,))
    assert classified == [(expected_code, expected_type)]
    assert unmapped == []


def test_classify_items_recognised_but_out_of_scope_item_produces_nothing():
    # "Financial Statements and Exhibits" (9.01) is recognised wording
    # but not in ITEM_CODE_TO_EVENT_TYPE -- must be silently excluded,
    # not treated as unmapped/unrecognised.
    classified, unmapped = norm.classify_items(("Financial Statements and Exhibits",))
    assert classified == []
    assert unmapped == []


def test_classify_items_unrecognised_wording_is_unmapped_not_raised():
    classified, unmapped = norm.classify_items(("Some New Item SEC Hasn't Told Us About",))
    assert classified == []
    assert unmapped == ["Some New Item SEC Hasn't Told Us About"]


def test_classify_items_mixed_batch():
    classified, unmapped = norm.classify_items(
        (
            "Results of Operations and Financial Condition",
            "Financial Statements and Exhibits",
            "A Brand New Item Type",
        )
    )
    assert classified == [("2.02", "earnings_release")]
    assert unmapped == ["A Brand New Item Type"]


def test_build_events_known_at_equals_first_seen_at():
    header = norm.parse_header_fields(make_header_text())
    result = norm.build_events(
        header, first_seen_at="2026-09-20T16:50:00Z", snapshot_id=42
    )

    assert len(result.events_written) == 1  # only 2.02 maps; 9.01 doesn't
    event = result.events_written[0]
    assert event.known_at == "2026-09-20T16:50:00Z"
    assert event.known_at == event.first_seen_at
    assert event.published_at == "2026-09-20T16:32:11Z"
    assert event.direction is None
    # 2026-09-20 is a Sunday -- session_date correctly rolls to the
    # next NYSE trading day (STORY-005), not "same day."
    assert event.session_date == "2026-09-21"
    assert event.security_id == "0000320193"
    assert event.type == "earnings_release"
    assert event.source_id == "0000320193-26-000050"
    assert event.snapshot_id == 42
    assert event.classifier_version == norm.CLASSIFIER_VERSION


def test_build_events_carries_unmapped_through():
    header = norm.parse_header_fields(
        make_header_text(items=("Results of Operations and Financial Condition", "A New Item"))
    )
    result = norm.build_events(header, first_seen_at="2026-09-20T16:50:00Z", snapshot_id=1)
    assert result.unmapped_item_descriptions == ("A New Item",)
