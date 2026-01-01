# Ralph Spectrum Scan

Autonomous spectrum survey using Ralph Wiggum loop technique.

## Usage

```
/ralph-scan                    # Create and run new comprehensive survey
/ralph-scan resume <id>        # Resume existing survey with Ralph loop
/ralph-scan quick              # Quick priority-only survey
```

## How It Works

Uses the Ralph Wiggum technique to iteratively execute survey segments:
1. Creates a spectrum survey with all priority bands
2. Executes segments one-by-one in a Ralph loop
3. Signals auto-ingest into DuckDB data lake
4. Stops when survey reaches 100% completion

## Quick Start

```bash
# Step 1: Create survey
DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run rfad-survey create --name "Ralph Survey $(date +%Y%m%d_%H%M)" --db data/unified.duckdb

# Step 2: Start Ralph loop (replace SURVEY_ID)
/ralph-loop "Execute spectrum survey segments.

OBJECTIVE: Scan all priority RF bands and ingest signals into data/unified.duckdb

WORKFLOW:
1. Run: DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run rfad-survey next SURVEY_ID --db data/unified.duckdb
2. Check segment completion status
3. Continue until survey reaches 100%

COMPLETION: Output <promise>SURVEY COMPLETE</promise> when:
- Survey status shows 'completed'
- All segments status='completed'
- No pending segments remain

DATABASE: data/unified.duckdb" --completion-promise "SURVEY COMPLETE" --max-iterations 35
```

## Survey Types

| Mode | Bands | Segments | Est. Time |
|------|-------|----------|-----------|
| Full | 24-1766 MHz | ~29 | 10-15 min |
| Priority | Known bands | ~15 | 5-8 min |
| Custom | User-specified | Varies | Varies |

## Priority Bands Scanned

- FM Broadcast (87.5-108 MHz)
- Aircraft VHF (118-137 MHz)
- Amateur 2m/70cm (144-148, 420-450 MHz)
- Marine VHF (156-162 MHz)
- ISM 315/433/868/915 MHz
- FRS/GMRS (462-467.7 MHz)
- ADS-B 1090 MHz
- GPS L1 (1575 MHz)
- Gap frequencies (coarse sweep)

## Data Flow

```
Ralph Loop
    |
    v
rfad-survey next <id>
    |
    v
SpectrumScanner.scan()
    |
    v
signals table (DuckDB)
    |
    v
Auto-promote (detection_count >= 3)
    |
    v
assets table (CMDB)
```

## Monitoring Progress

```bash
# Check survey status
DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run rfad-survey status <survey_id>

# Query database directly
uv run python -c "
from rf_asset_discovery.storage import UnifiedDB
with UnifiedDB('data/unified.duckdb') as db:
    survey = db.conn.execute('''
        SELECT name, status, completion_pct, total_signals_found
        FROM spectrum_surveys WHERE survey_id = 'SURVEY_ID'
    ''').fetchone()
    print(f'{survey[0]}: {survey[2]:.1f}% complete, {survey[3]} signals')
"
```

## Success Criteria

Ralph loop completes when:
- All segments executed (status='completed')
- Survey reaches 100% completion
- Signals persisted to database

## Environment

```bash
export DYLD_LIBRARY_PATH=/opt/homebrew/lib
```

## Cancel Loop

```
/cancel-ralph
```
