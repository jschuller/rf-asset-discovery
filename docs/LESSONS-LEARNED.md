# Lessons Learned

Project retrospective from RF Asset Discovery development.

## What Worked Well

| Pattern | Why It Worked | Reuse Potential |
|---------|---------------|-----------------|
| **Ralph Loop automation** | Autonomous survey completion, no babysitting. Claude sees previous work in files. | High - any iterative task |
| **Detection count deduplication** | Separates persistent signals from noise. Multiple passes = confidence. | High - any noisy data |
| **SQL CASE from Python dict** | Single source of truth for classification. Generate SQL, don't duplicate. | High - any classification |
| **Checkpoint commits** | Recovery points during long operations. Git as audit trail. | High - long-running tasks |
| **Context manager for SDR** | Prevents device lockups. `with SDRDevice() as sdr:` | High - any hardware/resource |
| **DuckDB medallion schemas** | Clean separation, lineage queries. `bronze.signals` vs `gold.assets` | High - any data project |
| **Skills over raw commands** | `/survey` easier than remembering CLI flags | High - any CLI project |

## What Didn't Work / Gotchas

| Issue | Root Cause | Solution | Prevention |
|-------|-----------|----------|------------|
| **Database >100MB** | GitHub file size limit | Export CSV, exclude DB from git | Check file sizes before commit |
| **IoT scan no results** | No active transmitters nearby | Expected; location-dependent | Document as normal behavior |
| **SDR device locked** | rtl_433 still running | `pkill -f rtl_433` before surveys | Add device check to pre-flight |
| **PLL not locked** | RTL-SDR tuner limitation at edges | Ignore warning, data still valid | Document in troubleshooting |
| **zsh for-loop syntax** | `DYLD_LIBRARY_PATH=x cmd` in loop fails | `export` first, then loop | Test shell snippets |
| **Ralph loop timeout** | Context exhaustion | Use completion promises | Add `<promise>DONE</promise>` |

## Performance Observations

| Metric | Value | Implication |
|--------|-------|-------------|
| Segments per survey | 29 | Full RTL-SDR spectrum coverage |
| Time per survey pass | ~12 min | 29 segments × ~25s average |
| Signal growth per pass | ~14K | Consistent, predictable |
| Multi-detection rate | 5% | After 12 passes (8.4K of 169K) |
| Gold promotion rate | 11% | Of silver signals (935 of 8.4K) |
| Database size growth | ~25MB/pass | Plan storage accordingly |

## Key Thresholds Discovered

```
detection_count >= 2  → Silver (verified signal)
detection_count >= 3  → Auto-promote candidate
power_db >= 0         → Above noise floor
power_db >= 10        → Gold asset (strong signal)
power_db >= 25        → High-priority (likely nearby)
```

## Ralph Loop Lessons

### What Works

```bash
# Clear completion promise
/ralph-loop "Complete task. Output <promise>DONE</promise> when finished."

# Specific iteration limit
--max-iterations 35

# Check previous work in files
git log --oneline -5
cat data/state.json
```

### What Doesn't Work

```bash
# Vague completion criteria
/ralph-loop "Work on this until it's good"  # Never exits

# No state persistence
# Claude forgets between iterations without file-based state

# Too many iterations
--max-iterations 1000  # Context exhaustion
```

### Best Practices

1. **Use completion promises** - `<promise>TASK COMPLETE</promise>`
2. **Track state in files** - Git, JSON, database
3. **Limit iterations** - 20-50 for most tasks
4. **Be specific** - "Run segment, check 100%, output promise"

## Classification Design Lessons

### Single Source of Truth

```python
# Good: Dictionary drives everything
BAND_MAP = {
    "fm_broadcast": BandInfo(protocol="FM", cmdb="RF_BROADCAST", purdue=5),
}

# Generate SQL from dict
PROTOCOL_SQL = generate_case_sql(BAND_MAP, "freq_band", "protocol")

# Bad: Duplicate logic
# Python function + separate SQL CASE + separate CLI logic
```

### Standards Alignment

| Standard | Used For | Value |
|----------|----------|-------|
| ServiceNow CMDB | CI class mapping | Enterprise integration |
| ISA-95/Purdue | OT level assignment | Security context |
| NIST CSF | Risk assessment | Compliance alignment |

## Data Quality Lessons

### What to Capture

| Field | Importance | Lesson |
|-------|------------|--------|
| detection_count | Critical | Only way to distinguish signal from noise |
| power_db | Critical | Quality gate for gold layer |
| freq_band | High | Enables protocol classification |
| first_seen/last_seen | Medium | Temporal analysis |
| bandwidth_hz | Low | Currently NULL; future enhancement |

### What to Skip

| Field | Why Skip |
|-------|----------|
| annotations | Never populated; remove from schema |
| raw IQ samples | Too large; sample selectively |
| microsecond timestamps | Overkill for survey use case |

## Git Strategy Lessons

### Large Files

```bash
# Problem: Database exceeds GitHub 100MB limit
git push origin main
# error: File data/unified.duckdb is 295.51 MB

# Solution: Export data, exclude database
echo "/data/" >> .gitignore
git add exports/rf_assets.csv
git push origin main
```

### Checkpoint Commits

```bash
# Commit after every 2 survey passes
git add -A && git commit -m "Data: 4 passes - checkpoint 1"

# Benefits:
# - Recovery point if something fails
# - Audit trail of data growth
# - Can bisect to find issues
```

## Architecture Lessons

### DuckDB Schemas

```sql
-- Good: Separate schemas for layers
CREATE SCHEMA bronze;
CREATE SCHEMA silver;
CREATE SCHEMA gold;

-- Access pattern
SELECT * FROM bronze.signals;
SELECT * FROM silver.verified_signals;
SELECT * FROM gold.rf_assets;

-- Bad: Prefixed table names in same schema
SELECT * FROM raw_signals;
SELECT * FROM curated_signals;
SELECT * FROM asset_signals;
```

### Transformation Idempotency

```python
# Good: Drop and recreate
self.conn.execute("DROP TABLE IF EXISTS silver.verified_signals")
self.conn.execute(f"CREATE TABLE silver.verified_signals AS {sql}")

# Bad: Append without checking
self.conn.execute(f"INSERT INTO silver.verified_signals {sql}")
# Duplicates on re-run
```

## CLI Design Lessons

### Subcommands > Flags

```bash
# Good: Clear subcommands
rfad-transform status
rfad-transform bronze
rfad-transform silver
rfad-transform gold
rfad-transform full

# Bad: Confusing flags
rfad-transform --mode=status --layer=all
```

### Consistent Patterns

```bash
# All commands follow same pattern
rfad-survey create --name "Pass 1" --full
rfad-survey status <id>
rfad-survey next <id>
rfad-survey resume <id>
```

## Testing Lessons

### Environment Variable

```bash
# RTL-SDR requires library path on macOS
DYLD_LIBRARY_PATH=/opt/homebrew/lib pytest tests/ -v

# Add to shell profile or test runner
export DYLD_LIBRARY_PATH=/opt/homebrew/lib
```

### Mock Hardware

```python
# Tests should work without physical device
@pytest.fixture
def mock_sdr():
    with patch('rtlsdr.RtlSdr') as mock:
        yield mock
```

## Documentation Lessons

### What to Document

| Priority | Content | Location |
|----------|---------|----------|
| High | Setup commands | CLAUDE.md |
| High | Common gotchas | LESSONS-LEARNED.md |
| High | Architecture overview | ARCHITECTURE.md |
| Medium | CLI reference | README.md |
| Medium | Troubleshooting | troubleshooting.md |
| Low | API reference | Docstrings |

### Information Density

```markdown
# Good: Dense, scannable
| Command | Purpose |
|---------|---------|
| `rfad-scan --fm` | FM band |
| `rfad-survey create` | New survey |

# Bad: Verbose prose
The rfad-scan command is used for scanning the radio spectrum.
When you want to scan the FM band, you should use the --fm flag.
```

## Summary

### Top 5 Patterns to Reuse

1. **Medallion Architecture** - Bronze → Silver → Gold with clear quality gates
2. **Ralph Loop Automation** - Autonomous task completion with promises
3. **Classification Registry** - Python dict → SQL CASE generation
4. **Context Managers** - Resource cleanup for hardware/connections
5. **Checkpoint Commits** - Recovery points for long operations

### Top 5 Gotchas to Avoid

1. **Large files in git** - Export data, not databases
2. **Device locking** - Kill competing processes
3. **Shell syntax differences** - Test bash vs zsh
4. **Vague completion criteria** - Use explicit promises
5. **Duplicate classification logic** - Single source of truth
