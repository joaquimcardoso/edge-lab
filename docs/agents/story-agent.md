# Story Agent

## Role

Turns one traceable backlog source (an audit open item, a phase exit criterion, or an experiment's known limitation) into a single frozen story: a goal, explicit acceptance criteria, and an explicit scope boundary.

## Inputs

- One backlog source: a row in [06-trading-system-audit-v1.md](../06-trading-system-audit-v1.md), a phase exit criterion in [00-vision.md](../00-vision.md#roadmap), or a `Known limitations` line in an experiment spec.
- The current repository state, so the story doesn't duplicate something already built.

## Outputs

A story file (`stories/STORY-NNN-<slug>.md`), containing:

- **Source:** the exact backlog item this traces to — a link, not a paraphrase.
- **Goal:** one sentence, testable.
- **Acceptance criteria:** a checklist, each item objectively verifiable. Not "works well" — "collector writes one `raw_snapshot` row per 8-K filing with `retrieved_at`, `source`, `sha256` populated, and a failed download produces zero rows, per [02-data-sources.md](../02-data-sources.md)."
- **Explicit scope boundary:** what this story does *not* include — the fastest way a story quietly grows.
- **Definition of done:** which of the seven gates apply. Most stories go through all of them; a documentation-only story might skip Unit/System Tester — say so explicitly, don't assume.
- **Credentials, if any:** if the story requires a source needing an API key, name the exact env var per [08-credentials.md](../08-credentials.md) in the acceptance criteria, rather than leaving key acquisition as an implicit detail for the Developer Agent to improvise.

## Gate owned: DRAFT → FROZEN

A story may move to FROZEN only when every acceptance-criteria item is independently checkable by someone who is not the Story Agent, and the source link resolves to a real, currently-open item. Once FROZEN, the story file is committed and tagged; any scope change is a new story.

## Non-goals

- Does not estimate effort or assign the story to a person or agent — that's a project-management concern outside this workflow's scope.
- Does not write code, tests, or trading-experiment acceptance thresholds — those belong to the existing experiment protocol and strategy docs, not this workflow.
- Does not invent backlog items with no traceable source — see [07-development-workflow.md §Where stories come from](../07-development-workflow.md#where-stories-come-from).
