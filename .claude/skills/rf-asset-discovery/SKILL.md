---
name: rf-asset-discovery
description: RF signal scanning, IoT discovery, and spectrum monitoring. Use when user mentions SDR, radio, signal, frequency, spectrum, FM, IoT, 433 MHz, antenna.
allowed-tools: Bash, Read, Write, Glob, Grep
---

# RF Asset Discovery

## Triggers
- "scan spectrum", "find signals", "what's on FM"
- "find IoT devices", "433 MHz", "weather station"
- "monitor aircraft", "watch frequency"
- "record signal", "capture IQ"

## Commands

```bash
# Scanning
uv run rfad-scan --fm              # FM broadcast
uv run rfad-scan --aircraft        # Aircraft band
uv run rfad-scan -s 400 -e 450     # Custom

# Survey (comprehensive, resumable, multi-location)
uv run rfad-survey create --name "Full Sweep" --full
uv run rfad-survey create --name "Site A" -l "NYC Office" -a "Discone"
uv run rfad-survey resume <id>     # Resume survey
uv run rfad-survey status <id>     # Check progress
uv run rfad-survey list -l "NYC Office"  # List by location
uv run rfad-survey next <id>       # Single segment (Ralph)

# IoT Discovery
uv run rfad-iot -f 433.92M,315M --db data/unified.duckdb

# Monitoring
uv run rfad-watch --band aircraft

# Recording
uv run rfad-record -f 101.9 -d 30

# Listening
uv run rfad-fm -f 101.9
uv run rfad-am -f 119.1
```

## Environment
```bash
export DYLD_LIBRARY_PATH=/opt/homebrew/lib
```

## Data
- `data/unified.duckdb` - DuckDB persistent storage
- `data/delta/signals` - Delta Lake for time travel queries
- `recordings/` - IQ samples (SigMF format)

### Schema (Survey-First Model)
All scans create surveys → signals go to unified `signals` table.

| Table | Purpose |
|-------|---------|
| `signals` | All RF detections with lifecycle |
| `assets` | Canonical CMDB inventory |
| `spectrum_surveys` | Survey orchestration |
| `survey_segments` | Segment definitions |
| `scan_sessions` | Audit log |

**Delta Lake:** Partitioned by `location_name/year/month` with time travel for baseline comparison.

## Reference
- [Best Practices](best-practices.md)
- [Frequency Bands](reference/frequency-bands.md)
- [Troubleshooting](troubleshooting.md)
