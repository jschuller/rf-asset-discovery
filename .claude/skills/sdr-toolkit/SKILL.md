---
name: sdr-toolkit
description: >
  Analyze and record RF signals using RTL-SDR hardware.
  Use when user mentions: SDR, radio, signal, frequency, spectrum,
  FM radio, RTL-SDR, antenna, demodulation, IQ samples, SigMF, scan.
  Capabilities: spectrum scanning, signal recording, FM demodulation,
  signal analysis, frequency detection.
allowed-tools: Bash, Read, Write, Glob, Grep
---

# SDR Toolkit Skill

Interact with RTL-SDR hardware to scan spectrum, record signals, and analyze RF data.

## Quick Start

### Pre-flight Check
Before any SDR operation, verify the device is connected:
```bash
rtl_test -t
```

### Set Library Path (Apple Silicon)
```bash
export DYLD_LIBRARY_PATH=/opt/homebrew/lib:$DYLD_LIBRARY_PATH
```

### Scan FM Band
```python
from sdr_toolkit.apps.scanner import SpectrumScanner

scanner = SpectrumScanner(threshold_db=-30)
result = scanner.scan(87.5e6, 108.0e6, step_hz=200e3)
print(f"Found {len(result.peaks)} signals")
```

### Record a Signal
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
freqs, power = compute_power_spectrum_hz(samples, recording.sample_rate, recording.center_frequency)
```

## Reference Documentation

- [Best Practices](best-practices.md) - Operational hygiene and reproducibility
- [Frequency Bands](reference/frequency-bands.md) - Common frequencies (NYC metro)
- [Troubleshooting](troubleshooting.md) - Common issues and fixes

## Key Classes

| Class | Purpose |
|-------|---------|
| `SDRDevice` | Low-level device control with context manager |
| `SpectrumScanner` | Sweep frequency range, detect signals |
| `SignalRecorder` | Record IQ samples to SigMF format |
| `FMRadio` | FM demodulation with audio output |
| `SigMFRecording` | Load/save industry-standard SigMF files |

## CLI Commands

```bash
sdr-scan -s 87.5 -e 108.0    # Scan FM band
sdr-record -f 101.9 -d 30    # Record 30 seconds
sdr-fm -f 101.9              # Listen to FM station
```

## Important Notes

1. **Receive only** - RTL-SDR cannot transmit
2. **Legal compliance** - Don't decode encrypted communications
3. **Always use SigMF** - Industry standard for reproducibility
4. **Close device properly** - Use context managers (`with SDRDevice()`)
