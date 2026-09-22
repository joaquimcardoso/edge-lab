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
