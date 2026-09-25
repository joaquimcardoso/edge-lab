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

### STORY-003 — 8-K normaliser and event store (2026-09-25)

1. **Did this feature close what it claimed to?** Yes, with one honest non-closure recorded rather than papered over: `session_date` is deliberately left `None` on every event, because computing it correctly needs a real exchange-calendar library (trading days, half-days, DST) that this story does not add — [01-point-in-time-rules.md §3](01-point-in-time-rules.md) explicitly warns against a naive/hard-coded version, and this story takes that warning literally rather than shipping something that *looks* done. `known_at` is correctly computed (`= first_seen_at`, the live-collected rule), and events are fully rebuildable from the raw snapshot alone (item classification reads the stored SGML header text, not the ephemeral submissions-API field). 44/44 tests green (18 new unit, 2 new system, 24 unchanged from STORY-001/002).
2. **Does anything here change the next story's priority?** Yes, worth naming explicitly rather than silently reordering: `session_date` being unresolved means **no experiment can actually run yet even once `prices_daily` and the feature builder exist** — every experiment spec depends on session-date mapping to define its reaction window. [STORY-004](../docs/07-development-workflow.md#suggested-mvp-story-sequence-phase-1) (`prices_daily` collector) does not itself need `session_date` and can proceed as planned. But the exchange-calendar dependency this story deferred should be pulled in explicitly — either as its own small story before STORY-005 (feature builder, which *does* need trading-day arithmetic for rolling windows) or folded into STORY-005 directly. Recorded here so it isn't quietly forgotten by the time it's blocking.
3. **Should the backlog pause rather than continue?** No blocking concern for STORY-004. Not a HALT — a REPRIORITISE-adjacent note: the exchange-calendar dependency is now a named prerequisite for STORY-005, not a surprise to rediscover later.

**Decision: PROCEED** (to STORY-004), **with a backlog note**: add exchange-calendar handling (trading-day/session-date resolution) as an explicit prerequisite before STORY-005 (feature builder) starts, since STORY-005's rolling-window features and STORY-003's deferred `session_date` need the same dependency.

### STORY-004 — prices_daily collector, normaliser and store (2026-09-25)

1. **Did this feature close what it claimed to?** Yes, with one honestly-recorded weaker guarantee: unlike `edgar_8k`, what this story stores as "raw" is yfinance's own parsed DataFrame (CSV-serialised), not Yahoo's original wire bytes -- reimplementing yfinance's cookie/crumb HTTP handling to capture the true raw response was judged a worse trade than accepting one processing layer's remove. Both raw close and adjusted close are stored as distinct columns, as required. 59/59 tests green (18 new unit, 2 new system, 39 unchanged).
2. **Does anything here change the next story's priority?** No. Item 4a (exchange-calendar integration, added after STORY-003's review) remains the correct next step before the feature builder (item 5) — `prices_daily` doesn't need it and wasn't expected to.
3. **Should the backlog pause rather than continue?** No blocking concern. One thing worth flagging for the eventual Pi deployment rather than blocking development now: this story's yfinance dependency has never been exercised against live Yahoo Finance in this sandbox (same open item pattern as STORY-002's SEC EDGAR schema) — compounded by yfinance's own documented fragility (`02-data-sources.md`: real risk of 429 throttling and silent breakage). Both collectors share the same carried-forward pre-deployment verification requirement.

**Decision: PROCEED.** Item 4a (exchange-calendar integration) stays next, ahead of STORY-005 (feature builder), per the STORY-003 review.

### STORY-005 — Exchange-calendar integration (2026-09-25)

1. **Did this feature close what it claimed to?** Yes. `is_trading_day`/`next_trading_day`/`compute_session_date` are backed by a real, maintained NYSE calendar library rather than a hand-rolled weekday check, and STORY-003's carried-forward open item (`session_date` left `None`) is now closed — the `edgar_8k` normaliser computes it correctly. 74/74 tests green (15 new, 2 intentionally updated to their now-correct computed values, 57 unchanged).
2. **Does anything here change the next story's priority?** No. STORY-006 (feature builder) was already gated on this story per the STORY-003 review and is now unblocked — no new information here changes what comes after it.
3. **Should the backlog pause rather than continue?** No blocking concern. One thing worth naming: this story's scope boundary explicitly deferred half-day-aware intraday cutoffs (a half day still resolves as a full trading day for session-date purposes) — fine for `session_date` resolution, but Daily's Gate 0 (STORY-007, feed-latency audit) will need to handle early closes precisely once it's built. Not a blocker now; flagged so it isn't a surprise then.

**Decision: PROCEED.** STORY-006 (feature builder) may leave DRAFT.

### STORY-006 — Point-in-time feature builder (2026-09-25)

1. **Did this feature close what it claimed to?** Yes. ATRpct20, ADV20 and zero-intercept beta252 are implemented to match the exact formulas already frozen in EXP-001/EXP-002/05-experiment-protocol.md, not reinvented or approximated -- including the specific detail that ATR uses Wilder's smoothing (not a simple moving average) and beta is a no-intercept OLS estimator (not cov/var). The point-in-time cutoff is enforced structurally at the read layer and proven by a test that plants a same-day "poison" price row and confirms it never leaks in. A real alignment bug (pairing stock/market returns by list position instead of trading date) was caught and fixed during review, before any test existed to hide it. 90/90 tests green (14 new unit, 2 new system, 74 unchanged).
2. **Does anything here change the next story's priority?** No. STORY-007 (feed-latency audit harness, Gate 0 for EXP-002) was already next and doesn't depend on this story's output beyond the calendar dependency STORY-005 already provides.
3. **Should the backlog pause rather than continue?** No blocking concern. Worth naming: this story explicitly does not build a materialised/cached feature table -- every call recomputes from `price_daily` directly. Fine at current data volumes; if an experiment run's runtime becomes dominated by feature recomputation, that's a legitimate future story, not a hidden cost today.

**Decision: PROCEED.** STORY-007 (feed-latency audit harness) may leave DRAFT.

### STORY-007 — Feed-latency audit harness, Gate 0 (2026-09-25)

1. **Did this feature close what it claimed to?** Yes. Gate 0's pass bar is applied exactly as EXP-002 specifies it (both conditions independently required, proven by tests where each bar fails alone while the other passes), and the full lag distribution is reported, not just a median that could hide a bad tail. Two real correctness gaps were caught and fixed during review before any test existed to hide them: a cross-module reach into another module's private constants, and — more importantly — a same-day/next-day confusion in the "seen before open" check that would have overstated a source's real pre-market visibility whenever a filing was missed on its actual day and only picked up early the following morning. That second bug is exactly the kind of thing Gate 0 exists to catch in the *data*; it would have been ironic to ship it in the *audit tool*. 105/105 tests green (14 new unit, 1 new system, 90 unchanged).
2. **Does anything here change the next story's priority?** This completes the originally-planned Phase 1 MVP sequence (STORY-001 through STORY-007, docs/07-development-workflow.md) — there is no "next story" already queued. What comes after Phase 1 (running an actual 2-3 week live polling campaign on the Pi to feed this harness real data, then EXP-001/002/V01 themselves) is deployment and research work, not more engineering backlog this document already anticipates.
3. **Should the backlog pause rather than continue?** Not a HALT, but a genuine stopping point: every MVP story is now DEPLOYED and TRADING_REVIEWED with 0 unexplained regressions throughout, and every carried-forward open item is named rather than silently dropped (edgar_8k and yfinance schema assumptions un-verified against live traffic in this sandbox; half-day-aware intraday cutoffs deferred; no materialised feature cache). The honest next step is Pi deployment and the live data collection this whole pipeline was built to support — not something this repository's own test suite can gate further on its own.

**Decision: PROCEED to Phase 1 deployment.** No further MVP story is queued; the next work is operational (Pi deployment, live collection) rather than another repository story, pending the user's direction.

### STORY-008 — Pi collector entrypoint and deploy scaffold, Gate 0 scope (2026-09-25)

1. **Did this feature close what it claimed to?** Yes, within its stated scope. There is now a runnable path from "tagged code" to "something a systemd timer can execute": a typed `config.py` that refuses to silently default a User-Agent or data directory, a real (non-fake) `RequestsHttpClient`, an entrypoint (`scripts/collect_premarket_8k.py`) that wires the existing STORY-002/003 collector and normaliser together and distinguishes success / per-CIK failure / zero-filings-today rather than collapsing them, and installable systemd units matching docs/04-infrastructure.md's schedule exactly (time zone, window, `RequiresMountsFor`). Two real bugs were caught during review, before being fixed and only then covered by a test: a normalisation failure for one snapshot would have propagated and killed the rest of that CIK's run instead of being recorded as an isolated failure (the same "one bad record must not blind the whole run" principle STORY-002's own collector already followed, missed on the newer path); and `load_universe`'s header-validation used an inverted subset check, so a wrong-header CSV would have crashed with an unrelated `KeyError` instead of raising the named `UniverseError` a caller is supposed to be able to catch. 122/122 tests green (17 new, 105 unchanged) — 0 regressions.
2. **Does anything here change the next story's priority?** Confirms, rather than changes, the direction the user already chose: build for Gate 0 operational health first (STORY-009 daily ops report, STORY-010 good-day/bad-day rubric), not a trading-signal or paper-trading story — those remain correctly blocked behind Gate 0 and EXP-002's own frozen prerequisites, and nothing in this story's implementation surfaced a reason to reorder that.
3. **Should the backlog pause rather than continue?** No. One honest limitation, stated rather than hidden: this sandbox is macOS with no reachable systemd or physical Pi, so the `.service`/`.timer` files are verified only as well-formed INI with the required directives present — real `systemd-analyze verify` and an actual install are deferred to whoever runs `deploy/install.sh` on the device. `config/universe.csv`'s starter list is also explicitly a placeholder for the user to review, not a vetted selection — flagged here so it isn't mistaken for one later.

**Decision: PROCEED to STORY-009 (daily operations report artifact).**

