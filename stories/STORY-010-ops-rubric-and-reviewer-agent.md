# STORY-010 — Good day / bad day operations rubric and Ops Reviewer Agent

| Field | Value |
|---|---|
| Status | TRADING_REVIEWED |
| Owner stage | Story Agent |

## Source

The user's explicit request: "what will be a good day or a bad day? who is looking into it, I need a agent to review all of that." Depends on [STORY-009](STORY-009-daily-ops-report.md)'s report artifact. [04-infrastructure.md](../docs/04-infrastructure.md)'s schedule already names the job this story's entrypoint fills in: "Daily report + commit" at 17:00 ET, and separately states the actual judgement role: "Role of Claude Pro: ... Scheduled weekly review of the reports in the repository." Consistent with that existing plan, this story keeps the objective day-scoring deterministic (no LLM on the Pi -- [04-infrastructure.md](../docs/04-infrastructure.md): "No local LLM (4 GB is insufficient for useful quality)") and defines the Ops Reviewer Agent as the human-facing role that reads already-scored artifacts, not something that runs unattended on the device itself.

## Goal

An objective, mechanical (no LLM) day-scoring rule applied to STORY-009's report, plus the entrypoint and systemd wiring to run it daily, plus a new agent role whose job is reading the resulting verdicts and reports and deciding whether the user's attention is needed. This story explicitly does **not** claim to judge trading performance -- there is no strategy or paper-trading loop yet (docs/00-vision.md's roadmap: this is Phase 1, collection & audit). "Good day / bad day" here means operational health of the collection pipeline during the Gate 0 campaign, nothing else.

## Acceptance criteria

- [ ] `DailyOpsReport` (STORY-009) gains three fields needed to score a day that the report didn't previously carry: `collector_runs_today` (a count, from a new append-only heartbeat log -- distinguishes "the collector ran and found nothing" from "the collector never ran," which `snapshots_today_by_source == {}` alone cannot tell apart), `disk_total_bytes`, `disk_free_bytes` (via `shutil.disk_usage` on `data_dir`'s filesystem). `scripts/collect_premarket_8k.py` gains `append_heartbeat(log_dir, *, now)`, called once per `main()` invocation regardless of outcome, writing to `<log_dir>/run_heartbeats.jsonl` -- same append-only pattern as `append_failure_log`.
- [ ] `docs/09-operations-rubric.md` states the rule in plain language and a table, matching exactly what `day_verdict.py` implements (never two divergent descriptions of the same rule).
- [ ] `src/edgelab/report/day_verdict.py`'s `score_day(report, *, is_scheduled_collection_day, min_sample_for_gate0_verdict=10, critical_disk_free_ratio=0.10) -> DayVerdict` applies, in this order (most severe wins, first match returns):
  1. **BAD** -- any raw-store integrity failure (`report.integrity_failures`). Data corruption is the single most severe signal this system can detect about itself.
  2. **BAD** -- any Gate 0 (source, event_type) combination with `passed=False` **and** `total_premarket_events >= min_sample_for_gate0_verdict` (a real, sample-backed feed problem, not noise from one or two events).
  3. **BAD** -- disk free ratio (`disk_free_bytes / disk_total_bytes`, when known) below `critical_disk_free_ratio`.
  4. **BAD** -- `is_scheduled_collection_day` is true and `collector_runs_today == 0` (the collector never ran at all on a day it was scheduled to).
  5. **WARN** -- `failures_today` is non-empty (some runs failed, but the collector did run and nothing above fired).
  6. **GOOD** -- none of the above.
  Every trigger that actually fired is recorded in `DayVerdict.reasons`, not just the first/most severe one, so a report showing only "BAD" never hides that three separate things were also wrong.
- [ ] `Gate0Progress` (built alongside the verdict, from `report.latency_stats`/`report.latency_gaps`) summarises, per (source, event_type): PASSING / FAILING / INSUFFICIENT_DATA -- INSUFFICIENT_DATA is informational context, never itself a verdict trigger, since it is the expected state for the first days of any campaign.
- [ ] `scripts/build_daily_report.py`: entrypoint composing STORY-009's `build_daily_ops_report` + `render_daily_report` + `score_day`, writing the report (as STORY-009 already does) plus a verdict section appended to the same Markdown/JSON -- one artifact, not two files that can drift apart. `is_scheduled_collection_day` is computed from the real NYSE calendar (STORY-005's `is_trading_day`) for the report's own date, reusing it rather than a second hand-rolled weekday check.
- [ ] `deploy/edgelab-daily-report.service` + `.timer`: systemd units for the 17:00 ET "Daily report" job (`04-infrastructure.md`'s schedule), same `RequiresMountsFor`/`EnvironmentFile` pattern as STORY-008's units. The "+ commit" half of that job's name is explicitly **not** built here -- committing the Pi's own generated reports back to git needs its own deploy-key/push story, out of scope, and is named as an open item rather than silently included or silently dropped.
- [ ] `docs/agents/ops-reviewer-agent.md` + `.claude/agents/ops-reviewer.md`: a new agent role that reads a day's (or a week's) already-written reports and verdicts and produces a short narrative decision-log entry -- "routine, no action" for GOOD days, a named concern for WARN, and an explicit flag for BAD -- explicitly consistent with `04-infrastructure.md`'s existing "Role of Claude Pro: scheduled weekly review" line, i.e. this role runs wherever Claude already runs (this session, a scheduled task), never as unattended code on the 4 GB Pi itself. Non-goals stated plainly: does not decide trading-strategy acceptance (Trading Expert Agent's job), does not touch code, does not override `score_day`'s deterministic verdict -- it narrates and contextualises it.
- [ ] Unit tests: each of the four BAD triggers independently (proving each alone is sufficient, matching STORY-007's "each bar independently required" testing pattern), WARN, GOOD, and that `reasons` accumulates every trigger that actually fired rather than stopping at the first. `append_heartbeat`'s format and append behaviour.
- [ ] System test: `build_daily_report.py`'s composition over a real report built from real stores, asserting the written artifact contains both the report sections and a verdict section that agree with directly calling `score_day` on the same report.

## Explicit scope boundary

- No LLM, no subjective judgement anywhere in `score_day` -- purely mechanical, consistent with ADR-0001's spirit even though this isn't a trading decision.
- Does not judge trading performance, P&L, or strategy acceptance -- there is none yet (Phase 1). A "GOOD day" here means the collection pipeline behaved correctly, nothing about whether any future strategy built on this data would be profitable.
- Does not implement the "+ commit" half of the 17:00 ET job, or any alerting/notification mechanism (email, push) -- both named as open items for a future story, not silently built or silently dropped.
- The Ops Reviewer Agent's spec is written and ready to invoke; this story does not set up a live recurring scheduled task to run it automatically, since there is no real collection data yet for it to review (the Pi hasn't been installed on) -- doing so now would be reviewing an empty store. Setting that up is the natural next step once `deploy/install.sh` has actually run on the device.

## Definition of done

All seven gates apply.

## Credentials, if any

None beyond what STORY-008/009 already require.
