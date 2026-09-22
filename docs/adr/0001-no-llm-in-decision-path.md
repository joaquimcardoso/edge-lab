# ADR-0001 — No LLM in the decision path

**Status:** Accepted

## Context
LLMs can turn news text into structured events, but their outputs vary across versions, are hard to test, and models trained after historical events may leak future knowledge into backtests.

## Decision
LLMs may only map text to the closed event taxonomy. Entry, exit and sizing decisions come exclusively from deterministic, versioned rules. LLM classification is not used on pre-cutoff historical events feeding a backtest.

## Consequences
- Every LLM output stores provider, model, version and prompt version.
- A model change is an experimental change.
- Historical experiments rely on structured sources (SEC, vendor fields) or frozen classifiers.
