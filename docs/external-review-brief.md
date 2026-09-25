# External review brief — edge-lab

*Self-contained system definition, written to be pasted into a review with another LLM or a human reviewer with no access to this repository. It summarises what is already committed in `docs/`; where this brief and the repository ever disagree, the repository is authoritative.*

## What this is

A personal, point-in-time research lab that tests whether tradable edges exist in US equities, before any capital is committed. It is not a live trading system yet. As of this writing it is in **Phase 0 — Documentation**: principles, rules and experiment specs are being written and committed; no code, no data collection, no trading has happened.

The lab evaluates three independent strategies with different horizons:

| Strategy | Horizon | Question it asks |
|---|---|---|
| **Swing** | 5–20 trading days | Does a stock keep drifting after a material event, once the market has already reacted? |
| **Daily** | Open → close, same session | Is the reaction to a pre-market event still incomplete at the open? |
| **Value** | 6–12 months | Does the market underprice reasonable-quality companies that are cheap and ignored? |

The strategies never share optimised parameters and are never merged into a single combined score (ADR-0007). Each can be accepted or rejected on its own evidence. Planned initial live capital, if any strategy is ever accepted, is small — on the order of €1,000.

## Core philosophy

1. **Evidence before capital.** A strategy trades real money only after it passes acceptance criteria that were frozen *before* results existed.
2. **Point-in-time or nothing.** Every input is tagged with the time at which the system itself could have known it; nothing computed from future information may leak into a decision.
3. **Freeze, then test.** Hypotheses, parameters and pass/fail thresholds are committed to Git before results are seen. Any change after freezing becomes a new experiment, not an edit.
4. **One change per experiment.** Refinements are new experiments, never silent edits to an old one.
5. **Rules decide; models structure.** Language models may classify raw text into a closed taxonomy of event types. They never make an entry, exit or sizing decision (ADR-0001).
6. **No signal is a valid output.** `REJECT` and `INCONCLUSIVE` are treated as successful experiment outcomes, not failures of the process.
7. **Free data first, pay to confirm — not to explore** (ADR-0002).
8. **Reproducibility.** Every result must be regenerable from immutable raw snapshots, a config hash and a code commit.

Explicit non-goals: automatic order execution, competing on sub-minute latency, maximising backtest returns, one unified cross-strategy score, and tax optimisation (noted as material to net returns but out of scope for the research code).

## Point-in-time integrity (the mechanism most of the rest depends on)

Every event/observation carries: `published_at` (source's own timestamp), `first_seen_at` (when this system first observed it live), `known_at` (the time decision logic is allowed to use), `retrieved_at`, `session_date`, `signal_date`, `entry_date`. A decision at time *t* may only use records with `known_at <= t`.

- Live-collected data: `known_at = first_seen_at`.
- Historical data with a reliable timestamp (e.g. SEC EDGAR acceptance time): `known_at = published_at + declared_feed_lag`, where the lag comes from a live latency audit, not an assumption.
- Historical data with a date but no time (e.g. Yahoo analyst actions): treated conservatively — the reaction window spans sessions D and D+1, and the earliest allowed entry is the open of D+2. This is known to understate any real effect; that is treated as the acceptable cost of not looking ahead.
- Historical data with neither a reliable date nor time: excluded outright.
- Rolling statistics (ATR, beta, average volume) are computed through the previous close only. Sector membership is dated (to handle reclassifications like the 2018 GICS move of Meta/Alphabet into Communication Services). Fundamentals are keyed by SEC filing date, not fiscal period end.
- Survivorship: the universe for any historical date includes names later delisted, acquired or bankrupt; coverage gaps and their likely bias direction must be stated in any report that has them.
- Every raw payload is stored exactly as received with a SHA-256 hash; normalised tables are always rebuildable from raw snapshots, and a backtest references the exact snapshot hashes it used.
- LLM outputs are never used to classify events that occurred before that model's training cutoff, when that classification feeds a backtest — to prevent the model "knowing" the outcome. Every LLM-assisted record stores provider, model, version and prompt version.
- Explicitly forbidden as inputs: analyst price targets used as a price/entry level, any forecast/expected/projected indicator, same-day volume/high/low/close in a same-day decision, parameters fitted on the period being tested, and any threshold chosen because it happens to include a known winner.

## Data sources

Free sources only in phases 1–3: SEC EDGAR (8-K events, Form 4 insider transactions, XBRL fundamentals — all with strong, official timestamps), yfinance (daily OHLCV and analyst actions — treated as fragile/unofficial, date-only for analyst actions), Stooq (backup prices), press-release wire RSS and per-ticker news RSS (own `first_seen_at`, headline/URL only — no full article text stored, no paywall circumvention), and GDELT (generic news mentions, 15-minute capture granularity). A failed data download must never silently produce a signal.

A paid vendor stack (~$180–280/month for delisted-inclusive minute bars and timestamped analyst/earnings data) is a candidate upgrade, gated by ADR-0002's rule: buy only after a free-data experiment already shows a positive, cost-surviving result that paid data would confirm with a cleaner/larger sample — never to go exploring.

For live execution (Phase 3+), any price shown to the human operator must be cross-checked against a second source within 1% agreement, display currency/exchange/timestamp/age, and be suppressed rather than shown stale if it can't be verified.

## Architecture (for context, not the focus of a trading-methodology review)

Pipeline: scheduled collectors on a Raspberry Pi write immutable raw snapshots → normalisers do entity linking/dedup/classification into a closed event taxonomy (POSITIVE/NEGATIVE/NEUTRAL/UNKNOWN × event type, e.g. `earnings_release`, `analyst_upgrade`, `insider_purchase`) → a point-in-time feature builder → the three independent experiment tracks → an evaluator (abnormal returns, costs, clustering-aware statistics, controls) → committed Markdown reports and a decision log (human-readable line + JSON record, including rejected candidates and near-misses). Storage is SQLite for operational state, Parquet/DuckDB for research (ADR-0003). There is no automated execution engine — the broker (XTB) has no API, so all orders are placed manually (ADR-0005), which raises the acceptance bar for the Daily strategy in particular since its edge, if any, is smaller and more timing-sensitive.

## Experiment / acceptance protocol

Lifecycle: `DRAFT → FROZEN → RUNNING → ACCEPT | REJECT | INCONCLUSIVE`. Once FROZEN, any change creates a new experiment ID or spec version rather than editing the existing one.

Returns are measured as beta-adjusted abnormal return (`AR = R_stock − β_(t−1) × R_market`), with sector-adjusted return as a robustness check and an ATR-normalised version to compare across volatility regimes. All results are reported gross and net under three cost scenarios (optimistic / base / typical slippage / stress — pessimistic slippage, including actual EUR/USD conversion cost), and in both USD and EUR.

Because events cluster in time (earnings season, strong market days), observations are not treated as independent: either a calendar-time portfolio approach or date-clustered standard errors is required, and results are reported by subperiod (year, market regime) — an effect present in only one subperiod needs an economic explanation or is rejected. Each experiment defines an honest control group (e.g. same gap size with no identified event) with a manual audit estimating the hidden-event rate in that control.

A strategy is accepted only if all five of these are yes: (1) is there an effect; (2) is it larger than the control/base rate; (3) does it survive base costs; (4) is it stable across subperiods/out-of-sample; (5) is it large enough to justify the capital, time and operational burden of running it.

## Strategy definitions

### Swing (5–20 trading days)
Long-only positions entered the next regular-session open after a material, company-specific event is fully known, held for a fixed research horizon (primary: 10 sessions). Hypothesis family is post-event drift (post-earnings-announcement drift, post-revision drift) — contested in the literature as possibly partly a risk premium rather than pure underreaction, hence the requirement for risk-adjusted returns and controls on every swing experiment. Universe: US common stocks, price ≥ $5, 20-day average dollar volume ≥ $20M. Overnight/gap risk is accepted at the research stage and sized for explicitly in the live phase (risk per trade defined by distance to invalidation level *and* a gap scenario, not stop distance alone).

### Daily (same-session, open → close)
Positions opened at the open and closed at the close of the same session, after an event known before 09:30 ET — no overnight exposure. Hypothesis is intraday continuation of a pre-market reaction (the opposite, intraday reversal, is also documented in the literature, so direction is not assumed a priori). Two gates apply before any backtest result is trusted: a feed-latency gate (if most pre-market events aren't observed by this system until after 09:30 ET, the strategy isn't executable regardless of backtest quality) and an execution-realism gate (must survive the stress/pessimistic-slippage cost scenario). Same-day volume, high, low and close are forbidden inputs for the day's own entry decision. Given manual execution and a smaller expected per-trade edge, the acceptance bar here is set higher than for Swing.

### Value (6–12 months)
Long positions in reasonable-quality companies priced well below a conservative valuation and receiving little market attention. The core discipline is separating genuine value candidates (positive/stable operating cash flow, manageable debt, stable-or-improving return on capital, insider buying) from value traps (falling revenue/margins, high leverage/refinancing risk, structurally declining industry, insider selling/dilution). Invalidation is thesis-based (e.g. cash flow turns negative, a leverage covenant is breached) rather than a tight price stop. Forward paper-testing alone would take years to mature, so historical tests on point-in-time SEC XBRL fundamentals and Form 4 insider data carry most of the evidential weight; value has had long real-world periods of underperformance, so subperiod analysis is treated as essential, not optional.

## Risk and capital framework (live phase, still being specified)

Initial live allocation is on the order of €1,000, shared — not duplicated — across whichever strategies are live at a given time; this repository currently records that the split (or a go-live sequencing across strategies) must itself be a frozen, pre-committed decision rather than an implicit trade-by-trade outcome. Planned account-level limits for the live phase (Phase 5) — to be frozen before any capital is committed, the same way an experiment spec is frozen — are: a maximum live-capital drawdown at which all strategies stop opening new positions pending review; a cap on total concurrent open positions across all three strategies, sized to what €1,000 can actually diversify; and a cap on how many open positions may share a sector or event date, so a single sector shock or news day can't hit the whole account at once. As of this writing the specific numeric values for these caps are not yet chosen.

## Current status

Phase 0 (documentation). Experiment specs drafted: EXP-001 (analyst drift, swing), EXP-002 (intraday continuation, daily — blocked pending the feed-latency gate), EXP-003 (8-K drift, swing), EXP-004 (news events, swing/daily — data collection only so far), EXP-V01 (quality-value-insider, value). No experiment has been frozen, run, or has an outcome yet.

## What would be useful from a review

This brief is offered for scrutiny of the *methodology*, not a request to validate a specific trade idea. Areas where outside pressure-testing would be most valuable: whether the point-in-time rules actually close all look-ahead paths they claim to (particularly the date-only conservative rule, and the feed-latency gate for Daily); whether the five-question acceptance protocol and clustering-aware statistics are sufficient given how small and clustered the eventual live sample will be; whether the value strategy's value-vs-trap heuristics are operational enough to code as deterministic rules, or are still qualitative judgment dressed as rules; and whether the account-level risk framework (still unfrozen) is missing anything given a ~€1,000 live account split across three uncorrelated-by-design strategies.
