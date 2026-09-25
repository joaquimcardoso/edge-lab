# 10 — Terminology reconciliation: mission document vs. this repository

## Purpose

An external review document proposed a Research → Replay → Paper Trading → Live Signal target architecture, using its own vocabulary. Much of what it describes already exists in this repository under different names, frozen before that document existed. This page maps one to the other so future work (mine or anyone's) never reinvents parallel terms, or worse, parallel *mechanisms*, for the same concept.

## Strategy lifecycle

| Mission document | This repository | Where frozen |
|---|---|---|
| `EXPERIMENT` | `DRAFT` | [05-experiment-protocol.md](05-experiment-protocol.md) |
| `DEVELOPMENT` | Development dataset | [05-experiment-protocol.md](05-experiment-protocol.md)'s dataset table |
| `VALIDATION` | Validation dataset ("the frozen spec's primary test — ACCEPT/REJECT/INCONCLUSIVE is decided on this") | Same |
| `OUT_OF_SAMPLE` | Final holdout (opened once, post-validation-pass only) | Same |
| Promotion gate | The five acceptance questions (effect exists; larger than base rate; survives base cost scenario; stable across subperiods/out-of-sample; large enough to justify capital/time) | Same |
| `PAPER` | Phase 3, "Forward paper trading — Live signals, paper log, no capital" | [00-vision.md](00-vision.md#roadmap) |
| `LIVE_SIGNAL` | Also Phase 3+ ("Live signals"); [01-point-in-time-rules.md](01-point-in-time-rules.md) §10's "Live-data freshness (Phase 3+)" already governs signal suppression on stale data | [00-vision.md](00-vision.md), [01-point-in-time-rules.md](01-point-in-time-rules.md) |
| Walk-forward / OOS discipline | "Walk-forward/out-of-sample splits are required from the moment any parameter is chosen using data" | [05-experiment-protocol.md](05-experiment-protocol.md) |

**Nothing here changes 05-experiment-protocol.md's acceptance criteria.** They were already more specific than the mission document's ask (three named cost scenarios, not just "gross vs net"; a named minimum-sample requirement per spec). This document reconciles vocabulary, not substance.

## Execution modes

| Mission document | This repository |
|---|---|
| `BACKTEST` | [src/edgelab/signals/execution_mode.py](../src/edgelab/signals/execution_mode.py)'s `ExecutionMode.BACKTEST` (STORY-011) |
| `HISTORICAL_REPLAY` | `ExecutionMode.HISTORICAL_REPLAY` (not yet backed by a replay engine — see [10-terminology-reconciliation.md](#agent-roles) below) |
| `PAPER` | `ExecutionMode.PAPER` (not yet backed by a paper portfolio) |
| `LIVE_SIGNAL` | `ExecutionMode.LIVE_SIGNAL` (not yet backed by a live strategy — none is validated) |

## Point-in-time terminology

The mission document asks for "event date, publication date, effective date, availability timestamp, market timestamp" to be distinguished. This repository already has a strictly more precise set: `published_at`, `first_seen_at`, `known_at`, `retrieved_at`, `session_date`, `signal_date`, `entry_date` ([01-point-in-time-rules.md](01-point-in-time-rules.md) §1). No new terminology is introduced.

## Agent roles

| Mission document | This repository | Status |
|---|---|---|
| Lead Architect | Orchestrator Agent | Exists |
| Quant/Research Agent | Trading Expert Agent | Exists — same rubric (experiment design, statistical methodology, biases, validation, acceptance criteria) |
| Data Engineer Agent | Reviewer Agent's own checklist already covers point-in-time correctness, forbidden inputs, reconstructability | Exists (folded into Reviewer, not separate) |
| Trading Simulation Agent | New — [trading-simulation-agent.md](agents/trading-simulation-agent.md) | Not yet activated (STORY-012) |
| Signal/Execution Agent | New — [signal-execution-agent.md](agents/signal-execution-agent.md) | Not yet activated (STORY-012) |
| Notification Agent | New — [notification-agent.md](agents/notification-agent.md) | Not yet activated until STORY-013 |
| QA Agent | Unit Tester + System Tester Agents already cover this ground; no separate adversarial-QA role added | Exists (folded into existing roles) |
