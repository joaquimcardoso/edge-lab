# 02 — Data sources

Free sources first ([ADR-0002](adr/0002-free-data-first.md)). Each source is trusted only for what it can actually support.

## Source verification (2026-09-25)

Every free source below was checked against its own current terms/status before any collector is built — not assumed from when this document was first drafted. Findings:

- **SEC EDGAR:** confirmed free, no registration or API key, 10 req/s rate limit, descriptive `User-Agent` required. Matches this doc; source: sec.gov's own EDGAR access page.
- **yfinance:** confirmed still free and maintained, but explicitly unofficial — real risk of `429` throttling and silent breakage under load, consistent with this doc's existing "treat as fragile" stance. No change needed; the caution was already correctly calibrated.
- **Stooq:** confirmed free, but **no official API** — access is either a manual CSV download from the website or the `pandas-datareader` `stooq` reader (capped at roughly 5 years of history). A generic crawl of `stooq.com/db/` was blocked by `robots.txt`. Collectors must respect that — poll only the specific download endpoints people already use programmatically, at a conservative rate, never crawl the site. Description tightened in the table below.
- **Press-release wire RSS (PR Newswire, GlobeNewswire):** confirmed free public RSS feeds exist with broad topic/industry coverage and no paywall language found. Terms for automated polling aren't explicitly published; treat as free-to-read but keep the existing "respect rate limits, no scraping beyond RSS" rule.
- **Business Wire:** offers RSS/Atom/NX/FTP feeds per its own feed-options page, with a paid "PressPass Account" for extras beyond basic feeds — base RSS appears free. Its own site was returning a maintenance page during this check, a live reminder that this source is exactly as fragile as this doc already assumes ("forward only, noisy").
- **GDELT 2.0:** confirmed "100% free and open" directly from the GDELT Project's own site, via raw files, BigQuery, or its JSON APIs.
- **New candidate, not yet integrated — Finnhub free news API:** see [below](#candidate-finnhub-free-news-api-not-yet-integrated).

Verdict: every source this document currently relies on for the MVP has a genuine free-forever option; nothing here requires a subscription, and nothing needs to be built from scratch to cover the gap a "news" source fills — SEC (official events), GDELT (broad news mentions) and the wire RSS feeds already give redundant free coverage, with Finnhub's free news API as a documented, structured backup if wire RSS proves too unreliable once Phase 1's audit has real data on it.

## Summary

| Source | Used for | Timestamp quality | Main limitation |
|---|---|---|---|
| **SEC EDGAR — 8-K** | Corporate events (results, material agreements, M&A) | Acceptance time to the second | Event direction not included |
| **SEC EDGAR — Form 4** | Insider transactions | Filing time | Filed up to 2 business days after the trade |
| **SEC XBRL `companyfacts`** | Fundamentals | `filed` date per value | Tag inconsistencies across companies |
| **SEC `company_tickers.json`** | Ticker ↔ CIK ↔ name mapping, entity linking | Current snapshot only | Needs its own dated history |
| **yfinance** | Daily OHLCV, analyst upgrades/downgrades, sector ETFs | Date only for analyst actions | Unofficial; can break; weak coverage of delisted names |
| **Stooq** | Backup daily prices | Daily | No official API — manual CSV or `pandas-datareader` (~5y history cap); respect `robots.txt` |
| **Press-release wire RSS** (PR Newswire, Business Wire, GlobeNewswire) | Primary corporate announcements | `first_seen_at` (own) | Forward only |
| **Yahoo Finance / Nasdaq RSS per ticker** | Headlines, incl. analyst actions reported by press | `first_seen_at` (own) | Forward only; noisy |
| **GDELT 2.0** | Historical and live news mentions | 15-minute capture time | Generic, noisy for finance |

## SEC EDGAR

- Requests must send a descriptive `User-Agent` with contact email, and respect the SEC fair-access rate limit (currently 10 requests per second). Stay well below it.
- 8-K items of interest:
  - **2.02** Results of Operations and Financial Condition (earnings releases)
  - **1.01** Entry into a Material Definitive Agreement
  - **2.01** Completion of Acquisition or Disposition of Assets
  - **8.01** Other Events (noisy; later experiments only)
- 8-K item 2.02 also provides the **earnings calendar** used to exclude earnings-contaminated events in other experiments.
- EDGAR includes filers that were later delisted, which helps with survivorship on the event side.

## yfinance

- Treat as fragile. Every collector call is wrapped, failures are logged and surfaced, and **a failed download never produces a signal**.
- Analyst actions carry a date but no time. Apply the date-only rule in [01 §4](01-point-in-time-rules.md).
- Historical analyst data may be revised by the provider. Forward snapshots with `first_seen_at` are the only fully point-in-time version.

## RSS and news

- Store headline, URL, source, `published_at` (as declared) and `first_seen_at`. **Do not store full article text.**
- Respect `robots.txt`, rate limits and terms of use. No paywall circumvention. No HTML scraping of news sites.
- Deduplicate by canonical URL and a normalised-title hash; keep the earliest `first_seen_at` and the count of distinct sources.

## GDELT

- Live: poll the 15-minute update files and keep only rows linked to universe tickers.
- History: filter in the public GDELT dataset on BigQuery (free tier) from the laptop, then download the reduced result. Never backfill raw GDELT on the Pi.

## Candidate: Finnhub free news API (not yet integrated)

Verified 2026-09-25: Finnhub offers a free-forever tier (60 calls/minute, no credit card) that includes a company-news and general-market-news endpoint — a documented, structured JSON API rather than an RSS scrape, which is easier to build clean `known_at`/`first_seen_at` semantics around. Not yet added as a collector. Before it is:

- Verify Finnhub's free-tier terms of service specifically permit personal research and eventual algorithmic-trading use — free tiers on data APIs sometimes carve out commercial or trading use even when the tier itself is described as free.
- If terms are clean, it slots in as a redundant/backup source for press-release-style events, not a replacement for the SEC-timestamped sources this repository already prioritises.

## Paid upgrade path (not active)

Candidate vendor stack, as reported in September 2026 and **to be re-verified before purchase**:

| Component | Vendor | Notes |
|---|---|---|
| Prices, incl. delisted, minute bars | Massive (Stocks Developer) | 10 years history; live data 15 min delayed on this tier |
| Analyst ratings / price targets | Benzinga via Massive | Timestamped since 2013; reported dataset refresh every ~2 hours |
| Earnings with surprise | Benzinga via Massive | Since 2011 |

Purchase trigger: see [ADR-0002](adr/0002-free-data-first.md).

## Live price verification (Phase 3+)

When a signal is shown for manual execution:

1. Primary price source and a secondary source must agree within 1%; otherwise check a third source.
2. Display: price, currency, exchange, timestamp, data age.
3. Suppress the signal if the price cannot be verified or is stale for the strategy.
