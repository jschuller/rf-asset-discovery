# Ralph IoT Discovery

Autonomous IoT device discovery using Ralph Wiggum loop technique.

## Usage

```
/ralph-iot                     # Run 3 scan cycles at 433.92 MHz
/ralph-iot --dual              # Scan both 433.92 MHz and 315 MHz
/ralph-iot --long              # Extended scan (5 cycles, 60s each)
```

## How It Works

Uses the Ralph Wiggum technique to iteratively scan for IoT devices:
1. Runs rtl_433 to capture ISM band transmissions
2. Decodes protocols (weather stations, TPMS, sensors, etc.)
3. Persists discovered devices to DuckDB
4. Stops after completing required scan cycles

## Quick Start

```bash
# Start Ralph loop for IoT discovery
/ralph-loop "Run IoT device discovery using rtl_433.

OBJECTIVE: Discover IoT devices at 433.92 MHz and 315 MHz bands

WORKFLOW:
1. Run: DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run sdr-iot -f 433.92M --db data/unified.duckdb --duration 30
2. Parse rtl_433 output for device packets
3. Run 3 scan cycles to capture intermittent transmitters

COMPLETION: Output <promise>IOT SCAN COMPLETE</promise> when:
- At least 3 scan cycles completed
- Devices persisted to database (or confirmed no devices after 3 attempts)

DATABASE: data/unified.duckdb" --completion-promise "IOT SCAN COMPLETE" --max-iterations 10
```

## Supported Frequencies

| Band | Frequency | Common Devices |
|------|-----------|----------------|
| ISM 433 | 433.92 MHz | Weather stations, temp sensors, door/window sensors |
| ISM 315 | 315 MHz | Car key fobs, garage doors, TPMS (US) |
| ISM 868 | 868 MHz | European IoT devices |
| ISM 915 | 915 MHz | US LoRa, industrial sensors |

## Supported Protocols (rtl_433)

- Acurite, Oregon Scientific, LaCrosse (weather stations)
- TPMS (tire pressure monitors)
- Honeywell, GE, Visonic (security sensors)
- Ambient Weather, Fine Offset
- Many more (1000+ device types)

## Scan Options

```bash
# Single frequency
uv run sdr-iot -f 433.92M --db data/unified.duckdb --duration 30

# Multi-frequency with hopping
uv run sdr-iot -f 433.92M,315M --db data/unified.duckdb --duration 60 --hop 30

# Higher gain for weak signals
uv run sdr-iot -f 433.92M --db data/unified.duckdb --gain 40
```

## Data Flow

```
Ralph Loop
    |
    v
rtl_433 subprocess
    |
    v
RTL433Decoder (JSON parsing)
    |
    v
DeviceRegistry (deduplication)
    |
    v
assets table (DuckDB)
```

## Device Classification

Discovered devices are classified into:
- **Protocol type**: weather, tpms, security, appliance, industrial
- **Device category**: sensor, controller, gateway, endpoint
- **CMDB CI class**: IOT_DEVICE, RF_SENSOR, etc.
- **Purdue level**: 0-5 (ISA-95 model)

## Monitoring

```bash
# Check IoT scan sessions
uv run python -c "
from sdr_toolkit.storage import UnifiedDB
with UnifiedDB('data/unified.duckdb') as db:
    sessions = db.conn.execute('''
        SELECT scan_id, start_time, results_summary
        FROM scan_sessions WHERE scan_type = 'iot'
        ORDER BY start_time DESC LIMIT 5
    ''').fetchall()
    for s in sessions:
        print(f'{s[0][:8]}... {s[1]}')
"
```

## Success Criteria

Ralph loop completes when:
- 3+ scan cycles executed
- Devices persisted OR confirmed no devices in range

## Important Notes

- IoT devices transmit **intermittently** (every 30s to several minutes)
- Multiple scan cycles needed to catch all transmitters
- 0 devices is a valid result if no compatible devices nearby
- Background RF noise doesn't count as device detection

## Environment

```bash
export DYLD_LIBRARY_PATH=/opt/homebrew/lib
```

## Cancel Loop

```
/cancel-ralph
```
