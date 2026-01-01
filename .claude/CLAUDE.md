# CLAUDE.md

SDR Toolkit: CLI + DuckDB + Claude Skills

## Current State (Sprint 12)

| Layer | Records | Notes |
|-------|--------:|-------|
| Bronze | 169,485 | Raw RF detections |
| Silver | 8,474 | Verified (multi-detected) |
| Gold | 935 | CMDB-ready assets |

**Key docs:** `docs/ARCHITECTURE.md`, `docs/LESSONS-LEARNED.md`

## Setup

```bash
uv sync --all-extras
export DYLD_LIBRARY_PATH=/opt/homebrew/lib
```

**System deps:** `brew install rtl-sdr rtl_433`

## Commands

```bash
# Scanning
uv run sdr-scan --fm              # FM band (87.5-108 MHz)
uv run sdr-scan --aircraft        # Aircraft (118-137 MHz)
uv run sdr-scan -s 400 -e 450     # Custom range

# IoT Discovery (rtl_433)
uv run sdr-iot -f 433.92M                           # Single band
uv run sdr-iot -f 433.92M,315M --db data/unified.duckdb  # Multi-band + persist

# Monitoring
uv run sdr-watch --band aircraft
uv run sdr-watch "Watch 121.5 MHz emergency"

# Recording
uv run sdr-record -f 101.9 -d 30  # 30 sec IQ recording

# Listening
uv run sdr-fm -f 101.9            # FM radio
uv run sdr-am -f 119.1            # Aircraft AM

# Medallion Transforms
uv run sdr-transform status       # Show pipeline status
uv run sdr-transform full         # Run bronze→silver→gold
```

## Skills

```
/prime           Context priming (start here)
/survey          Spectrum survey (quick + comprehensive)
/capture         Record + analyze signals
/fm_radio        FM listening
/iot             IoT device discovery
/watch           Autonomous monitoring
/transform       Medallion data transformations
```

## Schema (Medallion Architecture)

| Layer | Schema | Tables |
|-------|--------|--------|
| Bronze | `bronze` | signals, scan_sessions, survey_segments |
| Silver | `silver` | verified_signals, band_inventory |
| Gold | `gold` | rf_assets |

**Data flow:** Bronze (raw) → Silver (curated) → Gold (business-ready)

Main schema tables (legacy):
- `signals` - All RF detections
- `spectrum_surveys` - Survey orchestration
- `scan_sessions` - Operation audit log

## Architecture

```
src/sdr_toolkit/
├── apps/       # Scanner, recorder, FM/AM radio
├── decoders/   # IoT (rtl_433), ADS-B
├── storage/    # DuckDB unified storage
└── cli/        # Typer CLI

adws/           # Agentic workflows (TAC-8 style)
```

## Data

```
data/unified.duckdb   # Persistent storage
recordings/           # IQ samples (SigMF)
```

## Key Patterns

```python
# Always use context managers
with SDRDevice(center_freq=101.9e6) as sdr:
    samples = sdr.read_samples(1024000)

# IoT discovery with persistence
from sdr_toolkit.decoders.iot import RTL433Decoder, DeviceRegistry
from sdr_toolkit.storage import UnifiedDB

with UnifiedDB("data/unified.duckdb") as db:
    registry = DeviceRegistry(db=db)
    with RTL433Decoder(frequencies=["433.92M"]) as decoder:
        for packet in decoder.stream_packets():
            device = registry.process_packet(packet)
```

## Safety

- **Receive only** - RTL-SDR cannot transmit
- **Legal compliance** - Don't decode encrypted communications
- **Context managers** - Always close device properly

## Tests

```bash
DYLD_LIBRARY_PATH=/opt/homebrew/lib pytest tests/ -v
```

## Quick Gotchas

| Issue | Fix |
|-------|-----|
| SDR device locked | `pkill -f rtl_433` |
| PLL not locked warning | Ignore (edge frequency) |
| Database >100MB | Use CSV export, exclude from git |
| zsh loop fails | `export DYLD_LIBRARY_PATH` first |

## Key Thresholds

```
detection_count >= 2  → Silver layer
power_db >= 10        → Gold layer
power_db >= 25        → High priority
```

## Documentation

- `docs/ARCHITECTURE.md` - System diagrams
- `docs/MEDALLION-PATTERN.md` - Reusable template
- `docs/LESSONS-LEARNED.md` - Gotchas + patterns
- `docs/RESULTS-SUMMARY.md` - Final metrics
