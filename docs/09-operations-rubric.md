# 09 — Operations rubric: good day / bad day (Gate 0 phase)

## Scope

This rubric scores the **collection pipeline's operational health** for one calendar day (America/New_York). It says nothing about trading performance -- there is no strategy or paper-trading loop in this repository yet ([00-vision.md](00-vision.md#roadmap): this is Phase 1, Collection & audit). A "GOOD day" here means the pipeline behaved correctly; it is not a claim that any future strategy built on this data would be profitable.

This document and [src/edgelab/report/day_verdict.py](../src/edgelab/report/day_verdict.py) must never diverge -- the code is this table, mechanically applied.

## Inputs

Every rule below reads only [STORY-009](../stories/STORY-009-daily-ops-report.md)'s `DailyOpsReport` for the day being scored, plus whether that date was a scheduled NYSE trading day (STORY-005's `is_trading_day`, real calendar, not a hand-rolled weekday check).

## Rule (deterministic, no LLM, most severe wins)

| # | Condition | Verdict | Why this severity |
|---|---|---|---|
| 1 | Any raw-store integrity failure (a stored payload's sha256 no longer matches what was recorded at write time) | **BAD** | Evidence corruption is the single worst thing this system can discover about itself -- everything downstream depends on the raw store being trustworthy (ADR-0006). |
| 2 | Any Gate 0 (source, event type) combination reports `passed=False` **and** has at least `min_sample_for_gate0_verdict` (default 10) pre-market observations | **BAD** | A real, sample-backed feed-latency problem -- one or two slow events are noise; ten failing is a pattern. |
| 3 | Disk free ratio (free / total bytes on the filesystem holding the data directory) below `critical_disk_free_ratio` (default 10%) | **BAD** | An unattended 24/7 collector running out of disk silently stops writing evidence -- this must be caught before that happens, not after. |
| 4 | The day was a scheduled NYSE trading day and the collector recorded zero heartbeats | **BAD** | The collector never ran at all -- distinct from "ran and found nothing," which is a legitimate, non-alarming outcome. |
| 5 | (None of the above) but at least one collector failure was recorded today | **WARN** | Something went wrong on at least one run, but the collector did run overall and nothing above fired. |
| 6 | (None of the above) | **GOOD** | Routine day. |

A day can trigger more than one rule at once (e.g. low disk **and** an integrity failure) -- every rule that actually fired is recorded, not just the first or most severe, so a BAD verdict never hides that something else was also wrong.

## Gate 0 combination status (informational, not a verdict trigger on its own)

Each (source, event type) combination seen so far is separately labelled:

- **PASSING** -- meets Gate 0's real bar (share ≥ 80% seen before 09:30 ET, median lag ≤ 30s), with ≥ `min_sample_for_gate0_verdict` observations.
- **FAILING** -- fails that bar with ≥ `min_sample_for_gate0_verdict` observations (this is what feeds rule 2 above).
- **INSUFFICIENT_DATA** -- fewer than `min_sample_for_gate0_verdict` observations so far. This is the *expected* state for the first days of any campaign and never triggers BAD or WARN on its own -- only rule 2 (a real failure with enough samples) does.

## Who reads this

`score_day` runs on every daily-report invocation (cheap, deterministic, fine to run on the Pi itself -- no LLM required, consistent with [04-infrastructure.md](04-infrastructure.md)'s "no local LLM" constraint). The narrative, human-facing read of the resulting verdicts and reports is the [Ops Reviewer Agent](agents/ops-reviewer-agent.md)'s job, run wherever Claude already runs (a session, a scheduled task) -- matching [04-infrastructure.md](04-infrastructure.md)'s existing "Role of Claude Pro: scheduled weekly review of the reports in the repository" line, not something running unattended on the device.

## Explicit non-goals

- Not a trading-signal or paper-trading judgement -- see Scope above.
- Not an alerting mechanism -- this rubric produces a verdict in the written report; whether/how that reaches a human (email, push, a scheduled Claude session reading it) is a separate, not-yet-built concern.
- The specific thresholds (`min_sample_for_gate0_verdict=10`, `critical_disk_free_ratio=10%`) are defensible starting defaults, not empirically tuned -- revisit them once real Pi data exists.
