# 06 — Trading system audit v1

Consolidates two independent external LLM reviews of [external-review-brief.md](external-review-brief.md), checked against what is actually committed in this repository (not just against the brief, which is a summary and understates precision that exists at the experiment level in places). Tracks what's resolved and what's still open before Phase 1 starts.

## How to read this

Both reviewers praised the same core: point-in-time discipline, freeze-then-test, immutable raw snapshots, independent strategies, REJECT/INCONCLUSIVE as valid outcomes, and no LLM in the decision path. Neither reviewer disputed that. This document does not re-litigate it.

Both reviewers also independently flagged Value's qualitative language ("reasonable-quality," "manageable debt," "cheap") as not yet deterministic. **That critique is valid against [strategies/value.md](strategies/value.md), but [EXP-V01](experiments/value/EXP-V01-quality-value-insider.md) already has hard boolean gates** (positive operating cash flow 3/3 years, net debt/EBITDA ≤ 3.0, share issuance ≤ 5%, FCF-yield top quintile, insider Form 4 code P net of sales). The gap is real but narrower than either reviewer thought: `value.md` states the philosophy, `EXP-V01` freezes the numbers — that split is intentional (strategy docs don't hardcode what's supposed to be frozen per-experiment), but it means a reviewer handed only the brief will always flag this as unresolved. Fix applied: `EXP-V01`'s insider gate now excludes Rule 10b5-1 scheduled purchases, which the brief-level description couldn't have surfaced either way.

Similarly, "exactly which event types qualify" for Swing reads as open in `swing.md`, but `EXP-001` (analyst upgrade / target raise only) and `EXP-003a/b` (8-K 2.02 / 1.01 only, tested separately) already scope this precisely. What is genuinely open is event handling *inside* an open position, not eligibility at entry — see below.

## Resolved (this pass)

| Item | Where |
|---|---|
| Account-level risk limits were an empty placeholder | [00-vision.md](00-vision.md#account-level-risk-limits-phase-5) — proposed defaults: sequential (not simultaneous) strategy launch starting with Swing, 15% (~€150) drawdown breaker, 5 concurrent positions cap, minimum-viable-risk check against broker ticket size |
| Capital allocation across strategies was undocumented | [00-vision.md](00-vision.md#capital-allocation-across-strategies) |
| Daily and Value had no "Live-phase considerations" section (Swing did) | [strategies/daily.md](strategies/daily.md), [strategies/value.md](strategies/value.md) |
| Swing's correlation cap was stated with no number or owner | [strategies/swing.md](strategies/swing.md) |
| Gate 0 (Daily feed latency) had no numeric pass/fail bar | [EXP-002](experiments/daily/EXP-002-intraday-continuation.md#gate-0--feed-latency-runs-first) — proposed: ≥80% of pre-market events seen before 09:30 ET, median lag ≤30s vs. primary wire |
| `known_at` lag was a single number, not a distribution | [01-point-in-time-rules.md §2](01-point-in-time-rules.md) — now a conservative percentile by source × event type × session |
| No processing-latency chain beyond source lag | [01-point-in-time-rules.md §2](01-point-in-time-rules.md) — `source_time → first_seen_at → normalized_at → classified_at → signal_generated_at → operator_seen_at → order_submitted_at → fill_at` |
| No amendment/revision rule | [01-point-in-time-rules.md §11](01-point-in-time-rules.md) |
| No corporate-action methodology | [01-point-in-time-rules.md §12](01-point-in-time-rules.md) — open item with a proposed default (adjusted close for returns/rolling stats, raw close for gaps) |
| No beta estimation window | [01-point-in-time-rules.md §5](01-point-in-time-rules.md) — proposed: 252 sessions, min 60 obs, zero-alpha |
| Across-experiment multiple testing wasn't addressed (only within-experiment) | [05-experiment-protocol.md](05-experiment-protocol.md#multiple-testing-across-experiments) — dev/validation/holdout hierarchy, open item |
| Hidden-event audit had no quantitative pass bar | [05-experiment-protocol.md](05-experiment-protocol.md#controls) — proposed: hidden-event rate ≤15% |
| No `Minimum sample` for EXP-002 / EXP-V01 (EXP-001 had one) | Added to both, proposed defaults, INCONCLUSIVE-not-REJECT below the bar |
| EXP-001F date-only dilution was asserted, not measured | [EXP-001](experiments/swing/EXP-001-analyst-drift.md) — new diagnostic metric comparing D+2 vs. S+1 captured return |
| Mid-hold event contamination (event lands *during* the 10-session hold, not just near entry) | [EXP-001](experiments/swing/EXP-001-analyst-drift.md), [EXP-003](experiments/swing/EXP-003-8k-drift.md) — flagged `event_during_hold`, open item |
| EXP-002 ACCEPT could be read as clearing Daily for live capital | [EXP-002](experiments/daily/EXP-002-intraday-continuation.md#follow-up) — now explicit: live capital is gated behind EXP-002B (the executable-price version), not EXP-002 alone |
| EXP-V01 insider gate didn't exclude scheduled 10b5-1 purchases | [EXP-V01](experiments/value/EXP-V01-quality-value-insider.md) |

## Open — priority 1 (blocks trusting any experiment's result)

- **Multiple testing / holdout discipline.** The dev/validation/holdout split now exists as a stated principle but the actual data partitioning is not implemented or enforced anywhere. Until it is, an ACCEPT across several experiments cannot be fully trusted even though each spec was honestly frozen.
- **Beta/benchmark/return-definition freeze.** Proposed defaults are now recorded (252-session window, zero-alpha, SPY). They still need a conscious sign-off, and single-factor (beta-only) risk-adjustment likely isn't enough on its own — sector adjustment is already a robustness check, but size/momentum/liquidity exposure of the event-selected universe is not tested anywhere.
- **Corporate-action methodology.** A default is proposed; nothing enforces it yet, and it touches every return/gap/ATR calculation once collectors exist.

## Open — priority 2 (blocks a specific strategy)

- **Swing/8-K:** deterministic rule for multiple events on one name inside the hold window (reset clock / separate observations / cluster) — currently only flagged, not decided.
- **Daily:** EXP-002B (the executable-price variant) exists as a planned follow-up; it is now explicitly required before live capital, but is not written as a full spec yet.
- **Value:** portfolio-construction parameters beyond formation (max single-name/sector exposure within the equal-weight basket, cash allocation between monthly cohorts, whether quality gates are re-checked during the 12-month hold or only at entry) are not yet specified.

## Open — priority 3 (blocks live capital, not blocks research)

- **Control matching dimensions.** Current controls match on 2–3 variables (sector, reaction/gap bucket, month). Both reviewers suggested adding market cap, liquidity, prior volatility/trend, earnings proximity. Worth doing, but not for free: over-matching on a small sample shrinks the usable control pool further, which cuts directly against the sample-size concern above. Any addition here should be tested for how much it shrinks N before being frozen.
- **Strategy correlation.** "Independent by design" (ADR-0007) is about not sharing parameters or a combined score — it is not evidence the three strategies' live P&Ls will be uncorrelated. `corr(Swing, Daily)`, `corr(Swing, Value)`, `corr(Daily, Value)` and joint drawdown under stress should be measured once there's a paper-trading history, and factored into the account-level position/sector caps in [00-vision.md](00-vision.md#account-level-risk-limits-phase-5).
- **Research-integrity kill switch.** Distinct from the account-level drawdown breaker: a rule that halts a research run (not live trading) on source-coverage drop, timestamp-completeness decay, duplicate-event spikes, or a classifier-distribution shift, reporting `DATA INVALID` rather than a best-effort number. Not yet specified anywhere.
- **Per-trade risk-level caps** (max planned loss, max notional, max gap-loss assumption, pre-entry cancellation conditions) beyond the account-level caps already in [00-vision.md](00-vision.md#account-level-risk-limits-phase-5).
- **Cost-per-operational-unit.** With ~€1,000 split across strategies, execution/monitoring burden (not just spread/commission/FX) may dominate the edge on small positions. No estimate exists yet of expected net edge per trade after *all* costs including human time.

## Not adopted as-is

- A blanket "minimum 100 trades across 3 regimes" sample floor (one reviewer's suggestion) wasn't applied uniformly — EXP-001 already requires 150, which is stricter; Value's 12-month holding period makes a trade-count floor the wrong unit, so its proposed floor is stated in cohorts instead (24 monthly cohorts / ≥20 holdings per cohort). Each experiment keeps its own frozen number rather than inheriting one lab-wide constant.
- Specific numeric thresholds one reviewer proposed for Value's leverage/quality gates (e.g. interest coverage > 3.0×) were not inserted into EXP-V01, since EXP-V01 already has its own frozen quality gates (different metric, same intent) and swapping in a different reviewer's numbers post hoc would be exactly the kind of after-the-fact parameter change principle 3 exists to prevent. Noted here as a candidate for a *new* experiment variant, not a retroactive edit.

## Trading-expert review log

One entry per DEPLOYED story, per [Trading Expert Agent](agents/trading-expert-agent.md) — rubric answered before the next story leaves DRAFT.

### STORY-001 — Raw snapshot store (2026-09-25)

1. **Did this feature close what it claimed to?** Yes. The story's own scope was narrow by design — an immutable, content-addressed, SHA-256-verified, append-only store for one fetch attempt's raw payload, gzip-compressed per [ADR-0006](adr/0006-immutable-raw-snapshots.md). All acceptance criteria in [STORY-001](../stories/STORY-001-raw-snapshot-store.md) are met: empty-payload rejection with no row written, hash-tampering detected on read, identical content at different `retrieved_at` produces two rows sharing one on-disk blob, `first_seen_at` defaults correctly, no update/delete function exists anywhere in the module's public API. 12/12 tests green (10 unit, 2 system); the regression gate is vacuous — no experiment is `FROZEN` yet, so there is nothing to have regressed.
2. **Does anything here change the next story's priority?** No. Nothing built in this story touches a priority-1/2/3 open item above — it's infrastructure underneath all of them, not a fix to any of them. [STORY-002](../docs/07-development-workflow.md#suggested-mvp-story-sequence-phase-1) (the `edgar_8k` collector) was already next in the MVP sequence and stays next.
3. **Should the backlog pause rather than continue?** No blocking concern. This story makes no trading-methodology claim to evaluate — it is plumbing, not a strategy or a signal — so there is nothing here for a trading-methodology review to accept or reject in the ACCEPT/REJECT/INCONCLUSIVE sense.

**Decision: PROCEED.** STORY-002 may leave DRAFT.

### STORY-002 — EDGAR 8-K collector (2026-09-25)

1. **Did this feature close what it claimed to?** Yes, and it also closed something the review pass had only partially flagged: the collector stores the *complete* SGML-headed submission text file, not the rendered primary document, specifically so `known_at` can later be derived from data the raw store actually has (ACCEPTANCE-DATETIME is in that header) rather than from an ephemeral API response nothing persists. That's a stronger point-in-time guarantee than the story's own source item asked for, caught by the Reviewer gate rather than assumed compliant. 24/24 tests green (10 unchanged from STORY-001 plus 14 new); regression gate still vacuous — no experiment is `FROZEN` yet.
2. **Does anything here change the next story's priority?** No. [STORY-003](../docs/07-development-workflow.md#suggested-mvp-story-sequence-phase-1) (normaliser + event store, computing `known_at` from the raw 8-K submissions this story now produces) was already next and is now directly unblocked — this collector is exactly what STORY-003 needs to consume. No priority-1/2/3 open item above is touched by this story.
3. **Should the backlog pause rather than continue?** No blocking concern. One open item worth tracking explicitly rather than treating as resolved: this collector's field-name assumptions (SEC's submissions-API schema) have not been checked against one real, live response — this sandbox's network egress doesn't reach `data.sec.gov`. That verification is required before this collector is trusted unattended on the Pi (STORY-002's own Definition of done), but it does not block continuing to build STORY-003 against the fixture-verified parsing logic in the meantime.

**Decision: PROCEED.** STORY-003 may leave DRAFT. Carried-forward open item: verify `edgar_8k`'s field-name assumptions against one real `data.sec.gov` response before unattended Pi deployment (not before continuing development here).

