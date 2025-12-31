# Spectrum Survey

All-in-one spectrum scanning: comprehensive surveys AND quick ad-hoc scans.

## Usage

```
/survey                     # Show usage
/survey quick --fm          # Quick ad-hoc scan (replaces /scan_spectrum)
/survey create "My Survey"  # Create comprehensive survey
/survey resume <id>         # Resume existing survey
/survey status <id>         # Check progress
```

## Commands

### Quick Ad-Hoc Scan (Survey-First)

```bash
# Ad-hoc scans create single-segment surveys automatically
uv run sdr-scan --fm                        # FM band (87.5-108 MHz)
uv run sdr-scan --aircraft                  # Aircraft band (118-137 MHz)
uv run sdr-scan -s 400 -e 450               # Custom range
uv run sdr-scan --fm -l "NYC Office"        # With location
```

All scans route through surveys → signals table → optional promotion to assets.

### Create Full Survey

```bash
# Full survey (24-1766 MHz with gap filling) - ~30-45 min
uv run sdr-survey create --name "Full Sweep" --full

# Priority bands only (faster, ~10 min)
uv run sdr-survey create --name "Quick Scan" --priority-only

# Custom range
uv run sdr-survey create --name "VHF Survey" -s 100 -e 500
```

### Resume Survey

```bash
# Resume all remaining segments
uv run sdr-survey resume <survey_id>

# Scan only 5 segments then pause
uv run sdr-survey resume <survey_id> --max 5
```

### Check Status

```bash
# List all surveys
uv run sdr-survey list

# Single survey status
uv run sdr-survey status <survey_id>

# JSON output (for scripts)
uv run sdr-survey status <survey_id> --json
```

### Execute Next Segment (Ralph Integration)

```bash
# Single segment execution
uv run sdr-survey next <survey_id>

# JSON output for Ralph loops
uv run sdr-survey next <survey_id> --json
```

## Ralph Loop Integration

Start a Ralph loop to complete a survey iteratively:

```bash
/ralph-loop "Complete spectrum survey <id>. Run: uv run sdr-survey next <id>. Continue until you see 'SURVEY COMPLETE'. Output <promise>SURVEY COMPLETE</promise> when done." --max-iterations 50
```

## Survey Types

| Type | Coverage | Segments | Time |
|------|----------|----------|------|
| Full | 24-1766 MHz | ~40 | 30-45 min |
| Priority Only | Known bands | ~15 | 10 min |
| Custom | User-specified | Varies | Varies |

## Priority Bands (Scanned First)

- FM Broadcast (87.5-108 MHz)
- Aircraft VHF (118-137 MHz)
- Amateur 2m (144-148 MHz)
- Marine VHF (156-162 MHz)
- NOAA Weather (162.4-162.55 MHz)
- ISM 315 MHz (314-316 MHz)
- Amateur 70cm (420-450 MHz)
- ISM 433 MHz (433-434.8 MHz)
- FRS/GMRS (462-467.7 MHz)
- ISM 868/915 MHz
- ADS-B 1090 MHz

## Multi-Location Surveys

Run surveys from different locations with full differentiation (ServiceNow ITOM-style):

```bash
# Create survey with location context
uv run sdr-survey create --name "Morning Scan" \
    --location "NYC Office" \
    --antenna "Discone" \
    --notes "Clear weather"

# Run again from different location
uv run sdr-survey create --name "Evening Scan" \
    --location "Hoboken Home" \
    --antenna "Stock RTL-SDR"

# List surveys by location
uv run sdr-survey list --location "NYC Office"
```

**Tracked Context:**
- Location name (auto-increments run number)
- GPS coordinates (optional)
- Antenna type
- Conditions notes

## Signal State Management

Discovered signals progress through states (ServiceNow-style):

- **discovered** - Initial detection
- **confirmed** - Manually verified
- **dismissed** - Marked as noise
- **promoted** - Converted to asset

Signals auto-promote to assets after 3+ detections.

## Database

All data persists in `data/unified.duckdb`:

- `spectrum_surveys` - Survey metadata (with location/run context)
- `survey_segments` - Individual scan blocks
- `signals` - All RF detections with lifecycle (unified table)
- `assets` - Canonical CMDB inventory (promoted from signals)
- `scan_sessions` - Operation audit log

Delta Lake (`data/delta/signals`) provides time travel for baseline comparison.

## Environment

```bash
export DYLD_LIBRARY_PATH=/opt/homebrew/lib
```
