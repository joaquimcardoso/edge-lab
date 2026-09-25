# STORY-008 — Pi collector entrypoint and deploy scaffold (Gate 0 scope)

| Field | Value |
|---|---|
| Status | TRADING_REVIEWED |
| Owner stage | Story Agent |

## Source

[07-development-workflow.md's Orchestrator Agent "Known limitation: deployment target"](../docs/07-development-workflow.md): "actually rolling it onto the Pi remains a manual step, **or a future story that automates it** (e.g. over SSH)." [04-infrastructure.md](../docs/04-infrastructure.md)'s scheduling table names the two Gate 0-relevant jobs this story must produce a runnable, installable form of: "Pre-market snapshot" and "EDGAR 8-K / Form 4 polling... every 15 min, 08:00 ET-16:30 ET." Also traces to the user's explicit request for "an agent responsible to orchestrate system in rpi... create services if needed, create cronjobs."

## Goal

Everything needed to actually run the existing STORY-002/003 collector + normaliser on a schedule and get real, on-disk artifacts -- a runnable entrypoint script, a typed env-var config loader, a real (non-fake) `HttpClient`, an initial universe list, and installable systemd unit + timer files -- **scoped to 8-K collection only**, matching STORY-007's own scope boundary ("Covers 8-K-sourced events only"). This story does not add Finnhub, RSS, GDELT, Form 4, or price collection to the schedule; those get their own stories once their collectors exist.

## Acceptance criteria

- [ ] `src/edgelab/config.py`'s `load_collector_config()` reads `EDGELAB_SEC_USER_AGENT` and `EDGELAB_DATA_DIR` from the environment (dependency-injectable, not hardcoded `os.environ` -- testable without real env vars) and raises `ConfigError`, naming the exact missing variable and pointing at `docs/08-credentials.md`, if either is unset or blank. Never silently defaults a User-Agent (violates SEC fair-access policy) or a data directory (risk of writing to the wrong disk, per this project's own no-silent-default precedent in STORY-004's `PricesDailyError` fix).
- [ ] DB paths (`raw_snapshot.db`, `event.db`) and a reports directory are derived under `EDGELAB_DATA_DIR` by default, each individually overridable via its own `EDGELAB_*_DB_PATH` / `EDGELAB_REPORTS_DIR` variable.
- [ ] `src/edgelab/net/requests_http_client.py` provides `RequestsHttpClient`, a real implementation of `edgar_8k.py`'s `HttpClient` protocol wrapping the `requests` library -- the collector has had no real implementation until now, only fakes in tests.
- [ ] `scripts/collect_premarket_8k.py` exposes an importable `run(cik_ticker_pairs, *, http_client, config) -> RunSummary` (never network calls at import time) that, for each CIK, calls `collect_8k_for_cik` then `normalise_snapshot` for every snapshot it wrote, and returns a summary distinguishing per-CIK success, per-CIK collector failure (logged, never turned into "zero events"), and zero-filings-today (a legitimate, distinct outcome) -- reusing `CollectionResult.failures` rather than reinventing failure tracking. A `main()` wires `run()` to real config, `RequestsHttpClient`, and the universe file, for the systemd service to invoke as `python -m` or a direct script call.
- [ ] `config/universe.csv` (ticker, cik columns) seeds a small starter universe for Gate 0 measurement purposes only -- this is *not* a trading-strategy universe (no price/liquidity filters apply here, since Gate 0 measures feed latency, not returns) -- and the entrypoint raises clearly rather than silently polling nothing if the file is empty or missing.
- [ ] `.env.example` documents every `EDGELAB_*` variable this story introduces, alongside the existing `EDGELAB_FINNHUB_API_KEY`, per [08-credentials.md](../docs/08-credentials.md)'s convention.
- [ ] `deploy/edgelab-8k-poll.service` + `deploy/edgelab-8k-poll.timer`: systemd units matching [04-infrastructure.md](../docs/04-infrastructure.md)'s schedule (`OnCalendar` covering 08:00-16:30 America/New_York, every 15 minutes), `RequiresMountsFor=/mnt/data`, `EnvironmentFile=-/etc/edgelab.env` (optional-prefixed so a missing file surfaces as this story's own `ConfigError`, not a silent systemd unit failure), and a `MemoryMax=` bound per the infra doc's staggering requirement.
- [ ] `deploy/install.sh`: idempotent (safe to re-run), creates `/mnt/data/edgelab/{raw,reports}` if missing, copies the unit files to `/etc/systemd/system/`, reloads systemd, enables and starts the timer -- and refuses to enable the timer (printing a clear message) if `/etc/edgelab.env` doesn't exist yet, rather than starting a service guaranteed to fail on its first tick.
- [ ] `deploy/uninstall.sh`: stops and disables the timer/service and removes the installed unit files (never touches `/mnt/data` -- data deletion is never a side effect of an uninstall script).
- [ ] Unit tests: `load_collector_config` with every required var present, with each required var individually missing (raises `ConfigError` naming that var), and default vs. overridden derived paths. `run()`'s three outcome branches (success, per-CIK failure, zero-filings) using a fake `HttpClient` and fake universe -- no real network or real systemd calls anywhere in tests.
- [ ] System test: `run()` invoked end-to-end against a fake `HttpClient` returning a realistic submissions+filing fixture (reusing STORY-002/003's existing test fixtures), writing through the real `raw_snapshot`, `event_store` stores in a temp dir, asserting the resulting DB state and `RunSummary` match.
- [ ] Since this sandbox is macOS and the Pi's systemd is not reachable from here, the `.service`/`.timer` files are validated only as well-formed INI (a unit test parses them with `configparser`) -- real `systemd-analyze verify` is explicitly deferred to `deploy/install.sh` running on the actual Pi, and this limitation is stated plainly in this story rather than claimed as tested.

## Explicit scope boundary

- No Finnhub, RSS, GDELT, or Form 4 collection -- 8-K only, matching every prior story's scope.
- No price collection wired into this schedule (STORY-004's collector exists but has its own future deploy story, matching the infra doc's separate 16:30 ET job).
- Does not itself install anything on a real Pi from this session -- this sandbox cannot reach the physical device (same limitation the Orchestrator Agent's spec already names for the git deploy). `deploy/install.sh` is written, tested for well-formedness, and handed to whoever has hands on the Pi (or a future SSH-capable agent) to run.
- Does not decide the Gate 0 measurement universe's business merit -- `config/universe.csv`'s starter list is a placeholder for the user to review and edit, not a trading recommendation.
- Does not build the daily ops report or the good-day/bad-day rubric -- STORY-009 and STORY-010.

## Definition of done

All seven gates apply, as every prior story.

## Credentials, if any

`EDGELAB_SEC_USER_AGENT` (already documented in [08-credentials.md](../docs/08-credentials.md), not yet set in any `.env` -- this story is what first makes its absence loudly block a run instead of silently going unused). `EDGELAB_DATA_DIR` is not a credential but is required the same way.
