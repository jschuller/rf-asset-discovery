# RF Asset Discovery

Production-quality RF signal processing with medallion architecture for OT/IoT security monitoring.

## Problem Statement

Identifies unknown wireless devices in industrial environments through passive RF spectrum analysis. Classifies assets by protocol, risk level, and CMDB CI class for integration with enterprise asset management systems.

## Key Results

| Metric | Value |
|--------|-------|
| Signals Collected | 169,485 |
| Verified (multi-detection) | 8,474 |
| RF Assets Identified | 935 |
| Test Coverage | 305 tests |

## Dashboard

![RF Asset Discovery Dashboard](docs/images/dashboard_screenshot.png?v=2)

*Streamlit dashboard showing medallion layer metrics, band distribution, and top signals*

## Asset Classification

![Gold Asset Distribution](docs/images/gold_asset_distribution.png?v=2)

*Assets classified by CMDB CI Class, Purdue Level, and Risk Level*

## Architecture

```mermaid
flowchart LR
    subgraph Collection
        SDR[RTL-SDR] --> Scanner
        SDR --> IoT[rtl_433]
    end

    subgraph Medallion
        Scanner --> Bronze[(Bronze<br/>169K)]
        IoT --> Bronze
        Bronze -->|detection ≥2| Silver[(Silver<br/>8.4K)]
        Silver -->|power ≥10dB| Gold[(Gold<br/>935)]
    end

    subgraph Output
        Gold --> Dashboard[Streamlit]
        Gold --> CSV[CSV Export]
        Gold --> CMDB[ServiceNow]
    end
```

## Features

- **Spectrum Scanning**: 24 MHz - 1.7 GHz coverage (RTL-SDR range)
- **Medallion Architecture**: Bronze → Silver → Gold data pipeline
- **CMDB Integration**: ServiceNow-ready asset classification (Purdue Model, risk levels)
- **IoT Discovery**: rtl_433 protocol decoding (TPMS, weather stations, remotes)
- **Claude Code Skills**: 9 agentic commands for autonomous operation

## Quick Start

```bash
# Install dependencies
brew install rtl-sdr rtl_433
uv sync --all-extras
export DYLD_LIBRARY_PATH=/opt/homebrew/lib

# Run dashboard with example data (no hardware required)
uv run streamlit run dashboard.py

# Or scan with RTL-SDR hardware
uv run rfad-scan --fm
```

> **Note:** The included `data/example.duckdb` contains sample data for demonstration.
> Run `rfad-scan` with RTL-SDR hardware to collect your own spectrum data.

## CLI Commands

| Command | Description | Example |
|---------|-------------|---------|
| `rfad-scan` | Spectrum scanner | `rfad-scan --fm` `rfad-scan -s 433 -e 435` |
| `rfad-survey` | Multi-segment survey | `rfad-survey create "Full"` |
| `rfad-transform` | Medallion pipeline | `rfad-transform full` |
| `rfad-iot` | IoT discovery | `rfad-iot -f 433.92M -d 300` |
| `rfad-watch` | Autonomous monitor | `rfad-watch --band aircraft` |
| `rfad-fm` | FM radio playback | `rfad-fm -f 101.9` |
| `rfad-am` | AM/aircraft radio | `rfad-am -f 119.1` |

## Python API

```python
from rf_asset_discovery.storage import UnifiedDB
from rf_asset_discovery.apps.survey import SurveyManager

with UnifiedDB("data/unified.duckdb") as db:
    manager = SurveyManager(db)
    survey = manager.create_adhoc_survey(
        name="FM Scan",
        start_hz=87.5e6,
        end_hz=108e6,
    )
```

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/ARCHITECTURE.md) | System design with mermaid diagrams |
| [Medallion Pattern](docs/MEDALLION-PATTERN.md) | Bronze/Silver/Gold pipeline |
| [Results Summary](docs/RESULTS-SUMMARY.md) | Data analysis and metrics |
| [Lessons Learned](docs/LESSONS-LEARNED.md) | Development insights |

## Project Structure

```
src/rf_asset_discovery/
├── apps/       # Scanner, recorder, survey, transform
├── decoders/   # ADS-B, IoT (rtl_433)
├── storage/    # DuckDB, Delta Lake, models
├── dsp/        # FFT, demodulation, filters
└── cli/        # Typer CLI

dashboard.py    # Streamlit visualization
exports/        # CSV exports
```

## Development

```bash
DYLD_LIBRARY_PATH=/opt/homebrew/lib pytest tests/ -v  # 305 tests
ruff check src/
mypy src/
```

## Legal

**Receive-only.** RTL-SDR devices operate in receive mode only—no transmission capability. Users are responsible for compliance with local RF monitoring regulations. Educational and authorized security research use only.

## License

MIT - See [LICENSE](LICENSE)
