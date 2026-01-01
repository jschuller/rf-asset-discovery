# Medallion Transform

Transform RF discovery data through Bronze → Silver → Gold medallion architecture.

## Usage

```
/transform                  # Show pipeline status
/transform bronze           # Migrate tables to bronze layer
/transform silver           # Transform bronze → silver
/transform gold             # Transform silver → gold
/transform full             # Run complete pipeline
```

## Commands

### Show Status

```bash
uv run sdr-transform status --db data/unified.duckdb
```

Shows current state of medallion schemas and table row counts.

### Bronze Layer (Raw Ingestion)

```bash
# Migrate main schema tables to bronze
uv run sdr-transform bronze --db data/unified.duckdb
```

Copies signals, scan_sessions, survey_segments to bronze schema.

### Silver Layer (Curated/Verified)

```bash
# Transform with defaults
uv run sdr-transform silver --db data/unified.duckdb

# Custom thresholds
uv run sdr-transform silver --min-power 5 --min-detections 2

# Preview without writing
uv run sdr-transform silver --dry-run
```

**Transformations:**
- Filter by power threshold
- Filter by detection count
- Exclude unknown/gap bands
- Add rf_protocol classification

### Gold Layer (Business-Ready)

```bash
# Transform with defaults
uv run sdr-transform gold --db data/unified.duckdb

# High-quality signals only
uv run sdr-transform gold --min-power 15 --known-only

# Preview without writing
uv run sdr-transform gold --dry-run
```

**Enrichments:**
- CMDB CI class assignment
- Purdue level (ISA-95)
- Security posture assessment
- Risk level calculation

### Full Pipeline

```bash
# Run bronze → silver → gold
uv run sdr-transform full --db data/unified.duckdb

# Preview entire pipeline
uv run sdr-transform full --dry-run
```

## Schema Structure

```
rf_discovery (catalog)
├── bronze (raw ingestion)
│   ├── signals              # All raw RF detections
│   ├── scan_sessions        # Operation audit log
│   └── survey_segments      # Segment definitions
│
├── silver (curated/verified)
│   ├── verified_signals     # Filtered, protocol-classified
│   └── band_inventory       # Aggregated by freq_band
│
└── gold (business-ready)
    └── rf_assets            # CMDB-ready assets
```

## Transformation Criteria

| Layer | Filter | Enrichment |
|-------|--------|------------|
| Bronze | None (all data) | None |
| Silver | power >= 0 dB, detection >= 1, known band | rf_protocol |
| Gold | power >= 10 dB, known protocol | CMDB class, Purdue level, risk |

## Cross-Layer Lineage

Query data lineage across layers:

```sql
SELECT
    g.id AS asset_id,
    g.name AS asset_name,
    g.cmdb_ci_class,
    g.risk_level,
    s.rf_protocol,
    b.first_seen AS bronze_first_seen
FROM gold.rf_assets g
JOIN silver.verified_signals s ON g.source_signal_id = s.signal_id
JOIN bronze.signals b ON s.signal_id = b.signal_id;
```

## Environment

```bash
export DYLD_LIBRARY_PATH=/opt/homebrew/lib
```
