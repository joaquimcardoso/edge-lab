# STORY-002 — EDGAR 8-K collector

| Field | Value |
|---|---|
| Status | TRADING_REVIEWED |
| Owner stage | Story Agent |

## Source

[07-development-workflow.md §Suggested MVP story sequence, item 2](../docs/07-development-workflow.md#suggested-mvp-story-sequence-phase-1): "`edgar_8k` collector (the most defensible free source — official acceptance timestamps, no feed-latency ambiguity) writing into the raw store." Endpoint and rules from [02-data-sources.md §SEC EDGAR](../docs/02-data-sources.md#sec-edgar): descriptive `User-Agent` with contact email required, 10 req/s fair-access limit (stay well below it), items of interest `2.02` / `1.01` / `2.01` / `8.01`. Failure handling from [04-infrastructure.md §Failure handling](../docs/04-infrastructure.md): "A collector failure is logged, alerted and never converted into 'no event'."

## Goal

A collector module that, given a company's CIK, fetches its recent 8-K filings from SEC EDGAR's public submissions API, keeps only filings whose item codes match the items of interest, fetches each matching filing's primary document, and persists it as an immutable raw snapshot via [STORY-001](STORY-001-raw-snapshot-store.md)'s `write_raw_snapshot`. No parsing of filing *content* (event direction, magnitude) — that is the normaliser's job, STORY-003.

## Acceptance criteria

- [ ] `fetch_submissions(cik, *, http_client, user_agent)` fetches `https://data.sec.gov/submissions/CIK{10-digit-zero-padded-cik}.json`, sends the given `User-Agent`, and raises `SecEdgarError` on a non-200 response (propagates — per 04-infrastructure.md this must never be silently swallowed into "no filings").
- [ ] `parse_8k_filings(submissions_json)` parses the `filings.recent` parallel-array structure into a list of 8-K filings, keeping only `form == "8-K"` entries whose comma-separated `items` field intersects the items-of-interest set. A malformed individual entry (missing/short field) is skipped, not fatal to the whole parse.
- [ ] `collect_8k_for_cik(cik, ...)` fetches the submissions listing, parses it, then fetches each matching filing's **complete submission text file** (the SGML-headed `.txt`, not just the rendered primary document HTML — caught during review: SEC embeds ACCEPTANCE-DATETIME/ACCESSION-NUMBER/ITEMS in that header, so this is what makes the snapshot alone sufficient to rebuild `known_at` later, per the point-in-time checklist) over HTTP (rate-limited between requests, well under 10 req/s, including the submissions call itself) and writes it to the raw store with `source="edgar_8k"`.
- [ ] The HTTP layer is injected (a `http_client` protocol/object with a `.get(url, headers, timeout)` method), never imported and called directly inside the collection logic — so unit and system tests run against a fake transport with zero live network calls, deterministically.
- [ ] The collector returns a result distinguishing successful snapshots from per-filing failures (a failed individual document fetch is skipped and recorded, never silently dropped and never fabricated into a snapshot) — consistent with "a failed download never produces a signal" (02-data-sources.md) *and* "never converted into no event" (04-infrastructure.md): the caller can tell "zero filings today" apart from "N filings, M of them failed to fetch."
- [ ] Unit tests cover: parsing a realistic fixture submissions JSON into the correct filtered filing list; item-code filtering (in-scope vs. out-of-scope items, e.g. `8.01` alone when not in the interest set); a malformed entry being skipped without raising; the primary-document URL being built correctly from CIK + accession number + primary document filename; a non-200 submissions response raising `SecEdgarError`.
- [ ] System test: an end-to-end run against a fake `http_client` returning fixture responses for both the submissions call and each filing document, verifying the resulting raw snapshots are readable back through STORY-001's `read_raw_snapshot` with the correct source, and that a per-filing HTTP failure shows up in the result's failure list rather than crashing the run or silently vanishing.

## Explicit scope boundary

- No event classification (which item means what, direction, magnitude) — that's the normaliser, STORY-003.
- No scheduling, no persistent CIK universe list, no systemd timer — this story is the collector function itself; wiring it into a scheduled job is deployment (04-infrastructure.md), out of scope here.
- No live call against the real `data.sec.gov` endpoint is exercised by the automated test suite — this development sandbox's network egress does not reach `sec.gov` (verified during this story), and live external calls in an automated test suite are undesirable regardless (flaky, rate-limited, non-deterministic). Field names are pinned to SEC's documented, stable submissions-API schema; the story's Definition of done includes an explicit open item to re-verify against one real response the first time this runs with real network access (the Pi).
- No Form 4, XBRL, or other SEC endpoints — 8-K only, per the story name.

## Definition of done

All seven gates apply. System Tester's "re-run every FROZEN experiment" clause is still vacuous (no experiment is FROZEN yet). Open item carried into deployment: the first real run against live `data.sec.gov` (on the Pi, or from a laptop with unrestricted network) must be manually diffed against this story's fixture assumptions before the collector is trusted unattended.

## Credentials, if any

None. SEC EDGAR requires no API key or registration — only a descriptive `User-Agent` with a contact email, which is configuration, not a secret (see [08-credentials.md](../docs/08-credentials.md)).
