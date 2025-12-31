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
        sessions = db.get_scan_sessions()
        assets = db.get_all_assets()
        print(f'Scan sessions: {len(sessions)}')
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
