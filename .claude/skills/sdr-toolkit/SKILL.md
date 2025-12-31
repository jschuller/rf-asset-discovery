---
name: sdr-toolkit
description: RF signal scanning, IoT discovery, and spectrum monitoring. Use when user mentions SDR, radio, signal, frequency, spectrum, FM, IoT, 433 MHz, antenna.
allowed-tools: Bash, Read, Write, Glob, Grep
---

# SDR Toolkit

## Triggers
- "scan spectrum", "find signals", "what's on FM"
- "find IoT devices", "433 MHz", "weather station"
- "monitor aircraft", "watch frequency"
- "record signal", "capture IQ"

## Commands

```bash
# Scanning
uv run sdr-scan --fm              # FM broadcast
uv run sdr-scan --aircraft        # Aircraft band
uv run sdr-scan -s 400 -e 450     # Custom

# Survey (comprehensive, resumable, multi-location)
uv run sdr-survey create --name "Full Sweep" --full
uv run sdr-survey create --name "Site A" -l "NYC Office" -a "Discone"
uv run sdr-survey resume <id>     # Resume survey
uv run sdr-survey status <id>     # Check progress
uv run sdr-survey list -l "NYC Office"  # List by location
uv run sdr-survey next <id>       # Single segment (Ralph)

# IoT Discovery
uv run sdr-iot -f 433.92M,315M --db data/unified.duckdb

# Monitoring
uv run sdr-watch --band aircraft

# Recording
uv run sdr-record -f 101.9 -d 30

# Listening
uv run sdr-fm -f 101.9
uv run sdr-am -f 119.1
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
