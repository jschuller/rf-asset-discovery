# SDR Toolkit Project Instructions

Project-specific instructions for Claude Code when working with sdr-toolkit.

## Project Overview

Production-quality RTL-SDR toolkit for spectrum scanning, signal recording, and FM demodulation.

**Location:** `~/construction-mcp/sdr-toolkit/`

## Environment Setup

### Apple Silicon (Required)

Before running any SDR code, set the library path:

```bash
export DYLD_LIBRARY_PATH=/opt/homebrew/lib:$DYLD_LIBRARY_PATH
```

### Verify Device

```bash
rtl_test -t
```

## Key Patterns

### Always Use Context Managers

```python
from sdr_toolkit.core.device import SDRDevice

with SDRDevice(center_freq=101.9e6) as sdr:
    samples = sdr.read_samples(1024000)
# Device automatically closed
```

### Use Correct Attribute Names

When working with results, check available attributes:
```python
print([a for a in dir(result) if not a.startswith('_')])
```

Common attributes:
- `SigMFRecording`: `center_frequency` (not `center_freq`), `sample_rate`
- `ScanResult`: `peaks`, `noise_floor_db`, `scan_time_seconds`
- `SignalPeak`: `frequency_hz` (not `freq_mhz`), `power_db`
- `RecordingResult`: `path` (not `file_path`)

### Standard Recording Location

```
recordings/YYYY-MM-DD/session_NNN/
```

## Safety Reminders

1. **Receive only** - RTL-SDR cannot transmit
2. **Legal compliance** - Don't decode encrypted communications
3. **Always use SigMF** - For reproducibility
4. **Context managers** - For proper device cleanup

## Common Tasks

### Quick FM Scan

```python
from sdr_toolkit.apps.scanner import SpectrumScanner

scanner = SpectrumScanner(threshold_db=-30)
result = scanner.scan(87.5e6, 108.0e6, step_hz=200e3)
```

### Record Signal

```python
from sdr_toolkit.apps.recorder import SignalRecorder
from pathlib import Path

recorder = SignalRecorder(center_freq_mhz=101.9)
result = recorder.record_iq(duration=10, output_dir=Path("recordings"))
```

### Analyze Recording

```python
from sdr_toolkit.io.sigmf import SigMFRecording
from sdr_toolkit.dsp.spectrum import compute_power_spectrum_hz

recording = SigMFRecording.load(Path("recording.sigmf-meta"))
samples = recording.to_numpy()
```

## Skills Available

The `sdr-toolkit` skill (in `.claude/skills/`) provides:
- Quick start guides
- Best practices documentation
- NYC metro frequency reference
- Troubleshooting guide

## NYC Metro Frequencies

Common frequencies for testing:
- 101.9 MHz - WFAN-FM (usually strongest)
- 93.9 MHz - WNYC-FM
- 162.55 MHz - NOAA Weather

## Running Tests

```bash
cd ~/construction-mcp/sdr-toolkit
DYLD_LIBRARY_PATH=/opt/homebrew/lib pytest tests/ -v
```

## CLI Commands

```bash
sdr-scan -s 87.5 -e 108.0    # Scan FM band
sdr-record -f 101.9 -d 30    # Record 30 seconds
sdr-fm -f 101.9              # Listen to FM station
```
