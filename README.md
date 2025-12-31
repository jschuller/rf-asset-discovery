# SDR Toolkit

Production-quality RTL-SDR toolkit with unified asset storage and agentic capabilities.

## Features

| Category | Capabilities |
|----------|--------------|
| **Radio** | FM broadcast, AM/aircraft band (118-137 MHz) |
| **Scanning** | Spectrum analysis, peak detection, noise floor estimation |
| **Survey** | Multi-segment resumable surveys, signal state management |
| **Recording** | IQ samples (SigMF), FM audio (WAV) |
| **Decoding** | ADS-B aircraft, IoT devices (rtl_433) |
| **Monitoring** | Autonomous spectrum watch, anomaly detection, push alerts |
| **Storage** | DuckDB unified asset schema, Parquet export |
| **Compliance** | NIST 800-213A, ServiceNow CMDB, ISA-95/Purdue |

## Installation

```bash
# Install with pip
pip install -e ".[all]"

# Or specific extras
pip install -e ".[storage,ui]"  # DuckDB + Rich terminal
```

### Platform Setup

**macOS (Apple Silicon)**
```bash
brew install rtl-sdr rtl_433
export DYLD_LIBRARY_PATH="/opt/homebrew/lib:$DYLD_LIBRARY_PATH"
```

**Linux**
```bash
sudo apt install librtlsdr-dev rtl-433
echo "blacklist dvb_usb_rtl28xxu" | sudo tee /etc/modprobe.d/blacklist-rtlsdr.conf
```

## CLI Commands

| Command | Description | Example |
|---------|-------------|---------|
| `sdr-fm` | FM radio playback | `sdr-fm -f 100.1 -g auto` |
| `sdr-am` | AM/aircraft band | `sdr-am -f 119.1 --aircraft` |
| `sdr-scan` | Spectrum scanner | `sdr-scan --fm` or `-s 433 -e 435` |
| `sdr-survey` | Spectrum survey | `sdr-survey create "Full Sweep"` |
| `sdr-record` | IQ/audio recorder | `sdr-record -f 100.1 -d 30 --fm` |
| `sdr-iot` | IoT device discovery | `sdr-iot -f 433.92M -d 300` |
| `sdr-watch` | Autonomous monitor | `sdr-watch "Watch aircraft band" --ntfy alerts` |

## Python API

### Spectrum Scanning
```python
from sdr_toolkit.apps import SpectrumScanner

scanner = SpectrumScanner(threshold_db=-30)
result = scanner.scan_fm_band()
for peak in result.peaks[:5]:
    print(f"{peak.frequency_hz/1e6:.1f} MHz: {peak.power_db:.1f} dB")
```

### IoT Device Discovery
```python
from sdr_toolkit.decoders.iot import RTL433Decoder, DeviceRegistry

registry = DeviceRegistry()
with RTL433Decoder(frequencies=["433.92M"]) as decoder:
    for packet in decoder.stream_packets():
        device = registry.process_packet(packet)
        print(f"{device.model}: {device.protocol_type.value}")
```

### Unified Asset Storage
```python
from sdr_toolkit.storage import UnifiedDB, Asset, RFProtocol, auto_classify_asset

with UnifiedDB("data/unified.duckdb") as db:
    asset = Asset(
        name="Weather Station",
        rf_frequency_hz=433.92e6,
        rf_protocol=RFProtocol.WEATHER_STATION,
    )
    auto_classify_asset(asset)  # Sets CMDB class, Purdue level
    db.insert_asset(asset)

    # Export for analysis
    db.export_to_parquet("exports/")
```

### ADS-B Decoding
```python
from sdr_toolkit.decoders import decode_adsb_message

msg = decode_adsb_message("8D4840D6202CC371C32CE0576098")
print(f"ICAO: {msg.icao}, Callsign: {msg.callsign}")
```

### Autonomous Spectrum Watch
```python
import asyncio
from adws import watch_from_intent

async def main():
    # Natural language configuration
    watch = await watch_from_intent(
        "Watch aircraft band, alert on 121.5 MHz emergency",
        ntfy_topic="my-sdr-alerts",
    )
    # Runs until stopped
    await asyncio.sleep(3600)
    await watch.stop()

asyncio.run(main())
```

## Project Structure

```
src/sdr_toolkit/
├── core/       # Device abstraction, config, exceptions
├── dsp/        # FFT, demodulation, filters
├── io/         # SigMF, audio I/O
├── apps/       # FM, AM, scanner, recorder
├── decoders/   # ADS-B, IoT (rtl_433)
├── storage/    # DuckDB unified schema
├── ui/         # Rich terminal display
└── cli/        # Command-line interface

specs/          # Implementation specifications
adws/           # Agentic Developer Workflows
```

## Specifications

| Spec | Status | Description |
|------|--------|-------------|
| Unified Asset Schema | ✅ Implemented | DuckDB + CMDB/NIST/Purdue alignment |
| IoT Protocol Discovery | ✅ Implemented | rtl_433 wrapper, device registry |
| Autonomous Monitor | ✅ Implemented | Spectrum watch, alerts, ntfy.sh |
| Spectrum Survey | ✅ Implemented | Multi-segment surveys, signal state management |
| TorchSig Integration | 📋 Research | ML signal classification |

See `specs/README.md` for roadmap and dependencies.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests (300+ tests)
DYLD_LIBRARY_PATH=/opt/homebrew/lib pytest

# Type checking
mypy src/

# Linting
ruff check src/
```

## License

MIT License
