# Signal Capture

Record and analyze RF signals in one workflow. Creates IQ recordings in SigMF format with optional analysis.

## Usage

```
/capture -f 101.9 -d 30          # Record FM station for 30 seconds
/capture -f 433.92 -d 60 --analyze  # Record + analyze ISM signal
/capture analyze recordings/latest.sigmf  # Analyze existing capture
```

## Commands

### Record Signal

```bash
# Basic recording (creates SigMF file)
uv run rfad-record -f 101.9 -d 30

# With location context
uv run rfad-record -f 101.9 -d 30 -l "NYC Office"

# High sample rate for wideband
uv run rfad-record -f 915.0 -d 10 --sample-rate 2.4e6
```

Recordings are stored in `recordings/` with SigMF metadata.

### Analyze Capture

```bash
# Analyze existing recording
uv run sdr-analyze recordings/capture_101.9_20251231.sigmf

# Quick stats only
uv run sdr-analyze recordings/latest.sigmf --stats-only

# Generate spectrogram
uv run sdr-analyze recordings/latest.sigmf --spectrogram
```

## Recording Output

Each capture creates two files:
- `capture_<freq>_<timestamp>.sigmf-data` - IQ samples
- `capture_<freq>_<timestamp>.sigmf-meta` - JSON metadata

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

Analysis includes:
- Signal statistics (power, SNR, bandwidth)
- Modulation detection hints
- Frequency offset from center
- Spectrogram visualization (optional)

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

# 3. Analyze recording
uv run sdr-analyze recordings/latest.sigmf
```

### Document Interference

```bash
# Record interference at specific frequency
uv run rfad-record -f 2437.0 -d 120 -l "Office" --notes "WiFi interference"

# Analyze for pattern
uv run sdr-analyze recordings/latest.sigmf --spectrogram
```

## Environment

```bash
export DYLD_LIBRARY_PATH=/opt/homebrew/lib
```

## Data

- `recordings/` - IQ samples (SigMF format)
- `data/unified.duckdb` - Signal metadata with sigmf_path
