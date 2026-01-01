# Results Summary

Final metrics from 12 survey passes of SDR Toolkit data collection.

## Executive Summary

| Metric | Count | Growth |
|--------|------:|-------:|
| Bronze signals | 169,485 | +497% |
| Silver verified | 8,474 | +261% |
| Gold assets | 935 | +648% |
| Surveys completed | 16 | - |

**Collection Period:** 12 survey passes over ~3 hours

## Medallion Layer Breakdown

```
Bronze (169,485)
    ↓ detection_count >= 2, known band
Silver (8,474) — 5% of bronze
    ↓ power_db >= 10, enrichment
Gold (935) — 11% of silver, 0.6% of bronze
```

## Band Distribution (Silver Layer)

| Band | Signals | Avg Power | Max Power |
|------|--------:|----------:|----------:|
| other | 1,902 | +4.1 dB | +29.3 dB |
| ism_900 | 1,521 | +7.7 dB | +29.7 dB |
| uhf_amateur | 728 | +6.4 dB | +21.6 dB |
| aircraft | 613 | +3.2 dB | +9.9 dB |
| vhf_high | 591 | +2.5 dB | +14.5 dB |
| fm_broadcast | 556 | +5.9 dB | +18.0 dB |
| frs_gmrs | 521 | +7.0 dB | +27.0 dB |
| vhf_mid | 428 | +2.6 dB | +13.4 dB |
| cellular_800 | 379 | +4.6 dB | +19.1 dB |
| gps | 288 | +4.5 dB | +17.9 dB |

## Gold Asset Analysis

### By Risk Level

| Risk | Assets | % |
|------|-------:|--:|
| HIGH | 471 | 50.4% |
| LOW | 464 | 49.6% |

**HIGH risk assets:** ISM 900 MHz band (IoT devices at Purdue Level 1)

### By Protocol

| Protocol | Assets | % | Typical Use |
|----------|-------:|--:|-------------|
| FSK | 471 | 50.4% | IoT, LoRa, Zigbee |
| MIXED | 181 | 19.4% | Amateur radio |
| FM_VOICE | 162 | 17.3% | FRS/GMRS radios |
| FM_BROADCAST | 69 | 7.4% | Radio stations |
| SPREAD_SPECTRUM | 52 | 5.6% | GPS, WiFi |

### By CMDB Class

| Class | Assets | Security Context |
|-------|-------:|------------------|
| RF_IOT_DEVICE | 471 | Purdue Level 1 (HIGH risk) |
| RF_AMATEUR | 181 | Purdue Level 4 (LOW risk) |
| RF_TWO_WAY_RADIO | 162 | Purdue Level 4 (LOW risk) |
| RF_BROADCAST_TRANSMITTER | 69 | Purdue Level 5 (LOW risk) |
| RF_NAVIGATION | 52 | Purdue Level 5 (LOW risk) |

## Signal Strength Distribution

| Power Range | Silver Count | Gold Count | % Promoted |
|-------------|-------------:|-----------:|-----------:|
| +25 dB and above | 42 | 42 | 100% |
| +20 to +25 dB | 89 | 89 | 100% |
| +15 to +20 dB | 203 | 203 | 100% |
| +10 to +15 dB | 601 | 601 | 100% |
| +5 to +10 dB | 1,247 | 0 | 0% |
| 0 to +5 dB | 2,892 | 0 | 0% |
| Below 0 dB | 3,400 | 0 | 0% |

**Note:** Gold layer requires power_db >= 10

## Top 10 Strongest Signals

| Frequency | Power | Band | Protocol |
|----------:|------:|------|----------|
| 903.6 MHz | +29.7 dB | ISM 900 | FSK |
| 924.1 MHz | +28.6 dB | ISM 900 | FSK |
| 919.3 MHz | +27.9 dB | ISM 900 | FSK |
| 464.1 MHz | +27.0 dB | FRS/GMRS | FM_VOICE |
| 918.7 MHz | +26.9 dB | ISM 900 | FSK |
| 914.7 MHz | +26.7 dB | ISM 900 | FSK |
| 904.9 MHz | +26.4 dB | ISM 900 | FSK |
| 919.1 MHz | +26.4 dB | ISM 900 | FSK |
| 913.6 MHz | +26.3 dB | ISM 900 | FSK |
| 925.9 MHz | +26.3 dB | ISM 900 | FSK |

**Observation:** ISM 900 MHz dominates strongest signals — likely smart meters, LoRa gateways, or IoT hubs nearby.

## Data Growth Over Passes

| Pass | Bronze | Silver | Gold | Notes |
|-----:|-------:|-------:|-----:|-------|
| 1 | 14,202 | 0 | 0 | Initial scan |
| 2 | 28,401 | 2,345 | 125 | First multi-detections |
| 4 | 56,446 | 3,574 | 265 | Checkpoint 1 |
| 6 | 84,756 | 4,787 | 444 | Checkpoint 2 |
| 8 | 113,006 | 5,993 | 602 | Checkpoint 3 |
| 10 | 141,259 | 7,245 | 770 | Checkpoint 4 |
| 12 | 169,485 | 8,474 | 935 | Final |

**Growth Rate:**
- Bronze: ~14,000 signals per pass
- Silver: ~600 new verified per pass
- Gold: ~80 new assets per pass

## Quality Metrics

| Metric | Value | Target | Status |
|--------|------:|-------:|--------|
| Multi-detection rate | 5.0% | >3% | PASS |
| Gold promotion rate | 11.0% | >10% | PASS |
| Known band coverage | 77.6% | >70% | PASS |
| NULL bandwidth_hz | 100% | <50% | FAIL |
| NULL rf_protocol | 0% | 0% | PASS |

## Storage Statistics

| Component | Size | Notes |
|-----------|-----:|-------|
| DuckDB database | 295 MB | Excludes git (>100MB limit) |
| CSV export | 236 KB | 935 records |
| Git repo | ~50 MB | Code + docs only |

## Recommendations

### Immediate Actions

1. **Review HIGH risk assets** — 471 ISM 900 MHz devices need security assessment
2. **Investigate strongest signals** — 29.7 dB FSK signal at 903.6 MHz is very close

### Future Enhancements

1. **Add bandwidth estimation** — Currently NULL for all signals
2. **GPS tagging** — Enable location-based analysis
3. **Time-of-day surveys** — Identify scheduled transmitters
4. **IoT protocol decoding** — Extend rtl_433 integration

## Files

| File | Records | Format |
|------|--------:|--------|
| `data/unified.duckdb` | 169,485+ | DuckDB |
| `exports/rf_assets.csv` | 935 | CSV |
