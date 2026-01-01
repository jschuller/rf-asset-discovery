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
from rf_asset_discovery.storage import UnifiedDB
from pathlib import Path
db_path = Path('data/unified.duckdb')
if db_path.exists():
    with UnifiedDB(db_path) as db:
        assets = db.get_all_assets()
        surveys = db.conn.execute('SELECT COUNT(*) FROM spectrum_surveys').fetchone()[0]
        segments = db.conn.execute('SELECT COUNT(*) FROM survey_segments').fetchone()[0]
        signals = db.conn.execute('SELECT COUNT(*) FROM signals').fetchone()[0]
        sessions = db.conn.execute('SELECT COUNT(*) FROM scan_sessions').fetchone()[0]
        print(f'Surveys: {surveys}')
        print(f'Segments: {segments}')
        print(f'Signals: {signals}')
        print(f'Scan sessions: {sessions}')
        print(f'Assets promoted: {len(assets)}')
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
