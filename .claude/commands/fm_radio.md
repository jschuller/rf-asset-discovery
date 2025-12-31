# FM Radio

Tune to an FM radio station and listen.

## Arguments
- `$FREQ_MHZ` - FM station frequency in MHz (required, e.g., 100.1)
- `$DURATION` - Listen duration in seconds (default: 30, use 0 for continuous)
- `$GAIN` - Receiver gain: "auto" or dB value (default: auto)

## Instructions

1. **Validate Frequency**
   - FM broadcast band: 87.5 - 108.0 MHz
   - Verify frequency is within valid range

2. **Initialize FM Radio**
   ```python
   from sdr_toolkit.apps.fm_radio import FMRadio

   radio = FMRadio(freq_mhz=$FREQ_MHZ, gain="$GAIN")
   ```

3. **Start Playback**
   ```python
   # For timed listening
   radio.play(duration=$DURATION)

   # For continuous listening (Ctrl+C to stop)
   radio.play()
   ```

4. **Monitor Signal**
   - Display signal strength periodically
   - Report audio quality
   - Note any interference or dropout

5. **Output Format**
   ```
   FM Radio: $FREQ_MHZ MHz
   ========================
   Status: Playing
   Signal: -28.5 dB (Strong)
   Audio: Good quality

   Press Ctrl+C to stop...
   ```

## Example Usage

Listen to a station for 30 seconds:
```
/fm_radio FREQ_MHZ=100.1 DURATION=30
```

Continuous listening:
```
/fm_radio FREQ_MHZ=91.5 DURATION=0
```

With manual gain:
```
/fm_radio FREQ_MHZ=103.5 GAIN=40
```

## Common FM Stations (US)
- News/Talk: Various NPR affiliates (88-92 MHz range)
- Classic Rock: Often in 100-108 MHz range
- Top 40: Varies by market

## Troubleshooting
- **No audio**: Check antenna connection, try increasing gain
- **Distorted**: Reduce gain or try different frequency
- **Choppy**: Signal may be weak, try better antenna placement
