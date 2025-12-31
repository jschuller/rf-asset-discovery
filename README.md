# SDR Toolkit

Production-quality RTL-SDR toolkit with agentic capabilities.

## Features

- **FM Radio** - Listen to FM broadcast stations
- **AM Radio** - Listen to AM signals (aircraft band 118-137 MHz)
- **Spectrum Scanner** - Find signals across frequency ranges
- **Signal Recorder** - Record IQ samples in SigMF format
- **ADS-B Decoder** - Decode aircraft transponder messages
- **Cross-Platform** - Works on macOS Apple Silicon and Linux

## Installation

```bash
# Clone the repository
git clone https://github.com/jschuller/sdr-toolkit.git
cd sdr-toolkit

# Install with uv (recommended)
uv venv
uv sync

# Or with pip
pip install -e .
```

### Platform-Specific Setup

#### macOS (Apple Silicon)

```bash
# Install RTL-SDR library
brew install rtl-sdr

# Set library path (add to .zshrc or use direnv)
export DYLD_LIBRARY_PATH="/opt/homebrew/lib:$DYLD_LIBRARY_PATH"
```

#### Linux (Debian/ParrotOS)

```bash
# Install RTL-SDR library
sudo apt install librtlsdr-dev

# Blacklist DVB-T drivers
echo "blacklist dvb_usb_rtl28xxu" | sudo tee /etc/modprobe.d/blacklist-rtlsdr.conf

# Add udev rules for non-root access
sudo cp /usr/share/doc/librtlsdr0/rtl-sdr.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
```

## CLI Usage

### FM Radio

```bash
# Listen to FM station
sdr-fm -f 100.1

# With custom gain and duration
sdr-fm -f 100.1 -g 30 -d 60
```

### AM Radio (Aircraft Band)

```bash
# Listen to aircraft communications (JFK Tower default)
sdr-am -f 119.1

# Show common NYC aircraft frequencies
sdr-am --aircraft

# With custom gain
sdr-am -f 118.7 -g 40
```

### Spectrum Scanner

```bash
# Scan FM broadcast band
sdr-scan --fm

# Scan aircraft band
sdr-scan --aircraft

# Custom frequency range
sdr-scan -s 433 -e 435 --step 50

# Show all signals (no limit)
sdr-scan --fm --all

# Plain text output (no rich formatting)
sdr-scan --fm --plain
```

### Signal Recorder

```bash
# Record IQ samples
sdr-record -f 100.1 -d 10 -o ./recordings

# Record FM audio to WAV
sdr-record -f 100.1 -d 30 --fm -o station.wav
```

## Python API

```python
from sdr_toolkit import SDRDevice
from sdr_toolkit.apps import FMRadio, AMRadio, SpectrumScanner

# FM Radio
radio = FMRadio(freq_mhz=100.1)
radio.play(duration=30)

# AM Radio (aircraft band)
am = AMRadio(freq_mhz=119.1)
am.play(duration=60)

# Spectrum Scanner
scanner = SpectrumScanner()
result = scanner.scan_fm_band()
for peak in result.peaks:
    print(f"{peak.frequency_hz/1e6:.1f} MHz: {peak.power_db:.1f} dB")

# Direct device access
with SDRDevice(center_freq=100.1e6) as sdr:
    samples = sdr.read_samples(1024)
```

## ADS-B Decoding

```python
from sdr_toolkit.decoders import decode_adsb_message, is_valid_adsb

# Decode ADS-B message (hex string)
msg = "8D4840D6202CC371C32CE0576098"
if is_valid_adsb(msg):
    decoded = decode_adsb_message(msg)
    print(f"ICAO: {decoded.icao}")
    print(f"Callsign: {decoded.callsign}")
```

## SigMF Recordings

```python
from sdr_toolkit.io import SigMFRecording

# Create recording
recording = SigMFRecording.create(
    samples=iq_samples,
    sample_rate=1.024e6,
    center_freq=100.1e6,
    output_dir="./recordings",
)

# Load recording
loaded = SigMFRecording.load("./recordings/recording_20240101.sigmf-meta")
samples = loaded.to_numpy()
```

## Agentic Workflows

See `adws/README.md` for Claude Code integration. Workflows enable autonomous spectrum scanning, recording, and analysis with built-in compliance awareness.

## Development

```bash
# Install dev dependencies
uv sync --extra dev

# Run tests
pytest

# Type checking
mypy src/

# Linting
ruff check src/
```

## Project Structure

```
sdr-toolkit/
├── src/sdr_toolkit/
│   ├── core/         # Device, config, exceptions
│   ├── dsp/          # Spectrum, demodulation, filters
│   ├── io/           # Audio, SigMF, recording
│   ├── apps/         # FM radio, AM radio, scanner, recorder
│   ├── decoders/     # ADS-B decoder
│   ├── ui/           # Rich terminal display
│   └── cli/          # Command-line interface
├── adws/             # Agentic Developer Workflows
├── ai_docs/          # AI/ML research documentation
├── tests/            # Unit tests
└── examples/         # Usage examples
```

## License

MIT License
