# STORY-012 — Terminology reconciliation and new agent specs

| Field | Value |
|---|---|
| Status | TRADING_REVIEWED |
| Owner stage | Story Agent |

## Source

Same external review document as STORY-011. Docs-only: a reconciliation between that document's vocabulary (`EXPERIMENT → DEVELOPMENT → VALIDATION → OUT_OF_SAMPLE → PAPER → LIVE_SIGNAL`) and this repository's already-frozen equivalents (`DRAFT → FROZEN → RUNNING → ACCEPT/REJECT/INCONCLUSIVE`, [05-experiment-protocol.md](../docs/05-experiment-protocol.md)), so future work never reinvents parallel terms for the same thing. Plus specs for the three genuinely new agent roles the mission document names that don't map onto an existing role: Trading Simulation, Signal/Execution, Notification.

## Goal

`docs/10-terminology-reconciliation.md` plus three new `docs/agents/*.md` + `.claude/agents/*.md` pairs, written in the same format as every existing agent spec, each explicitly marked not-yet-activated (no subsystem exists for them to operate on yet, except Notification once STORY-013 lands).

## Acceptance criteria

- [ ] `docs/10-terminology-reconciliation.md` maps every mission-document term to its repository equivalent (or states plainly there is none yet): EXPERIMENT≈DRAFT, DEVELOPMENT≈FROZEN's Development dataset, VALIDATION≈Validation dataset ("the frozen spec's primary test"), OUT_OF_SAMPLE≈Final holdout, PAPER≈Phase 3 "Forward paper trading," LIVE_SIGNAL≈Phase 3+'s "Live signals" (00-vision.md). Explicitly notes: the mission document's ACCEPT-gates-promotion principle already exists (05-experiment-protocol.md's five questions); nothing here changes that document's acceptance criteria.
- [ ] `docs/agents/trading-simulation-agent.md` + `.claude/agents/trading-simulation.md`: owns the (not yet built) replay engine and paper portfolio -- chronological, no-future-information processing over already-collected data, simulated fills/fees/slippage/P&L. Non-goals: does not decide strategy logic, does not touch Phase 1 collection stores except to read from them.
- [ ] `docs/agents/signal-execution-agent.md` + `.claude/agents/signal-execution.md`: owns the (STORY-011-built) `Signal`/`ExecutionMode`/`Strategy` contracts plus, once built, the signal store, dedup, and risk checks. Non-goals: does not decide whether a strategy is statistically valid (Trading Expert Agent's job via the experiment protocol), does not add order-execution code (ADR-0005).
- [ ] `docs/agents/notification-agent.md` + `.claude/agents/notification.md`: owns Telegram formatting/sending once it exists (STORY-013). Non-goals: never constructs a trading-relevant number itself (entry/stop/target come only from a `Signal`, never from free-form generation); explanation text may eventually be LLM-assisted but the structured fields never are (mission document's own "never construct important trading parameters using free-form LLM output").
- [ ] Every new agent spec states plainly, in an explicit "Status" note, that it is not yet activated -- there is nothing for it to do until its subsystem exists -- so it isn't mistaken for a live role.

## Explicit scope boundary

- No code -- this story is entirely documentation.
- Does not change `05-experiment-protocol.md`'s frozen acceptance criteria, `00-vision.md`'s roadmap, or any existing agent's spec (other than a later cross-reference addition once these subsystems exist, out of scope here).

## Definition of done

Docs-only story: Story Agent + Reviewer Agent gates apply (content accuracy, cross-references correct); no code gates (Unit/System Tester, Integrator) apply beyond confirming the full test suite is unaffected.

## Credentials, if any

None.
