# Record Signal

Record RF signals to SigMF format for later analysis.

## Arguments
- `$FREQ_MHZ` - Center frequency in MHz (required)
- `$DURATION` - Recording duration in seconds (default: 10)
- `$OUTPUT_DIR` - Output directory (default: ./recordings)
- `$FORMAT` - Output format: sigmf, wav, npy (default: sigmf)

## Instructions

1. **Check Signal Presence**
   ```python
   from sdr_toolkit.core.device import SDRDevice
   from sdr_toolkit.dsp.spectrum import compute_power_spectrum

   with SDRDevice(center_freq=$FREQ_MHZ * 1e6) as sdr:
       samples = sdr.read_samples(sdr.sample_rate)
       freqs, power = compute_power_spectrum(samples, sdr.sample_rate)
       peak_power = power.max()
       print(f"Signal strength: {peak_power:.1f} dB")
   ```

2. **Perform Recording**
   ```python
   from sdr_toolkit.apps.recorder import SignalRecorder

   recorder = SignalRecorder(center_freq_mhz=$FREQ_MHZ)
   result = recorder.record_iq(
       duration=$DURATION,
       output_dir="$OUTPUT_DIR"
   )
   ```

3. **Verify Recording**
   - Confirm file was created
   - Check file size is reasonable (expected: sample_rate * duration * 8 bytes)
   - Quick spectrum analysis to confirm signal presence

4. **Output Format**
   ```
   Recording Complete
   ==================
   File: $OUTPUT_DIR/recording_XXXXXX.sigmf-data
   Frequency: $FREQ_MHZ MHz
   Duration: $DURATION s
   Sample Rate: X.XXX MHz
   File Size: XX.X MB
   Signal Strength: -XX.X dB
   ```

## Example Usage

Record FM station:
```
/record_signal FREQ_MHZ=100.1 DURATION=30
```

Record with custom output:
```
/record_signal FREQ_MHZ=162.55 DURATION=60 OUTPUT_DIR=./weather_recordings
```
