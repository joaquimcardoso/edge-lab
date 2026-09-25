# Notification Agent

## Status

**Not yet activated** for trading signals (none exist). Activated for operational status once [STORY-013](../../stories/STORY-013-telegram-ops-notification.md) lands -- daily Gate 0 / collection-health verdicts only, not trading signals.

## Role

Owns Telegram as a notification sink -- never part of strategy or decision logic. Turns already-structured data (a `Signal`, once one is real; a `DayVerdict`, already real per STORY-010) into a formatted message and sends it. The mission document's own principle: "A signal should produce a structured event. Then a Telegram adapter can turn it into a message."

## Inputs

- A structured event to notify about: today, [DayVerdict](../../src/edgelab/report/day_verdict.py) / [DailyOpsReport](../../src/edgelab/report/daily_report.py); in the future, [Signal](../../src/edgelab/signals/signal.py).
- Telegram credentials via the existing `EDGELAB_*` convention ([08-credentials.md](../08-credentials.md)).

## Responsibilities

- Every trading-relevant number in a message (entry, stop, target) comes only from the structured object that produced it -- never from free-form generation, matching the mission document's "never construct important trading parameters using free-form LLM output."
- An LLM may eventually help phrase an explanation of *why* a signal fired, but never originates the entry/stop/target/direction fields themselves ([ADR-0001](../adr/0001-no-llm-in-decision-path.md)'s decision/explanation split).
- Message formatting is a pure function, tested without requiring real Telegram credentials -- a fake/recording sender in tests, same pattern as every fake `HttpClient` already in this repository.
- Sends are idempotent per notified event -- re-running a report generation must not re-send an already-sent notification for the same day/signal.

## Outputs

- A message formatter and a sender client, with unit tests covering formatting (no live network) and a system test using a recording fake sender.

## Non-goals

- Never originates trading parameters -- only formats what a `Signal` or report already decided.
- Does not decide whether to notify -- that's the calling code's job (e.g. STORY-010's `score_day`, or a future risk-check layer for signals); this agent only turns an already-made decision into a message.
- Not wired to send real trading signals yet -- none exist to send.
