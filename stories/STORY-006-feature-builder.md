# STORY-006 — Point-in-time feature builder (ATR%, ADV, beta)

| Field | Value |
|---|---|
| Status | TRADING_REVIEWED |
| Owner stage | Story Agent |

## Source

[07-development-workflow.md §Suggested MVP story sequence, item 6](../docs/07-development-workflow.md#suggested-mvp-story-sequence-phase-1): "Feature builder: ATR%, beta, ADV — point-in-time only, per §5." Formulas are not new — they are already frozen in experiment specs and must be matched exactly, not reinvented: `ADV20` ([strategies/swing.md](../docs/strategies/swing.md), [EXP-001](../docs/experiments/swing/EXP-001-analyst-drift.md): average **dollar** volume, 20-session trailing window), `ATRpct20 = ATR20(t−1) / close(t−1)` using **Wilder's** ATR specifically ([EXP-002](../docs/experiments/daily/EXP-002-intraday-continuation.md)), and the zero-alpha beta model (`AR = R_stock − β·R_market`, no intercept, 252-day window, minimum 60 observations — [01-point-in-time-rules.md §5](../docs/01-point-in-time-rules.md), [05-experiment-protocol.md](../docs/05-experiment-protocol.md)).

## Goal

A small, pure feature-math module (no I/O) implementing Wilder ATR / ATR%, rolling average dollar volume, and zero-intercept beta exactly per their already-frozen definitions — plus a thin orchestrator that reads `price_daily` rows (STORY-004) strictly **before** a given `as_of_date` (never including it), so "point-in-time only" is a property of the function's contract, not something every caller has to remember to enforce.

## Acceptance criteria

- [ ] `true_range(high, low, prev_close)` implements the standard formula: `max(high−low, |high−prev_close|, |low−prev_close|)`.
- [ ] `wilder_atr(highs, lows, closes, window=20)` implements **Wilder's** smoothing specifically (not a simple/arithmetic rolling mean of True Range): the first value is the simple average of the first `window` True Ranges; every subsequent value is `(previous_ATR × (window−1) + TR_t) / window`. Values before `window` True Ranges are available are `None`.
- [ ] `atr_pct(atr_values, closes)` returns `atr / close` element-wise, `None` where either input is `None`.
- [ ] `average_dollar_volume(closes, volumes, window=20)` returns the trailing `window`-session mean of `close × volume`, `None` until `window` observations exist.
- [ ] `zero_intercept_beta(stock_returns, market_returns, window=252, min_observations=60)` computes `β = Σ(R_market × R_stock) / Σ(R_market²)` over the trailing window (**not** `cov/var`, which assumes an intercept the model doesn't have) — [05-experiment-protocol.md](../docs/05-experiment-protocol.md)'s own formula. Returns `None` if fewer than `min_observations` paired returns are available in the window.
- [ ] `build_features_as_of(security_id, market_security_id, as_of_date, ...)` reads `price_daily` rows with `date < as_of_date` **only** (never `date >= as_of_date`, even for read access — not just excluded from the final number) for both the security and the market benchmark, and returns `ATR20`, `ATRpct20`, `ADV20` and `beta252` computed from that data. Enforcing the cutoff at the read, not just the computation, is what makes "point-in-time only" a property the caller cannot accidentally violate by passing extra rows. Stock and market returns feeding `beta252` are paired by actual trading **date**, not by trailing list position — caught during review: truncating both return series to the same length from the end silently misaligns the pairs whenever one series has a gap the other doesn't (a missing bar, a temporary delisting).
- [ ] Unit tests cover: `true_range` against hand-computed examples including a gap (where `|high−prev_close|` or `|low−prev_close|` exceeds `high−low`); Wilder ATR against a hand-computed short series (verifying the smoothing formula, not just "some average"); `average_dollar_volume` against a hand-computed series; `zero_intercept_beta` against a synthetic series with a known, hand-derived beta, and returning `None` below `min_observations`; `build_features_as_of` never reading a `price_daily` row on or after `as_of_date` even when one exists in the store (a same-day row present in the fixture, deliberately, to prove the cutoff holds under temptation).
- [ ] System test: `build_features_as_of` run against real `price_daily` rows written through STORY-004's actual store, for both a security and a market benchmark, verifying the returned values are computed only from the correct point-in-time slice.

## Explicit scope boundary

- **No sector-relative or fundamentals-keyed features** — [01-point-in-time-rules.md §5](../docs/01-point-in-time-rules.md)'s sector-history and fundamentals rules need a `sector_history` table and an XBRL collector that don't exist yet. Only the three features this story's source item names (ATR%, ADV, beta) are built.
- **The market benchmark series is supplied by the caller, not auto-selected or auto-fetched.** `build_features_as_of` takes `market_security_id` as a parameter; it does not decide "SPY" for you, and does not collect benchmark prices itself — that's STORY-004's collector, run once per benchmark ticker like any other security.
- No caching or precomputed feature table — every call recomputes from `price_daily` directly. A materialised feature store is future work if recomputation cost ever matters.
- `ATR20`/`ADV20` window is fixed at 20 to match the already-frozen `ATR20`/`ADV20` naming used throughout the experiment specs; the beta window is fixed at 252 (min 60) per [01-point-in-time-rules.md §5](../docs/01-point-in-time-rules.md)'s proposed default. Neither is re-derived or made a free parameter of an experiment — they are data-layer conventions, not something a spec should be able to silently drift by passing a different number.

## Definition of done

All seven gates apply. System Tester's "re-run every FROZEN experiment" clause remains vacuous — no experiment is FROZEN yet (its own spec being frozen is different from an experiment *run* being frozen and accepted).

## Credentials, if any

None. Pure computation plus reads from the local price store.
