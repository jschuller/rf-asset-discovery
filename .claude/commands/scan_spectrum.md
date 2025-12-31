# Scan Spectrum

Scan the RF spectrum to detect and classify signals.

## Arguments
- `$START_MHZ` - Start frequency in MHz (default: 87.5 for FM band)
- `$END_MHZ` - End frequency in MHz (default: 108.0 for FM band)
- `$STEP_KHZ` - Step size in kHz (default: 200)
- `$THRESHOLD_DB` - Detection threshold in dB (default: -30)

## Instructions

1. **Initialize SDR Device**
   ```python
   from sdr_toolkit.core.device import SDRDevice
   from sdr_toolkit.apps.scanner import SpectrumScanner

   scanner = SpectrumScanner(threshold_db=$THRESHOLD_DB)
   ```

2. **Execute Spectrum Scan**
   ```python
   result = scanner.scan(
       start_freq=$START_MHZ * 1e6,
       end_freq=$END_MHZ * 1e6,
       step_hz=$STEP_KHZ * 1e3
   )
   ```

3. **Analyze Results**
   - Report total number of signals detected
   - List strongest signals with frequencies and power levels
   - Classify signals by type (FM broadcast, narrowband, digital, etc.)
   - Estimate noise floor

4. **Output Format**
   ```
   Spectrum Scan: $START_MHZ - $END_MHZ MHz
   ========================================
   Signals Found: N
   Noise Floor: -XX.X dB

   Top Signals:
   1. XXX.X MHz: -XX.X dB (FM Broadcast)
   2. XXX.X MHz: -XX.X dB (Narrowband)
   ...
   ```

## Example Usage

Scan the FM broadcast band:
```
/scan_spectrum START_MHZ=87.5 END_MHZ=108.0
```

Scan amateur 2m band:
```
/scan_spectrum START_MHZ=144 END_MHZ=148 STEP_KHZ=12.5
```
