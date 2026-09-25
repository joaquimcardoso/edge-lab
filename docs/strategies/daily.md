# Strategy — Daily

## Definition

Positions opened at the regular-session open and closed at the same session's close, after an event known **before** the open. No overnight exposure.

## Hypothesis family

Intraday continuation: the reaction to pre-market information may be incomplete at the open. The opposite (intraday reversal after gaps) is also documented, so neither direction is assumed.

## Gates before any backtest result matters

1. **Feed-latency gate.** Measure, over live pre-market sessions, the delay between `published_at` and `first_seen_at` for each event source. If most pre-market events become visible after 09:30 ET, the strategy is not executable with that source, whatever the backtest says.
2. **Execution-realism gate.** The strategy must survive the stress cost scenario (pessimistic open slippage).

## Common rules

| Item | Rule |
|---|---|
| Universe | Same as swing |
| Event timing | `known_at` < 09:30 ET |
| Inputs allowed | Previous close, t-1 features, event, today's open. **No** same-day volume, high, low or close. |
| Entry / exit | Open → close |
| Benchmark | Same-session SPY and sector ETF open-to-close |

## Operational constraints

- The US open is typically 14:30 in Lisbon, during working hours.
- Execution is manual (no broker API).
- The expected return per trade is smaller than in swing, so costs weigh proportionally more.

These constraints make the acceptance bar for daily higher than for swing.

## Live-phase considerations

- Because positions are closed the same session, there is no overnight gap risk to size for (unlike swing); risk per trade is bounded by the invalidation level used at entry.
- Daily and swing can hold positions on the same day and draw on the same €1,000; concurrent exposure across strategies is governed by the account-level limits in [00 Vision](../00-vision.md#account-level-risk-limits-phase-5), not sized independently per strategy.
- Execution is manual, at the US open (typically 14:30 Lisbon).

## Experiments

- [EXP-002 Intraday continuation](../experiments/daily/EXP-002-intraday-continuation.md)
- EXP-002B Execution model with minute bars (only if EXP-002 is accepted)
