# Signal Capture

Record and analyze RF signals in one workflow. Creates IQ recordings in SigMF format with optional analysis.

## Usage

```
/capture -f 101.9 -d 30          # Record FM station for 30 seconds
/capture -f 433.92 -d 60 --analyze  # Record + analyze ISM signal
/capture analyze recordings/recording_<timestamp>.sigmf-meta  # Analyze existing capture
```

## Commands

### Record Signal

```bash
# Basic recording (creates SigMF file)
uv run rfad-record -f 101.9 -d 30

# With location context
uv run rfad-record -f 101.9 -d 30 -l "NYC Office"

# Fixed gain, other output directory
uv run rfad-record -f 915.0 -d 10 -g 30 -o recordings/ism
```

Recordings are stored in `recordings/` (`-o` to change) with SigMF metadata.
The sample rate is the platform default (1.024 MHz on Apple Silicon, 2.048 MHz
elsewhere); `rfad-record` has no option to change it. The RTL-SDR tunes
24-1766 MHz, so 2.4 GHz WiFi and 5 GHz bands are out of range.

### Analyze Capture

There is no analyze command. Analyze a recording with the library's SigMF
reader and DSP functions:

```bash
uv run python - recordings/recording_20251231_120000.sigmf-meta <<'PY'
import sys

import numpy as np

from rf_asset_discovery.dsp.spectrum import (
    compute_power_spectrum_hz,
    compute_spectrogram,
    estimate_noise_floor,
    find_peaks,
    signal_to_noise,
)
from rf_asset_discovery.io.sigmf import SigMFRecording

rec = SigMFRecording.load(sys.argv[1])
samples = rec.to_numpy()
print(rec, f"{rec.duration_seconds:.1f} s")

# Spectrum of the last 2048 samples, frequencies in Hz
freqs_hz, power = compute_power_spectrum_hz(samples, rec.sample_rate, rec.center_frequency or 0)
print(f"Noise floor {estimate_noise_floor(power):.1f} dB, SNR {signal_to_noise(power):.1f} dB")
peaks = find_peaks(power, threshold_db=estimate_noise_floor(power) + 10)
for idx, peak_db in sorted(peaks, key=lambda p: p[1], reverse=True)[:10]:  # strongest first
    print(f"  peak {freqs_hz[idx] / 1e6:.4f} MHz  {peak_db:.1f} dB")

# Spectrogram (time x frequency bins, dB) over the whole recording
times, freqs, spectrogram = compute_spectrogram(samples)
print("spectrogram", spectrogram.shape, f"max {np.max(spectrogram):.1f} dB")
PY
```

## Recording Output

Each capture creates two files (timestamp in UTC; `rfad-record` prints the path):
- `recording_<YYYYmmdd_HHMMSS>.sigmf-data` - IQ samples
- `recording_<YYYYmmdd_HHMMSS>.sigmf-meta` - JSON metadata

### SigMF Metadata Example

```json
{
  "global": {
    "core:datatype": "cf32_le",
    "core:sample_rate": 1024000,
    "core:hw": "RTL-SDR"
  },
  "captures": [{
    "core:sample_start": 0,
    "core:frequency": 101900000
  }],
  "annotations": []
}
```

## Analysis Output

The snippet above prints:
- Noise floor and SNR estimates
- The strongest spectral peaks, in MHz
- Spectrogram dimensions (plot `spectrogram` with matplotlib from the `plot` extra)

## Integration with Surveys

Recordings are linked to surveys via the signals table:

```bash
# Record creates adhoc survey + signal entry
uv run rfad-record -f 433.92 -d 30 -l "Lab"

# Signal entry includes sigmf_path for later analysis
```

## Common Workflows

### Capture Unknown Signal

```bash
# 1. Scan to find signal
uv run rfad-scan -s 430 -e 440

# 2. Record strong signal
uv run rfad-record -f 433.92 -d 60

# 3. Analyze recording: run the "Analyze Capture" snippet on the
#    .sigmf-meta path that rfad-record printed
```

### Document Interference

```bash
# Record interference at specific frequency (915 MHz ISM; must be 24-1766 MHz)
uv run rfad-record -f 915.0 -d 120 -l "Office"

# Analyze for pattern: run the "Analyze Capture" snippet and look at the spectrogram
```

## Environment

```bash
export DYLD_LIBRARY_PATH=/opt/homebrew/lib
```

## Data

- `recordings/` - IQ samples (SigMF format)
- `data/unified.duckdb` - Signal metadata with sigmf_path
