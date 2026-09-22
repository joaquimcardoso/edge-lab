# Strategy — Value

## Definition

Long positions held 6–12 months in reasonable-quality companies whose price is well below a conservative valuation and that receive little market attention.

## Cheap is not undervalued

The strategy must separate value candidates from value traps:

| Value candidate | Value trap signals |
|---|---|
| Positive and stable operating cash flow | Falling revenue and margins |
| Manageable debt | High leverage, refinancing risk |
| Stable or improving returns on capital | Structurally declining industry |
| Insider buying | Insider selling, dilution |

## Data

- Fundamentals: SEC XBRL, keyed by filing date.
- Insider activity: Form 4 (open-market purchases, transaction code `P`).
- Prices: daily.

## Common rules

| Item | Rule |
|---|---|
| Universe | US common stocks, market cap and liquidity floors defined per experiment |
| Portfolio | Equal-weight basket, rebalanced on a fixed schedule |
| Benchmark | Sector-adjusted and market-adjusted returns |
| Invalidation | By thesis (e.g. cash flow turns negative, leverage breaches limit), not by tight price stops |

## Evaluation realities

- Re-ratings are slow; each observation takes 6–12 months to mature.
- Value has had long periods of underperformance. Subperiod analysis is essential.
- Forward testing alone would take years; historical tests on point-in-time XBRL data carry most of the evidence.

## Experiments

- [EXP-V01 Quality-value-insider](../experiments/value/EXP-V01-quality-value-insider.md)
