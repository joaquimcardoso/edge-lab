# edge-lab

A point-in-time research lab that tests whether tradable edges exist in US equities, before any capital is committed.

The lab covers three independent strategies that share one data layer, one set of point-in-time rules and one experiment protocol:

| Strategy | Horizon | Question it asks |
|---|---|---|
| **Swing** | 5–20 trading days | Does a stock keep drifting after a material event, once the market has reacted? |
| **Daily** | Open → close, same session | Is the reaction to a pre-market event still incomplete at the open? |
| **Value** | 6–12 months | Does the market underprice reasonable companies that are cheap and ignored? |

The strategies never share optimised parameters and are never merged into a single score. Each one can be accepted or rejected on its own evidence.

## Status

**Phase 0 — Documentation.** No code, no data collection, no trading.

| Experiment | Strategy | Status |
|---|---|---|
| [EXP-001 Analyst drift](docs/experiments/swing/EXP-001-analyst-drift.md) | Swing | Draft |
| [EXP-002 Intraday continuation](docs/experiments/daily/EXP-002-intraday-continuation.md) | Daily | Draft (blocked by feed-latency gate) |
| [EXP-003 8-K drift](docs/experiments/swing/EXP-003-8k-drift.md) | Swing | Draft |
| [EXP-004 News events](docs/experiments/news/EXP-004-news-events.md) | Swing / Daily | Data collection only |
| [EXP-V01 Quality-value-insider](docs/experiments/value/EXP-V01-quality-value-insider.md) | Value | Draft |

## Core principles

1. **Evidence before capital.** A strategy trades real money only after it passes its frozen acceptance criteria out of sample and after costs.
2. **Point-in-time or nothing.** Every input carries the time at which *this system* could have known it. See [point-in-time rules](docs/01-point-in-time-rules.md).
3. **Freeze, then test.** Hypotheses, parameters and pass/fail criteria are committed to Git before results are seen.
4. **One change per experiment.** Refinements become new experiments, never silent edits.
5. **Rules decide; models structure.** LLMs and NLP may classify text into structured events. They never make trading decisions. See [ADR-0001](docs/adr/0001-no-llm-in-decision-path.md).
6. **No signal is a valid output.** `REJECT` and `INCONCLUSIVE` are successful experiment outcomes.
7. **Free data first.** Paid data is bought only when free data has produced a result worth confirming. See [ADR-0002](docs/adr/0002-free-data-first.md).

## Documentation map

| Document | Purpose |
|---|---|
| [00 Vision](docs/00-vision.md) | Goals, non-goals, roadmap |
| [01 Point-in-time rules](docs/01-point-in-time-rules.md) | Time fields, look-ahead rules, forbidden inputs |
| [02 Data sources](docs/02-data-sources.md) | What each source is trusted for, and its limits |
| [03 Architecture](docs/03-architecture.md) | Components, data model, decision log |
| [04 Infrastructure](docs/04-infrastructure.md) | Raspberry Pi 5 deployment, storage, scheduling, backups |
| [05 Experiment protocol](docs/05-experiment-protocol.md) | Lifecycle, metrics, statistics, reporting |
| [Strategies](docs/strategies/) | Swing, daily and value strategy definitions |
| [Experiments](docs/experiments/) | Individual hypothesis specifications |
| [ADRs](docs/adr/) | Architecture decision records |

## Non-goals

- Automatic order execution. The broker (XTB) offers no API; execution is manual. See [ADR-0005](docs/adr/0005-manual-execution-xtb.md).
- Competing on latency. The lab does not try to react to news within seconds or minutes.
- Predicting prices with an LLM.

## Disclaimer

Personal research project. Nothing in this repository is investment advice.
