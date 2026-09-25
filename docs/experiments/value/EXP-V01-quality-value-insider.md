# EXP-V01 — Quality-value-insider

| Field | Value |
|---|---|
| Strategy | Value |
| Status | DRAFT |
| Spec version | 0.1.0 |

## Hypothesis

- **H1:** Companies of acceptable quality that are cheap relative to their sector and show recent insider buying outperform their sector over the following 12 months.
- **H0:** No positive sector-adjusted return after costs.

## Formation (monthly, point-in-time)

Using only fundamentals with `filed` ≤ formation date:

**Universe:** US common stocks, market cap ≥ $300M, ADV20 ≥ $2M, price ≥ $5. Financials and REITs excluded (different accounting).

**Quality (all required):**
- Operating cash flow positive in each of the last 3 fiscal years
- Net debt / EBITDA ≤ 3.0 (or net cash)
- No net share issuance > 5% over the last 12 months

**Value:** FCF yield (TTM FCF / market cap) in the top quintile of its sector.

**Insider:** at least one open-market purchase (Form 4 code `P`) by an officer or director in the last 90 days, net of sales, excluding purchases flagged under a Rule 10b5-1 trading plan (Form 4's 10b5-1 checkbox, in effect for filings from February 2023 onward; earlier filings cannot be determined and are included as-is). A pre-scheduled 10b5-1 purchase is not a discretionary signal of conviction the way an open-market buy is.

## Portfolio

Equal weight, held 12 months, one cohort per month (overlapping cohorts, calendar-time portfolio).

## Metrics

- **Primary:** 12-month sector-adjusted return of the calendar-time portfolio
- Secondary: market-adjusted return, drawdown, hit rate, turnover, value-trap rate (share of holdings breaching a quality rule during the holding)

## Controls

1. Quality + value **without** insider buying
2. Value **without** quality filters (measures the trap-avoidance effect)

## Minimum sample (proposed, to confirm before freezing)

At least 24 monthly cohorts (2 years) with at least 20 qualifying holdings per average cohort, spanning at least 2 distinct market regimes. Below that, the result is reported INCONCLUSIVE per [00 Vision](../../00-vision.md), not REJECT — 12-month holds mature slowly, so this is the strategy most likely to be starved of sample size rather than genuinely disproven.

## Acceptance criteria (to freeze)

- Primary positive with CI excluding 0
- Better than both controls
- Not dependent on a single sub-period (e.g. positive in at least two distinct market regimes)

## Known limitations

- XBRL tags vary across companies; the tag-mapping table is versioned and audited.
- Sector classification history must be point-in-time.
- Each observation takes 12 months; the sample grows slowly.

## Outcome

_Pending._
