---
description: Prime Claude with project context
allowed-tools: Bash, Read, Glob
---

Context priming for new session. Shows project structure and recent activity.

## Usage
`/prime`

## Steps

1. Show project structure:
```bash
git ls-files
```

2. Check database for previous discoveries:
```bash
DYLD_LIBRARY_PATH=/opt/homebrew/lib uv run python -c "
from sdr_toolkit.storage import UnifiedDB
from pathlib import Path
db_path = Path('data/unified.duckdb')
if db_path.exists():
    with UnifiedDB(db_path) as db:
        assets = db.get_all_assets()
        # Survey tables
        surveys = db.conn.execute('SELECT COUNT(*) FROM spectrum_surveys').fetchone()[0]
        segments = db.conn.execute('SELECT COUNT(*) FROM survey_segments').fetchone()[0]
        signals = db.conn.execute('SELECT COUNT(*) FROM survey_signals').fetchone()[0]
        # Legacy scan tables
        sessions = db.conn.execute('SELECT COUNT(*) FROM scan_sessions').fetchone()[0]
        captures = db.conn.execute('SELECT COUNT(*) FROM rf_captures').fetchone()[0]
        print(f'Spectrum surveys: {surveys}')
        print(f'Survey segments: {segments}')
        print(f'Survey signals: {signals}')
        print(f'Scan sessions: {sessions}')
        print(f'RF captures: {captures}')
        print(f'Assets discovered: {len(assets)}')
else:
    print('No database yet')
"
```

3. Verify SDR device:
```bash
rtl_test -t 2>&1 | head -5
```

## Output
- File structure
- Previous scan history
- Device status
