# STORY-007 — Feed-latency audit harness (Gate 0)

| Field | Value |
|---|---|
| Status | FROZEN |
| Owner stage | Story Agent |

## Source

[07-development-workflow.md §Suggested MVP story sequence, item 7](../docs/07-development-workflow.md#suggested-mvp-story-sequence-phase-1): "Feed-latency audit harness (Gate 0 for [EXP-002](../docs/experiments/daily/EXP-002-intraday-continuation.md))." Gate 0's own text, verbatim: "poll each event source every few minutes from 08:00 ET and record `first_seen_at`. Report, per source, the distribution of `first_seen_at − published_at` and the share of pre-market events visible before 09:30 ET." Pass bar: **≥80%** of pre-market events seen before 09:30 ET **and** median lag **≤30s**; a source failing either bar is "not used live."

## Goal

An analysis harness that reads already-collected events (their `published_at`/`first_seen_at`, populated by STORY-003's normaliser) for a source and event type, computes the pre-market-visibility share and the full lag distribution (not just its median — [01-point-in-time-rules.md §2](../docs/01-point-in-time-rules.md): "The audit stores the full distribution, not one summary number"), applies Gate 0's exact pass bar, and renders a Markdown report. This does **not** run the 2–3 week live polling campaign itself — that is an operational/scheduling activity on the Pi ([04-infrastructure.md](../docs/04-infrastructure.md)); this story is the analysis that campaign's collected data feeds into, same "collector runs the schedule, this repository analyses the result" split as every other story.

## Acceptance criteria

- [ ] `is_premarket_event(published_at)` is true only for a `published_at` whose `America/New_York` time falls before 09:30 ET **on a genuine NYSE trading day** — reusing [STORY-005](STORY-005-exchange-calendar.md)'s calendar, not a second hand-rolled check.
- [ ] `lag_seconds(published_at, first_seen_at)` returns `first_seen_at − published_at` in seconds.
- [ ] `compute_latency_stats(events, source, event_type=None)` filters to pre-market events for that source (and event type, if given), and returns the **share** seen before 09:30 ET plus the **p50/p90/p95** of the lag distribution — never only a median, so a source with a fast median but a slow tail is visible, not hidden. "Seen before 09:30 ET" specifically means before 09:30 ET **on the same calendar day as `published_at`** — caught during review: naively reapplying the pre-market check to `first_seen_at` on its own would wrongly count a filing missed all of Monday and only picked up at, say, 06:00 ET Tuesday as "seen before open," since that check alone only asks whether 06:00 is before *that* day's 09:30, not whether the day is even the right one.
- [ ] The Gate 0 pass bar (`share ≥ 0.80` **and** `p50 ≤ 30` seconds) is applied exactly, both conditions required — a source passing only one bar still fails.
- [ ] Zero matching pre-market events raises `FeedLatencyAuditError` rather than computing statistics on nothing, or silently reporting a false PASS/FAIL.
- [ ] `render_report(stats_list)` produces a Markdown table — per source/event-type: sample size, share before open, p50/p90/p95 lag, PASS/FAIL — matching this repository's existing Markdown-report convention ([03-architecture.md §Components](../docs/03-architecture.md#components): "Reporter... Markdown reports").
- [ ] Unit tests cover: `is_premarket_event` for a genuine pre-market weekday time, an intraday/post-close time, and a weekend timestamp (all correctly excluded/handled); the percentile calculation against a hand-computed series; the pass bar applied correctly to a passing case, a failing-on-share case, and a failing-on-lag case (each independently, proving both conditions are actually required); zero events raising rather than fabricating a result.
- [ ] System test: events written through STORY-003's real normaliser/event store, then audited end-to-end, producing a correct pass/fail verdict and a non-empty rendered report.

## Explicit scope boundary

- Does not run or schedule the live polling campaign Gate 0 describes — analysis only, over events already in the store.
- No numeric minimum-sample floor is invented for this story (unlike EXP-002's own frozen "150 observations" for the full experiment) — Gate 0's own text specifies no such number, and one is not fabricated here. The report states the raw sample size plainly; judging whether it's enough is left to the person reading the report, consistent with Gate 0 being a human-reviewed audit, not an auto-pass/fail pipeline gate.
- Covers 8-K-sourced events only, since that is the only normaliser this repository has (STORY-003). Analyst-action and RSS/wire sources (also named in Gate 0's own event list) get their own audit input once their collectors/normalisers exist — this harness's logic does not change, only which events are fed into it.

## Definition of done

All seven gates apply. System Tester's "re-run every FROZEN experiment" clause remains vacuous — no experiment is FROZEN yet (EXP-002 itself is explicitly blocked on this very gate, per its own "Status: DRAFT — blocked by Gate 0").

## Credentials, if any

None. Pure analysis over locally stored data.
