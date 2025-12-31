-- Unified Asset Schema for SDR Toolkit
-- DuckDB schema for RF and network asset tracking
-- Version: 1.0.0

-- ============================================================================
-- Core Tables
-- ============================================================================

-- Unified device inventory
CREATE TABLE IF NOT EXISTS assets (
    id VARCHAR PRIMARY KEY,
    name VARCHAR,
    asset_type VARCHAR NOT NULL,  -- rf_only, network_only, correlated, unknown
    first_seen TIMESTAMP NOT NULL,
    last_seen TIMESTAMP NOT NULL,
    correlation_confidence DOUBLE DEFAULT 0.0,

    -- RF attributes
    rf_frequency_hz DOUBLE,
    rf_signal_strength_db DOUBLE,
    rf_bandwidth_hz DOUBLE,
    rf_modulation_type VARCHAR,
    rf_fingerprint_hash VARCHAR,

    -- Network attributes
    net_mac_address VARCHAR,
    net_ip_address VARCHAR,
    net_hostname VARCHAR,
    net_open_ports INTEGER[],
    net_vendor VARCHAR,
    net_os_guess VARCHAR,

    -- Provenance
    discovery_source VARCHAR,
    metadata JSON,

    -- Standards alignment
    cmdb_ci_class VARCHAR,           -- ServiceNow CI class
    cmdb_sys_id VARCHAR,             -- ServiceNow record sys_id
    rf_protocol VARCHAR DEFAULT 'unknown',
    security_posture VARCHAR DEFAULT 'unknown',
    risk_level VARCHAR DEFAULT 'informational',
    purdue_level INTEGER,            -- ISA-95/Purdue Model (0-5, 35 for DMZ)
    device_category VARCHAR,         -- sensor, actuator, gateway, etc.
    ot_protocol VARCHAR,             -- WirelessHART, ISA100.11a, etc.
    ot_criticality VARCHAR           -- essential, important, standard
);

-- RF signal captures
CREATE TABLE IF NOT EXISTS rf_captures (
    capture_id VARCHAR PRIMARY KEY,
    asset_id VARCHAR REFERENCES assets(id),
    scan_id VARCHAR NOT NULL,
    frequency_hz DOUBLE NOT NULL,
    power_db DOUBLE NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    sigmf_path VARCHAR,
    rf_protocol VARCHAR,
    annotations JSON
);

-- Network scan results
CREATE TABLE IF NOT EXISTS network_scans (
    id INTEGER PRIMARY KEY,
    scan_id VARCHAR NOT NULL,
    asset_id VARCHAR REFERENCES assets(id),
    mac_address VARCHAR,
    ip_address VARCHAR,
    timestamp TIMESTAMP NOT NULL,
    ports INTEGER[],
    services JSON
);

-- Scan session metadata
CREATE TABLE IF NOT EXISTS scan_sessions (
    scan_id VARCHAR PRIMARY KEY,
    scan_type VARCHAR NOT NULL,      -- rf_spectrum, network, wifi, iot, combined
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    parameters JSON,
    results_summary JSON
);

-- ============================================================================
-- Indexes for Query Performance
-- ============================================================================

-- Asset lookups
CREATE INDEX IF NOT EXISTS idx_assets_mac ON assets(net_mac_address);
CREATE INDEX IF NOT EXISTS idx_assets_freq ON assets(rf_frequency_hz);
CREATE INDEX IF NOT EXISTS idx_assets_fingerprint ON assets(rf_fingerprint_hash);
CREATE INDEX IF NOT EXISTS idx_assets_last_seen ON assets(last_seen);

-- Standards/compliance lookups
CREATE INDEX IF NOT EXISTS idx_assets_cmdb ON assets(cmdb_sys_id);
CREATE INDEX IF NOT EXISTS idx_assets_protocol ON assets(rf_protocol);
CREATE INDEX IF NOT EXISTS idx_assets_security ON assets(security_posture);
CREATE INDEX IF NOT EXISTS idx_assets_purdue ON assets(purdue_level);
CREATE INDEX IF NOT EXISTS idx_assets_category ON assets(device_category);

-- RF capture lookups
CREATE INDEX IF NOT EXISTS idx_rf_captures_scan ON rf_captures(scan_id);
CREATE INDEX IF NOT EXISTS idx_rf_captures_asset ON rf_captures(asset_id);
CREATE INDEX IF NOT EXISTS idx_rf_captures_freq ON rf_captures(frequency_hz);
CREATE INDEX IF NOT EXISTS idx_rf_captures_protocol ON rf_captures(rf_protocol);
CREATE INDEX IF NOT EXISTS idx_rf_captures_time ON rf_captures(timestamp);

-- Network scan lookups
CREATE INDEX IF NOT EXISTS idx_network_scans_mac ON network_scans(mac_address);
CREATE INDEX IF NOT EXISTS idx_network_scans_scan ON network_scans(scan_id);
CREATE INDEX IF NOT EXISTS idx_network_scans_asset ON network_scans(asset_id);

-- Session lookups
CREATE INDEX IF NOT EXISTS idx_sessions_type ON scan_sessions(scan_type);
CREATE INDEX IF NOT EXISTS idx_sessions_time ON scan_sessions(start_time);

-- ============================================================================
-- Views for Common Queries
-- ============================================================================

-- Active assets (seen in last 24 hours)
CREATE OR REPLACE VIEW active_assets AS
SELECT * FROM assets
WHERE last_seen >= NOW() - INTERVAL '24 hours'
ORDER BY last_seen DESC;

-- RF-only assets without network correlation
CREATE OR REPLACE VIEW rf_only_assets AS
SELECT * FROM assets
WHERE asset_type = 'rf_only'
  AND net_mac_address IS NULL
ORDER BY rf_frequency_hz;

-- Assets by security posture
CREATE OR REPLACE VIEW security_summary AS
SELECT
    security_posture,
    COUNT(*) as count,
    COUNT(CASE WHEN risk_level = 'critical' THEN 1 END) as critical,
    COUNT(CASE WHEN risk_level = 'high' THEN 1 END) as high
FROM assets
GROUP BY security_posture;

-- Protocol distribution
CREATE OR REPLACE VIEW protocol_distribution AS
SELECT
    rf_protocol,
    COUNT(*) as count,
    MIN(first_seen) as earliest,
    MAX(last_seen) as latest
FROM assets
WHERE rf_protocol != 'unknown'
GROUP BY rf_protocol
ORDER BY count DESC;

-- OT assets by Purdue level
CREATE OR REPLACE VIEW ot_assets_by_level AS
SELECT
    purdue_level,
    CASE purdue_level
        WHEN 0 THEN 'Physical Process'
        WHEN 1 THEN 'Basic Control'
        WHEN 2 THEN 'Supervisory'
        WHEN 3 THEN 'Site Operations'
        WHEN 35 THEN 'DMZ'
        WHEN 4 THEN 'Enterprise IT'
        WHEN 5 THEN 'Enterprise Network'
    END as level_name,
    COUNT(*) as count
FROM assets
WHERE purdue_level IS NOT NULL
GROUP BY purdue_level
ORDER BY purdue_level;
