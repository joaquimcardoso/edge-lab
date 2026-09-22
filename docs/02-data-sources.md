# 02 — Data sources

Free sources first ([ADR-0002](adr/0002-free-data-first.md)). Each source is trusted only for what it can actually support.

## Summary

| Source | Used for | Timestamp quality | Main limitation |
|---|---|---|---|
| **SEC EDGAR — 8-K** | Corporate events (results, material agreements, M&A) | Acceptance time to the second | Event direction not included |
| **SEC EDGAR — Form 4** | Insider transactions | Filing time | Filed up to 2 business days after the trade |
| **SEC XBRL `companyfacts`** | Fundamentals | `filed` date per value | Tag inconsistencies across companies |
| **SEC `company_tickers.json`** | Ticker ↔ CIK ↔ name mapping, entity linking | Current snapshot only | Needs its own dated history |
| **yfinance** | Daily OHLCV, analyst upgrades/downgrades, sector ETFs | Date only for analyst actions | Unofficial; can break; weak coverage of delisted names |
| **Stooq** | Backup daily prices | Daily | Coverage varies |
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
