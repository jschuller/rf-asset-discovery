# SDR Toolkit Best Practices

Operational hygiene, reproducibility standards, and governance for SDR operations.

## Pre-flight Checklist

Before any SDR operation:

1. **Device check**
   ```bash
   rtl_test -t  # Should show "Found 1 device(s)"
   ```

2. **Library path** (Apple Silicon)
   ```bash
   export DYLD_LIBRARY_PATH=/opt/homebrew/lib:$DYLD_LIBRARY_PATH
   ```

3. **Antenna connected** - Verify physical connection

4. **Disk space** - IQ recordings are large (~8 MB/second at 1 MHz sample rate)

5. **Audio device** (for FM radio) - Check system audio output

## Reproducibility Standards

### Always Record These Parameters

| Parameter | Why | Example |
|-----------|-----|---------|
| Center frequency (Hz) | Core identifier | 101900000 |
| Sample rate (Hz) | Needed for playback | 1024000 |
| Gain (dB or "auto") | Affects signal levels | 40.2 |
| Timestamp (ISO 8601) | When captured | 2025-12-31T04:41:26Z |
| Antenna type | Reception characteristics | Telescopic whip |
| Location | Propagation context | 40.76°N, 74.00°W |

### Use SigMF Format

Always save recordings in SigMF format:
- `.sigmf-meta` - JSON metadata (human-readable)
- `.sigmf-data` - Raw IQ samples (binary)

```python
from sdr_toolkit.io.sigmf import SigMFRecording

recording = SigMFRecording.create(
    samples=samples,
    sample_rate=1.024e6,
    center_freq=101.9e6,
    output_dir=Path("recordings"),
    description="WFAN-FM capture"
)
```

### Session Structure

Organize recordings by date and session:

```
recordings/
└── 2024-12-30/
    ├── session_001/
    │   ├── scan_results.json       # Spectrum scan output
    │   ├── capture_101.9MHz.sigmf-meta
    │   ├── capture_101.9MHz.sigmf-data
    │   └── session.log             # Notes, observations
    └── session_002/
        └── ...
```

## Signal Capture Best Practices

### Before Recording

1. **Quick scan first** - Verify signal presence
   ```python
   scanner = SpectrumScanner(threshold_db=-35)
   result = scanner.scan(freq - 1e6, freq + 1e6)
   ```

2. **Check signal strength** - Aim for > -30 dB above noise

3. **Choose appropriate gain**
   - Too low: Weak signal, poor SNR
   - Too high: Clipping, distortion
   - Start with "auto", adjust if needed

4. **Verify disk space**
   - 1 second at 1 MHz = ~8 MB
   - 1 minute = ~480 MB
   - 10 minutes = ~4.8 GB

### During Recording

1. **Monitor for dropouts** - USB buffer issues
2. **Note any interference** - Nearby electronics, WiFi
3. **Use appropriate sample rate**
   - FM broadcast: 1-2 MHz
   - Narrowband: 200-500 kHz
   - Wideband: 2+ MHz

### After Recording

1. **Verify file integrity**
   ```python
   recording = SigMFRecording.load(path)
   samples = recording.to_numpy()
   assert len(samples) > 0
   ```

2. **Quick spectral check** - Confirm expected signal
3. **Add annotations** to SigMF metadata
4. **Backup important recordings**

## Governance

### Legal Compliance

1. **Receive only** - RTL-SDR cannot transmit
2. **No encrypted content** - Don't attempt to decode encrypted communications
3. **Respect privacy** - Don't record private communications
4. **Check local regulations** for specific bands:
   - Amateur radio requires license to transmit (receive is OK)
   - Some frequencies restricted in certain jurisdictions

### Data Retention

1. **Define retention policy** - How long to keep recordings?
2. **Secure storage** - Encrypt sensitive captures
3. **Clear labeling** - What, when, where, why
4. **Regular cleanup** - Delete old test recordings

### Data Classification

| Category | Example | Retention |
|----------|---------|-----------|
| Test | Quick scans, debugging | Delete after session |
| Reference | Known stations, calibration | Keep indefinitely |
| Research | Signal analysis, experiments | Project-dependent |
| Sensitive | Possibly private content | Handle with care |

## Device State Management

### Always Use Context Managers

```python
# GOOD - automatic cleanup
with SDRDevice(center_freq=101.9e6) as sdr:
    samples = sdr.read_samples(1024000)
# Device automatically closed

# BAD - manual cleanup required
sdr = SDRDevice(center_freq=101.9e6)
sdr.open()
samples = sdr.read_samples(1024000)
sdr.close()  # Easy to forget!
```

### Handle Errors Gracefully

```python
try:
    with SDRDevice() as sdr:
        samples = sdr.read_samples(n)
except DeviceNotFoundError:
    print("RTL-SDR not connected. Check USB cable.")
except DeviceError as e:
    print(f"Device error: {e}")
```

## Naming Conventions

### Files

```
<type>_<freq>_<date>_<time>.<ext>

Examples:
scan_fm_20251230_143022.json
capture_101.9MHz_20251230_143522.sigmf-meta
```

### Sessions

```
session_<number>_<purpose>

Examples:
session_001_fm_survey
session_002_aircraft_monitoring
```

## Performance Tips

1. **Lower sample rate on Apple Silicon** - Use 1.024 MHz instead of 2.048 MHz
2. **Shorter recordings** - Process in chunks if possible
3. **Close other USB devices** - Reduce contention
4. **Use SSD storage** - HDD may cause dropouts
5. **Batch processing** - Queue analysis tasks
