# Regression tests

Empty until the first experiment reaches `FROZEN`
(docs/05-experiment-protocol.md). This is where the Integrator
Agent's "0 regressions" gate lives mechanically
(docs/07-development-workflow.md, "Definition of '0 regressions'"):
one fixture per FROZEN experiment, recording its `data_snapshot_ids`
and `config_hash`; a test here re-runs that experiment against the
recorded snapshots and diffs the result against the last-accepted
`observation` row. Any unexplained diff fails the build and blocks
integration.

Not populated by STORY-001 — there is no FROZEN experiment yet, so
this gate is vacuous for that story (see
tests/system/test_raw_snapshot.py::test_regression_fixture_set_is_vacuous_pre_first_experiment),
not skipped.
