# 04 — Infrastructure

## Roles

- **Raspberry Pi 5 (4 GB):** 24/7 collector, normaliser, daily signal computation, light experiments on daily data, reports and commits.
- **Laptop:** research, heavy backtests, GDELT history, model conversion. See [ADR-0004](adr/0004-pi-collects-laptop-researches.md).

## Hardware

| Item | Requirement |
|---|---|
| Power supply | Official 27 W (5V/5A). With weaker supplies the Pi 5 limits USB current and external disks may drop. |
| Cooling | Official Active Cooler (sustained load causes throttling otherwise). |
| SD card | 64 GB, A2, preferably high-endurance. OS and software only. |
| External disk | USB 3, **ext4**. All data, logs and snapshots. 2.5" USB-powered or 3.5" with its own power. |

Keep a full image of the configured SD card on the laptop.

## OS configuration

- Raspberry Pi OS Lite 64-bit, headless.
- External disk mounted by UUID in `/etc/fstab` with `nofail`, e.g. at `/mnt/data`.
- **Every service declares `RequiresMountsFor=/mnt/data`** so nothing writes to the SD card when the disk is missing.
- `hd-idle` with a long timeout (or disabled during market hours) to avoid frequent spin-up cycles.
- `zram` instead of disk swap.
- journald volatile (or `log2ram`); application logs go to `/mnt/data/logs`.
- `/tmp` on tmpfs.

## Software

- Python 3.11+ in a virtual environment.
- SQLite in WAL mode (`PRAGMA journal_mode=WAL`) for operational data.
- DuckDB with `memory_limit` ≈ 1.5–2 GB for research queries; process by chunks, never load full history into pandas.
- FinBERT exported to **ONNX int8 on the laptop**; only the final model is copied to the Pi. No PyTorch on the Pi.
- No local LLM (4 GB is insufficient for useful quality). Optional API calls for ambiguous classifications.
- Exchange calendar library for sessions and holidays.

## Scheduling

systemd timers with explicit time zones. Each unit sets `MemoryMax=` and jobs are staggered so heavy work never overlaps collection.

| Lisbon (typical) | New York | Job |
|---|---|---|
| 13:00–14:15 | 08:00–09:15 | Pre-market snapshot: analyst actions, new 8-Ks, RSS |
| every 15 min, 13:00–21:30 | 08:00–16:30 | EDGAR 8-K / Form 4 polling, RSS, GDELT |
| 21:30 | 16:30 | Daily prices, features, signals, paper log, alerts |
| 22:00 | 17:00 | Daily report + commit |
| 02:00 | 21:00 | Classification batch (FinBERT) |
| Saturday | — | XBRL fundamentals, weekly report, backup verification |

Timers are defined in `America/New_York`; the Lisbon column is indicative only (DST transitions differ).

## Failure handling

- A collector failure is logged, alerted and **never** converted into "no event".
- Each feed has a health check: alert when a feed returns zero items for longer than its normal gap.
- Signals are suppressed when any required input for that day is missing.

## Backups

The raw store is irreplaceable: lost `first_seen_at` values cannot be recreated.

- Nightly consistent SQLite snapshot (`.backup` or `VACUUM INTO`), never a copy of a live file.
- Raw snapshots and the SQLite snapshot copied off-device (`rclone` to cloud storage and/or `rsync` to the laptop).
- Monthly restore test.

## Secrets

`.env` on the Pi, never committed. API keys have minimum scopes. The GitHub deploy key is write-limited to this repository.

## Role of Claude Pro

- Development and maintenance with Claude Code.
- Scheduled weekly review of the reports in the repository: data anomalies, interesting rejections, experiment progress.
- Review of every rule change for look-ahead.

Not in the data path: scheduling on the Pi is independent of Claude sessions and usage limits.
