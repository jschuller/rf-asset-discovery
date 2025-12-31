# SDR Toolkit Troubleshooting

Common issues and solutions for RTL-SDR operations.

## Device Issues

### Device Not Found

**Symptom:**
```
DeviceNotFoundError: No RTL-SDR devices found
```

**Solutions:**

1. **Check physical connection**
   ```bash
   # List USB devices
   system_profiler SPUSBDataType | grep -A5 "RTL\|Realtek"
   ```

2. **Verify device with rtl_test**
   ```bash
   rtl_test -t
   # Should show: Found 1 device(s)
   ```

3. **Unplug and replug** - USB enumeration can be flaky

4. **Try different USB port** - Some ports have power issues

5. **Check for driver conflicts** (Linux)
   ```bash
   # Blacklist DVB-T driver
   echo "blacklist dvb_usb_rtl28xxu" | sudo tee /etc/modprobe.d/blacklist-rtl.conf
   sudo modprobe -r dvb_usb_rtl28xxu
   ```

### Permission Denied (Linux)

**Symptom:**
```
usb_claim_interface error -3
```

**Solution:** Create udev rule
```bash
echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2838", MODE="0666"' | \
    sudo tee /etc/udev/rules.d/rtl-sdr.rules
sudo udevadm control --reload-rules
sudo udevadm trigger
# Replug device
```

### Library Not Found (Apple Silicon)

**Symptom:**
```
ImportError: Error loading librtlsdr
```

**Solution:** Set library path
```bash
export DYLD_LIBRARY_PATH=/opt/homebrew/lib:$DYLD_LIBRARY_PATH
```

Add to `~/.zshrc` for persistence:
```bash
echo 'export DYLD_LIBRARY_PATH=/opt/homebrew/lib:$DYLD_LIBRARY_PATH' >> ~/.zshrc
```

### PLL Not Locked

**Symptom:**
```
[R82XX] PLL not locked!
```

**Status:** This is usually informational, not an error. The device will still work.

**If causing issues:**
1. Try different sample rate (1.024 MHz instead of 2.048 MHz)
2. Let device warm up for 30 seconds
3. Check USB power (use powered hub)

## Recording Issues

### Buffer Overflow / Dropouts

**Symptom:**
```
Buffer overflow
Lost samples
```

**Solutions:**

1. **Lower sample rate**
   ```python
   SDRDevice(sample_rate=1.024e6)  # Instead of 2.048e6
   ```

2. **Use SSD storage** - HDD may be too slow

3. **Close other USB devices** - Reduce bus contention

4. **Increase buffer size** (if supported)

5. **Use shorter recordings** - Process in chunks

### File Size Issues

**Expected sizes:**
| Duration | Sample Rate | File Size |
|----------|-------------|-----------|
| 1 second | 1.024 MHz | ~8 MB |
| 10 seconds | 1.024 MHz | ~80 MB |
| 1 minute | 1.024 MHz | ~480 MB |
| 10 minutes | 1.024 MHz | ~4.8 GB |

**Check available space:**
```bash
df -h .
```

### SigMF Metadata Issues

**Problem:** Metadata doesn't match data

**Verify file pair:**
```python
from pathlib import Path

meta_path = Path("recording.sigmf-meta")
data_path = Path(str(meta_path).replace("-meta", "-data"))

assert meta_path.exists(), "Missing .sigmf-meta file"
assert data_path.exists(), "Missing .sigmf-data file"
```

## Audio Issues

### No Audio Output

**Solutions:**

1. **Check audio device**
   ```python
   import sounddevice as sd
   print(sd.query_devices())  # List available devices
   ```

2. **Verify signal strength**
   ```python
   scanner = SpectrumScanner()
   result = scanner.scan(freq - 1e6, freq + 1e6)
   print(f"Peak power: {max(p.power_db for p in result.peaks):.1f} dB")
   ```

3. **Check gain setting**
   - Too low = weak signal
   - Too high = distortion

### Audio Dropouts / Choppy

**Solutions:**

1. **Increase buffer size**
   ```python
   FMRadio(freq_mhz=101.9, buffer_size=4096)
   ```

2. **Lower sample rate**

3. **Close other applications** using audio

4. **Check CPU usage** - DSP is CPU-intensive

### Distorted Audio

**Solutions:**

1. **Reduce gain**
   ```python
   SDRDevice(gain=30.0)  # Instead of "auto"
   ```

2. **Check frequency accuracy** - May be slightly off-tune

3. **Verify modulation type** - FM vs AM

## Spectrum Analysis Issues

### Noise Floor Too High

**Expected:** -25 to -35 dB

**If higher:**
1. Check antenna connection
2. Move away from interference sources (monitors, WiFi routers)
3. Try different location
4. Use shielded USB cable

### Missing Expected Signals

**Solutions:**

1. **Lower threshold**
   ```python
   SpectrumScanner(threshold_db=-45)  # More sensitive
   ```

2. **Check frequency range** - Verify target is in scan range

3. **Check antenna** - Type matters (dipole vs whip)

4. **Time of day** - Some signals vary (AM propagation, activity)

### Spectrum Looks Wrong

**DC spike in center:**
- Normal for direct sampling SDRs
- Can be filtered in post-processing

**Mirror images:**
- Check if I/Q swap needed
- Some devices have reversed I/Q

## Platform-Specific Issues

### macOS (Apple Silicon)

1. **Library path** - Always set DYLD_LIBRARY_PATH
2. **Lower sample rate** - Use 1.024 MHz
3. **USB stability** - May need occasional replug
4. **Gatekeeper** - May need to allow rtl-sdr tools

### Linux (Debian/ParrotOS)

1. **Udev rules** - Required for non-root access
2. **DVB driver conflict** - Blacklist kernel module
3. **Package versions** - Use librtlsdr-dev

### Windows (WSL2)

1. **USB passthrough** - Requires usbipd-win
2. **Driver conflicts** - Zadig for driver installation
3. **Performance** - May be slower than native

## Survey Issues

### Survey Won't Resume

**Symptom:** `sdr-survey resume <id>` doesn't continue

**Solutions:**

1. **Check survey status**
   ```bash
   sdr-survey status <survey_id>
   ```
   - `paused` - Can resume
   - `completed` - Already finished
   - `failed` - Check error message

2. **Check for pending segments**
   ```python
   from sdr_toolkit.storage import UnifiedDB
   with UnifiedDB("data/unified.duckdb") as db:
       result = db.query(f"""
           SELECT COUNT(*) FROM survey_segments
           WHERE survey_id = '{survey_id}' AND status = 'pending'
       """)
       print(f"Pending segments: {result[0]['count']}")
   ```

3. **Reset failed segment**
   ```python
   db.conn.execute("""
       UPDATE survey_segments SET status = 'pending'
       WHERE segment_id = 'failed-segment-id'
   """)
   ```

### Segments Keep Failing

**Symptom:** Segments fail during scan

**Solutions:**

1. **Check RTL-SDR device**
   ```bash
   rtl_test -t
   ```

2. **Verify frequency range is valid**
   - RTL-SDR range: 24 MHz - 1766 MHz

3. **Check for USB issues**
   - Try different USB port
   - Unplug other USB devices

4. **Lower sample rate** if using high bandwidth

### Survey Progress Lost

**Symptom:** Progress not saved between sessions

**Solutions:**

1. **Verify database path**
   ```bash
   ls -la data/unified.duckdb
   ```

2. **Check for write errors** in logs

3. **Use explicit database path**
   ```bash
   sdr-survey resume <id> --db data/unified.duckdb
   ```

### Ralph Loop Timeout

**Symptom:** Ralph loop stops responding

**Solutions:**

1. **Check for SDR device lock**
   - Another process may be using the device
   - Restart the SDR device

2. **Verify segment isn't stuck**
   ```bash
   sdr-survey status <survey_id>
   ```

3. **Manual intervention**
   - Use `/cancel-ralph` to stop loop
   - Resume with `sdr-survey resume`

### Too Many Signals Detected

**Symptom:** Thousands of signals, mostly noise

**Solutions:**

1. **Increase threshold** in scan parameters

2. **Use auto-promote threshold**
   - Only signals with 3+ detections become assets

3. **Manually dismiss noise**
   - Update signal state to `dismissed`

4. **Check antenna** - May be picking up interference

## Getting Help

1. **Check device info:**
   ```bash
   rtl_test -t
   ```

2. **Verify Python environment:**
   ```python
   import pyrtlsdr
   print(pyrtlsdr.__version__)
   ```

3. **Test basic operation:**
   ```python
   from sdr_toolkit.core.device import SDRDevice
   with SDRDevice() as sdr:
       print(f"Opened: {sdr.is_open}")
   ```

4. **Check library versions:**
   ```bash
   pip list | grep -E "numpy|scipy|pyrtlsdr|sounddevice"
   ```
