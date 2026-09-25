# 05 — Experiment protocol

## Lifecycle

```text
DRAFT → FROZEN → RUNNING → ACCEPT | REJECT | INCONCLUSIVE
```

- **DRAFT:** spec under discussion. Parameters may change.
- **FROZEN:** spec, config and acceptance criteria committed and tagged (`exp-001-frozen`). From here, any change creates a new experiment ID or a new major spec version.
- **RUNNING:** data collection or backtest in progress. No peeking at partial results to adjust parameters.
- **Outcome:** written into the spec file with a link to the report.

## Spec template

Every experiment file contains:

1. Hypothesis H1 and null H0
2. Event definition and source
3. Timing rules (reference to [01](01-point-in-time-rules.md))
4. Universe and filters, with exact formulas
5. Entry and exit
6. **One primary metric and one primary horizon**
7. Secondary metrics (descriptive only)
8. Controls
9. Cost scenarios
10. Statistical method
11. Minimum sample
12. Acceptance criteria
13. Known limitations
14. Outcome

## Returns

- **Primary:** beta-adjusted abnormal return  
  `AR = R_stock − β_(t−1) × R_market`
- **Robustness:** sector-adjusted return  
  `SR = R_stock − R_sector_etf(as of event date)`
- **Normalised:** `AR / ATR%20_(t−1)`, used to compare stocks with different volatility. R-multiples are not used while experiments have no stops.
- Market benchmark: SPY. Sector benchmarks: sector ETFs with dated membership.

## Costs

All results are reported gross and net under three scenarios:

| Scenario | Per round trip |
|---|---|
| Optimistic | spread + commission |
| Base | + typical slippage |
| Stress | + pessimistic slippage (open auction for daily) |

Costs include the EUR/USD conversion actually charged by the broker account, unless the account holds a USD balance. Results are reported in USD and in EUR.

## Statistics

- Events cluster in time (earnings season, strong market days). Observations are **not** independent.
- Use one of:
  - **calendar-time portfolio:** daily return of all open positions, tested as a time series; or
  - **standard errors clustered by date**.
- Report subperiod results (by year and by market regime). An effect present in only one subperiod needs an economic explanation or is rejected.
- Walk-forward/out-of-sample splits are required from the moment any parameter is chosen using data. For fully frozen specs, subperiod stability is the robustness check.

## Controls

Each experiment defines a control group that isolates the variable being tested (e.g. same gap size without an identified event). Control labels describe what is known, not what is assumed: `NO_IDENTIFIED_ANALYST_EVENT`, not `NO_CATALYST`. A manual audit of ~200 control observations estimates the hidden-event rate. **A control group is usable as a benchmark only if its estimated hidden-event rate is below a frozen threshold (proposed default: 15%)** — otherwise "no identified event" mostly means "our classifier missed it," not a genuine absence of a catalyst.

## Contamination rules

- Events within ±2 sessions of an earnings release (8-K 2.02) are excluded from non-earnings experiments, or reported as a separate subgroup.
- Several events on the same security and session are collapsed into one observation, with the count kept as an attribute.

## Near misses

Candidates that fail exactly one filter are logged with their outcome. They are never used to change a frozen spec. They may motivate a new experiment.

## Multiple testing across experiments

Freezing a spec before running it stops *within-experiment* hindsight. It does not stop *across-experiment* data mining: running EXP-001, EXP-003, EXP-004, EXP-V01 and their sub-variants and reporting only the ones that pass is the same problem at the program level, even when every individual spec was honestly frozen.

| Dataset | Allowed use |
|---|---|
| Development | hypothesis formation, exploratory checks before a spec is written |
| Validation | the frozen spec's primary test — ACCEPT/REJECT/INCONCLUSIVE is decided on this |
| Final holdout | untouched until validation has already produced a decision; used once, for confirmation only |

A spec may only be re-run against the validation dataset while still DRAFT. Once FROZEN, a result — pass or fail — is final for that spec; a different outcome requires a new experiment ID or spec version. The final holdout is opened at most once per accepted strategy, only after it has already passed on the validation set; opening it earlier, or more than once, invalidates the confirmation.

Open design item, not yet operational — see [06 Trading System Audit](06-trading-system-audit-v1.md).

## The five questions

An experiment is accepted only if all answers are yes:

1. Is there an effect?
2. Is it larger than the control / base rate?
3. Does it survive the base cost scenario?
4. Is it stable across subperiods / out of sample?
5. Is it large enough to justify the capital, time and operational burden?

## Report template

`reports/experiments/EXP-xxx-<run_id>.md`

- Spec version, config hash, code commit, data snapshot IDs
- Sample: N events, N rejected by reason, coverage gaps
- Primary metric with confidence interval
- Secondary metrics
- Control comparison
- Cost scenarios
- Subperiod table
- Decision and rationale
