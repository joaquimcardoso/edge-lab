# ADR-0004 — The Pi collects, the laptop researches

**Status:** Accepted

## Context
The Pi 5 (4 GB) is reliable for continuous light workloads but constrained for heavy historical backtests and large downloads (e.g. GDELT history).

## Decision
The Pi runs collection, normalisation, classification batches, daily signals and reports. The laptop runs research, heavy backtests, GDELT history via BigQuery and model conversion.

## Consequences
- Parquet data is synced from the Pi to the laptop.
- Light experiments on daily data may run on the Pi, outside collection windows, with `MemoryMax` set.
