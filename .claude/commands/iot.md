---
description: IoT device discovery using rtl_433
allowed-tools: Bash, Read, Write, Grep
---

Discover IoT devices on ISM bands (433 MHz, 315 MHz).

## Usage
`/iot` or `/iot 433.92M,315M`

## Commands
```bash
# Basic discovery
uv run sdr-iot -f 433.92M              # Single band
uv run sdr-iot -f 433.92M,315M         # Multi-band hopping
uv run sdr-iot -f 433.92M -d 300       # 5-minute scan

# With persistence (survey-first)
uv run sdr-iot -f 433.92M,315M -l "Home Lab"

# Verbose (show all packets)
uv run sdr-iot -f 433.92M -v
```

## Devices Found
- Weather stations (Acurite, Oregon, LaCrosse)
- TPMS (tire pressure)
- Door/window sensors
- Temperature sensors
- Remote controls

## Environment
```bash
export DYLD_LIBRARY_PATH=/opt/homebrew/lib
```

## Requires
`brew install rtl_433`
