# 00 — Vision

## Problem

Most retail trading systems are built backwards: a striking move (for example, a large-cap stock rising 11% in one session) inspires a rule, the rule is tuned until it would have caught that move, and the result is mistaken for an edge. Hindsight, look-ahead bias and survivorship bias make almost any idea look profitable on paper.

## Goal

Build a small, reproducible research lab that answers one question per experiment:

> Given only what was knowable at decision time, does this signal produce a positive excess return after realistic costs, out of sample, and large enough to justify the capital and effort?

The lab covers three strategies with different horizons, data and risk profiles. They share infrastructure, not parameters.

## What "success" means

- A strategy is **accepted** when it passes the frozen criteria in its experiment specification.
- A strategy is **rejected** when it fails them. This is a successful outcome: it prevents losing money on a non-edge.
- An experiment is **inconclusive** when the sample is too small or results are unstable. The response is more data or a narrower question, not looser criteria.

## Principles

1. **Evidence before capital.**
2. **Point-in-time or nothing.** The system records when it *could* have known each fact, not only when the fact happened.
3. **Freeze, then test.** Specs are committed before results exist. Git history is the proof.
4. **One change per experiment.**
5. **Rules decide; models structure.**
6. **No signal is a valid output.**
7. **Free data first; pay to confirm, not to explore.**
8. **Reproducibility.** Every result can be regenerated from immutable raw snapshots, a config hash and a code version.

## Non-goals

- Automatic execution.
- Sub-minute latency.
- Maximising backtest returns.
- One unified "super score" across strategies.
- Tax optimisation. Portuguese tax treatment affects net returns and must be considered before live trading, but it is outside the scope of the research code.

## Roadmap

| Phase | Content | Exit criterion |
|---|---|---|
| **0 — Documentation** | Principles, rules, specs, ADRs | Specs reviewed and committed |
| **1 — Collection & audit** | Collectors on the Pi, raw snapshots, data audit, feed-latency measurement | Audit report: reconstructable-event rate and failure profile |
| **2 — Historical tests** | EXP-001F, EXP-003, EXP-V01 on free historical data | Each experiment reaches ACCEPT / REJECT / INCONCLUSIVE |
| **3 — Forward paper trading** | Live signals, paper log, no capital | Forward sample reaches the spec's minimum size |
| **4 — Paid data decision** | Buy vendor data only if Phase 2/3 show a result worth confirming | Written decision (ADR) |
| **5 — Small live capital** | Manual execution, strict risk limits | Live results consistent with paper results |

## Initial capital context

The initial live allocation is small (order of €1,000). Position sizing, costs per trade and minimum ticket sizes must be evaluated against this amount, not against the round numbers used in examples.

### Capital allocation across strategies

Strategies never share parameters or a combined score (principle 5, [ADR-0007](adr/0007-independent-strategies.md)), but Phase 5 implies they may compete for the same €1,000 pool if more than one is live at once. Before any strategy enters Phase 5, this repository must record — as a frozen decision, per principle 3 — either an explicit split of the capital across the strategies live at that time, or an order in which strategies go live one at a time. Otherwise the allocation gets decided implicitly, trade by trade, which is exactly the kind of undocumented parameter the rest of this lab avoids.

### Account-level risk limits (Phase 5)

"Strict risk limits" (Roadmap, Phase 5) is not yet defined anywhere in this repository. At minimum it must specify:

- A maximum drawdown on live capital at which all strategies stop opening new positions until reviewed — a number to be frozen before Phase 5, not decided ad hoc during a drawdown.
- A cap on how many positions across all three strategies can be open at once, sized to what €1,000 can actually diversify.
- A cap on how many of those open positions may share a sector or an event date, so one sector shock or news day cannot hit the whole account at once.

These limits should be frozen the same way an experiment spec is frozen — committed before Phase 5 starts, not adjusted after seeing live results. The strategy docs ([swing](strategies/swing.md), [daily](strategies/daily.md), [value](strategies/value.md)) reference this section rather than each inventing its own number.

**Proposed defaults (not yet frozen — require an explicit decision before Phase 5):**

- **Sequencing over sharing.** Do not split €1,000 three ways on day one. Deploy it to one accepted strategy first; add a second only once the first has a live track record. Swing is the natural first strategy — it tolerates manual-execution latency better than Daily, and matures faster than Value.
- **Drawdown circuit breaker:** 15% of live capital (≈€150 on €1,000). At that point, all strategies stop opening new positions until a manual code-and-execution audit is done — not just a review of whether the thesis was right.
- **Concurrent positions:** cap at 5 account-wide while capital is this small: more than that and per-position sizing falls below what a 1% risk budget can meaningfully express once broker minimum ticket sizes and fractional-share limits are accounted for.
- **Minimum viable risk per trade:** before sizing any live trade, check that the risk budget implied by the account size and per-trade risk % is at least the broker's minimum ticket size at the stop distance required — otherwise the position is either skipped or the risk % for that trade is documented as an exception, not silently rounded up.
