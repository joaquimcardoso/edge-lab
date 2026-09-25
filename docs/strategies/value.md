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

## Live-phase considerations

- With ~€1,000 of capital and 6–12 month holding periods, only a handful of value positions can be held at once; tranche scaling is limited by broker minimum ticket sizes, not by the three-tranche ideal that applies to larger accounts.
- Sector concentration across the value basket is governed by the account-level limits in [00 Vision](../00-vision.md#account-level-risk-limits-phase-5).
- Value's capital turns over far more slowly than swing or daily; if all three strategies are live at once, value's share of the €1,000 should be earmarked under the capital-allocation decision in [00 Vision](../00-vision.md#capital-allocation-across-strategies), not left to compete trade-by-trade for whatever cash is free.

## Experiments

- [EXP-V01 Quality-value-insider](../experiments/value/EXP-V01-quality-value-insider.md)
