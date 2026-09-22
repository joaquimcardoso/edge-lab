# EXP-004 — News events

| Field | Value |
|---|---|
| Strategy | Swing / Daily |
| Status | DATA COLLECTION ONLY |
| Spec version | 0.0.1 |

No hypothesis is frozen yet. The goal of this phase is to accumulate a point-in-time news archive so a future experiment starts with months of clean data.

## Collection

- Press-release wires RSS, Yahoo Finance / Nasdaq RSS for universe tickers, GDELT 15-minute files.
- Stored: headline, URL, source, declared `published_at`, `first_seen_at`, raw snapshot hash. No full text.

## Processing pipeline (built when the experiment is activated)

1. **Entity linking:** SEC `company_tickers.json` + alias dictionary + cashtags.
2. **Deduplication:** canonical URL + normalised-title hash; keep earliest `first_seen_at` and `n_sources`.
3. **Classification:** closed taxonomy from [03](../../03-architecture.md); rules → FinBERT (ONNX int8) → optional LLM for ambiguous cases, versioned.

## Candidate questions (not frozen)

- Does news novelty (first story on a topic) add information beyond the 8-K and analyst events?
- Does `n_sources` (attention) predict continuation or reversal?

## Activation criteria

- At least 6 months of archive
- Entity-linking precision measured on a manual sample
- EXP-001 and EXP-003 concluded
