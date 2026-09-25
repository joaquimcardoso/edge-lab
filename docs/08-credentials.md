# 08 — Credentials and API keys

## Policy

- **Storage:** `.env`, never committed. `.env`, `*.key` and `secrets/` are already in `.gitignore`. Local/laptop development uses its own `.env` at the repo root; production (the Pi) has its own separate `.env`, created directly on the device — never copied over from a laptop's file, and never synced through git ([04-infrastructure.md](04-infrastructure.md) already states this; this document makes it concrete per source).
- **Naming convention:** `EDGELAB_<SOURCE>_<PURPOSE>`, e.g. `EDGELAB_SEC_USER_AGENT`, `EDGELAB_FINNHUB_API_KEY`. One name per credential, referenced the same way in code and in this document, so a new collector's required variable is discoverable by reading this file rather than the code.
- **Minimum scope, free tier only:** matches [ADR-0002](adr/0002-free-data-first.md). If a source's "free tier" requires a card on file, treat it as **not free** for this project — flag it in [02-data-sources.md](02-data-sources.md) rather than signing up.
- **Never in a Claude session:** an agent (or a human) never pastes a real secret value into a conversation transcript. Reference the env var **name** only; the actual value is set directly in `.env` on whichever machine needs it, by whoever has hands on that machine.
- **If one ever leaks:** treat a committed or exposed key as compromised immediately — revoke/regenerate at the source first, then deal with removing it from history. Don't wait to see if it "matters."

## Per source

### SEC EDGAR — no API key, but a required identity string

Not a secret, but required by [SEC's fair-access policy](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data): a descriptive `User-Agent` header naming the requester and a contact email, e.g. `"edge-lab research <your-email>"`.

- Get it: nothing to sign up for — just decide the string.
- Store as: `EDGELAB_SEC_USER_AGENT` in `.env`. Not sensitive, but keeping it there with everything else keeps all runtime config in one place, out of source.

### GDELT — no key for raw files; optional Google credentials for BigQuery

Raw GDELT files need no credentials at all. The BigQuery path ([03-architecture.md](03-architecture.md): laptop-only, for historical GDELT filtering) needs a free Google Cloud project:

1. Create a free Google Cloud account at [cloud.google.com](https://cloud.google.com) — no charge unless BigQuery's free monthly query quota is exceeded; verify the current quota before relying on it for anything routine.
2. Create a project and enable the BigQuery API.
3. Prefer `gcloud auth application-default login` on the laptop (no key file to manage or leak) over a service-account JSON key. If a key file is unavoidable, store it **outside the repository entirely** (e.g. `~/.config/edge-lab/gcp-key.json`) and reference only its path via `EDGELAB_GCP_CREDENTIALS_PATH` in `.env` — never inside the repo, even in a gitignored folder, since a `.gitignore` typo is a much easier mistake than a wrong path.

### Finnhub (candidate, not yet integrated) — free API key required

1. Sign up free at [finnhub.io/register](https://finnhub.io/register) — no card required for the free tier.
2. Copy the API key from the account dashboard.
3. Store as `EDGELAB_FINNHUB_API_KEY` in `.env`.
4. Getting the key is step one, not a green light: confirm the free tier's terms of service actually permit the intended research/trading use before this source is wired into a collector — see the open item in [02-data-sources.md](02-data-sources.md#candidate-finnhub-free-news-api-not-yet-integrated).

### Everything else in the MVP sequence — no credentials needed

yfinance, Stooq, PR Newswire RSS, GlobeNewswire RSS, Business Wire RSS: all public, no sign-up, no key. The entire [MVP story sequence](07-development-workflow.md#suggested-mvp-story-sequence-phase-1) can be built without creating a single account.

## For the Developer Agent

A story that needs a new credential names the exact env var it needs (in this document's naming convention) in its acceptance criteria, and this document gets a new entry in the same pull request — never a hardcoded key, a new ad hoc env var name invented on the spot, or a credential documented somewhere other than here.
