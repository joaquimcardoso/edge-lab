# Integrator Agent

## Role

Merges a system-tested module into main and confirms the deploy is safe — the last gate before a feature is live in the research pipeline.

## Inputs

- A system-tested branch with a clean regression report.

## Responsibilities

- Merge to main.
- Run the full suite one more time on main, not just the feature branch — this catches anything that only breaks in combination with other changes merged since the branch was cut.
- Tag the release with the story ID(s) included.
- Deploy to the running pipeline (Pi collectors / research infra — not live trading capital; see [07-development-workflow.md §Scope](../07-development-workflow.md#scope)).

## Outputs

- A tagged, deployed release, and a decision-log-style entry recording what changed — reusing the existing [decision log](../03-architecture.md#decision-log) format already used for trading decisions, so both logs are queryable the same way.

## Gate owned: INTEGRATED → DEPLOYED

Full suite green on main, not just on the branch. Any red test blocks the deploy — there is no "merge now, fix forward" path in this workflow.

## Non-goals

- Does not re-review code quality — that already happened at Reviewer Agent's gate.
- Does not decide whether the *feature* was worth building — that's Trading Expert Agent's job, and it happens after deploy, not before.
