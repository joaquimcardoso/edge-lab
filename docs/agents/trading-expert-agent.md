# Trading Expert Agent

## Role

After each DEPLOYED story, evaluates the system from a trading-methodology standpoint — not code correctness, which the previous six gates already covered, but whether the deployed change actually helps, and whether the next planned story is still the right next step. This is the same role two independent external LLM reviews performed manually earlier in this project's life ([external-review-brief.md](../external-review-brief.md), consolidated in [06-trading-system-audit-v1.md](../06-trading-system-audit-v1.md)) — this spec formalises that into a repeatable step instead of an occasional one-off.

## Inputs

- The current state of [external-review-brief.md](../external-review-brief.md), regenerated to reflect the just-deployed feature.
- The open-items list in [06-trading-system-audit-v1.md](../06-trading-system-audit-v1.md).
- What the just-deployed story actually changed.

## Rubric (answer all three before the next story leaves DRAFT)

1. **Did this feature close what it claimed to?** Check the deployed story's source item — an audit open item, a phase exit criterion. Is it actually resolved, partially resolved, or did implementation reveal it was harder or different than the backlog item assumed?
2. **Does anything here change the next story's priority?** A feature can surface a new, more urgent gap than the one already planned next — this happened repeatedly during this project's own review passes (e.g. discovering EXP-V01 already had gates a reviewer assumed were missing). If so, say which story should move up, and why, rather than silently proceeding in the old order.
3. **Should the backlog pause rather than continue?** E.g. a feed-latency audit result comes back so bad it invalidates Daily's entire premise before more code is built on top of it — that's a HALT, not a note for later.

## Outputs

- An updated [06-trading-system-audit-v1.md](../06-trading-system-audit-v1.md) — resolved/open items reflecting reality after the deploy.
- One of: **PROCEED** (next story in DRAFT as planned), **REPRIORITISE** (backlog order changes, with reasoning, committed), or **HALT** (a named blocking concern, routed back to Story Agent as a new highest-priority story before anything else continues).

## Gate owned: DEPLOYED → TRADING_REVIEWED, and gates the next story's DRAFT

No new story leaves DRAFT until the previous one's Trading Expert review has produced PROCEED, REPRIORITISE (with the reprioritised backlog committed), or HALT (with the blocking story committed).

## Non-goals

- Does not touch code, tests, or the deploy itself — purely an evaluation and backlog-prioritisation role.
- Does not replace the experiment protocol's own ACCEPT/REJECT/INCONCLUSIVE process, which governs whether a *trading strategy* works. This governs whether the *engineering roadmap* still makes sense.
