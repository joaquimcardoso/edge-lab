# STORY-003 — 8-K normaliser and event store

| Field | Value |
|---|---|
| Status | TRADING_REVIEWED |
| Owner stage | Story Agent |

## Source

[07-development-workflow.md §Suggested MVP story sequence, item 3](../docs/07-development-workflow.md#suggested-mvp-story-sequence-phase-1): "Normaliser + event store for 8-K 2.02/1.01, with `known_at` computed per [01-point-in-time-rules.md §2](../docs/01-point-in-time-rules.md)." Event schema and closed taxonomy from [03-architecture.md §Core data model](../docs/03-architecture.md#core-data-model) and [§Closed event taxonomy (V1)](../docs/03-architecture.md#closed-event-taxonomy-v1).

## Goal

Parse a raw `edgar_8k` snapshot ([STORY-002](STORY-002-edgar-8k-collector.md)) into one or more typed `event` rows — one per in-scope Item Information entry found in the filing's own SGML header — with `known_at` computed correctly, and persist them in a dedicated, dedup-safe event store. No text classification: the item code *is* the closed-taxonomy type, taken from SEC's own standard "ITEM INFORMATION:" wording in the header (not from the ephemeral submissions-API `items` field STORY-002 used only for pre-filtering), so an event is fully rebuildable from the raw snapshot alone.

## Acceptance criteria

- [ ] `parse_header_fields(raw_text)` extracts `accession_number`, `acceptance_datetime` (parsed from the `<ACCEPTANCE-DATETIME>` SGML tag, `YYYYMMDDHHMMSS`, converted to ISO-8601 UTC), `cik`, `submission_type`, and every `ITEM INFORMATION:` description line, from the raw complete-submission text.
- [ ] `classify_items(item_descriptions)` maps each description to an item code and a closed-taxonomy `type` via SEC's own standard wording (`ITEM_DESCRIPTION_TO_CODE`, `ITEM_CODE_TO_EVENT_TYPE`) — only for item codes in scope (`2.02` → `earnings_release`, `1.01` → `material_agreement`, `2.01` → `acquisition_disposition`, `8.01` → `other_verified`). An unrecognised description (SEC wording drift, a new item type) is returned separately as unmapped, never silently dropped and never fatal to the rest of the filing.
- [ ] `known_at` is computed per [01-point-in-time-rules.md §2](../docs/01-point-in-time-rules.md)'s live-collected rule: `known_at = first_seen_at` (taken from the raw snapshot row), **never** `published_at + declared_feed_lag` — that formula needs the latency-distribution audit STORY-006 hasn't built yet. `published_at` (from `acceptance_datetime`) is still stored on every event; it is exactly the input STORY-006 will need later.
- [ ] `direction` is always `None` (`UNKNOWN`) for every event this normaliser produces — 8-K direction is not inferred from text in V1 (`03-architecture.md`).
- [ ] Every event stores `snapshot_id` (the raw snapshot it was derived from) and `classifier_version` (a fixed string identifying this deterministic ruleset), so a rule change is auditable and every event is traceable back to its raw evidence.
- [ ] The event store rejects/dedups a second write of the same `(source, source_id, type)` — re-normalising the same snapshot twice must not create duplicate events. `source_id` is the filing's accession number.
- [ ] `normalise_snapshot(snapshot_id, ...)` reads one raw snapshot, parses, classifies, and writes its resulting events, returning which were written and which item descriptions (if any) were unmapped.
- [ ] Unit tests cover: header parsing against a realistic fixture SGML header; item-description-to-taxonomy-type mapping for all four in-scope items; an unrecognised item description being returned as unmapped rather than raised; `known_at` equal to the snapshot's `first_seen_at`; a malformed/incomplete header not crashing the parse.
- [ ] System test: `normalise_snapshot` run end-to-end against a raw snapshot actually written through STORY-001/002's store, verifying the resulting event rows read back correctly and that running it twice on the same snapshot does not duplicate events.

## Explicit scope boundary

- **`session_date` is not computed in this story.** Correctly mapping an acceptance time to a trading session (rule 3) needs a real exchange-calendar library (trading days, half-days, holidays, DST) — [01-point-in-time-rules.md §3](../docs/01-point-in-time-rules.md) explicitly warns "never hard-code" this. Faking it with a naive weekday check would be a real point-in-time bug wearing a passing test. Every event's `session_date` is `None` until a follow-up story adds a proper calendar dependency; nothing downstream may treat `None` as "same day."
- **`security_id` is the zero-padded CIK, not a full security record.** No `security` table (ticker, name, delisted history — `03-architecture.md`'s `security` table) exists yet. Using CIK directly is stable and sufficient for STORY-003; ticker/name resolution is deferred to whichever future story needs it (likely alongside `prices_daily`, STORY-004, which needs the same mapping).
- No FinBERT, no LLM classification of any kind — item-code-to-type mapping is fully deterministic, consistent with [ADR-0001](../adr/0001-no-llm-in-decision-path.md).
- No entity linking beyond CIK passthrough, no cross-source dedup (e.g. against a wire-news mention of the same event) — single-source normalisation only.
- Only 8-K events are normalised here; Form 4 (insider) and other sources are separate future normalisers.

## Definition of done

All seven gates apply. System Tester's "re-run every FROZEN experiment" clause remains vacuous — no experiment is FROZEN yet.

## Credentials, if any

None. Pure parsing and local storage; no external calls.
