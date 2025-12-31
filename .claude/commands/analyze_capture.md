# Analyze Capture

Analyze a previously recorded RF signal capture.

## Arguments
- `$RECORDING_PATH` - Path to SigMF recording (.sigmf-meta or .sigmf-data) (required)
- `$ANALYSIS_TYPE` - Analysis type: spectrum, demod, classify (default: spectrum)

## Instructions

1. **Load Recording**
   ```python
   from sdr_toolkit.io.sigmf import SigMFRecording

   recording = SigMFRecording.load("$RECORDING_PATH")
   samples = recording.to_numpy()
   print(f"Loaded {len(samples)} samples at {recording.sample_rate} Hz")
   print(f"Center frequency: {recording.center_freq / 1e6} MHz")
   ```

2. **Perform Analysis**

   **For "spectrum" analysis:**
   ```python
   from sdr_toolkit.dsp.spectrum import compute_power_spectrum, find_peaks

   freqs, power = compute_power_spectrum(samples, recording.sample_rate)
   peaks = find_peaks(freqs, power, threshold_db=-30)
   ```

   **For "demod" analysis:**
   ```python
   from sdr_toolkit.dsp.demodulation import fm_demodulate

   audio, audio_rate = fm_demodulate(samples, recording.sample_rate)
   # Analyze audio content
   ```

   **For "classify" analysis:**
   - Examine signal bandwidth
   - Identify modulation characteristics
   - Classify as FM/AM/digital/unknown

3. **Report Findings**
   - Signal type classification
   - Signal strength (dB)
   - Signal-to-noise ratio (dB)
   - Bandwidth estimation
   - Modulation identification
   - Any notable characteristics

4. **Output Format**
   ```
   Signal Analysis Report
   ======================
   Recording: $RECORDING_PATH
   Analysis Type: $ANALYSIS_TYPE

   Signal Classification: FM Broadcast
   Signal Strength: -25.3 dB
   SNR: 35.2 dB
   Bandwidth: 200 kHz
   Modulation: Wideband FM (stereo)

   Summary: Strong FM broadcast signal with good SNR...
   ```

## Example Usage

Analyze spectrum of a recording:
```
/analyze_capture RECORDING_PATH=./recordings/fm_capture.sigmf-meta
```

Demodulate and analyze audio:
```
/analyze_capture RECORDING_PATH=./recordings/fm_capture.sigmf-meta ANALYSIS_TYPE=demod
```

Classify unknown signal:
```
/analyze_capture RECORDING_PATH=./recordings/unknown.sigmf-meta ANALYSIS_TYPE=classify
```
