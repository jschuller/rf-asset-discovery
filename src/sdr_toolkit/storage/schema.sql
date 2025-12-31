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
-- Spectrum Survey Tables
-- ============================================================================

-- Spectrum survey sessions (multi-segment, resumable)
CREATE TABLE IF NOT EXISTS spectrum_surveys (
    survey_id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'pending',  -- pending, in_progress, paused, completed, failed
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    last_activity_at TIMESTAMP,

    -- Coverage configuration
    start_freq_hz DOUBLE NOT NULL DEFAULT 24000000,
    end_freq_hz DOUBLE NOT NULL DEFAULT 1766000000,

    -- Progress tracking
    total_segments INTEGER NOT NULL DEFAULT 0,
    completed_segments INTEGER NOT NULL DEFAULT 0,
    completion_pct DOUBLE NOT NULL DEFAULT 0.0,

    -- Results
    total_signals_found INTEGER NOT NULL DEFAULT 0,
    unique_frequencies INTEGER NOT NULL DEFAULT 0,

    -- Configuration and results
    config JSON,
    results_summary JSON,

    -- Phase 2: Location/Run Context
    location_name VARCHAR,
    location_gps_lat DOUBLE,
    location_gps_lon DOUBLE,
    environment VARCHAR,
    antenna_type VARCHAR,
    sdr_device VARCHAR,
    gain_setting VARCHAR,
    run_number INTEGER,
    timezone VARCHAR,
    conditions_notes VARCHAR,
    baseline_survey_id VARCHAR
);

-- Survey segments (individual scan blocks within a survey)
CREATE TABLE IF NOT EXISTS survey_segments (
    segment_id VARCHAR PRIMARY KEY,
    survey_id VARCHAR NOT NULL,  -- FK removed due to DuckDB UPDATE bug

    -- Segment definition
    name VARCHAR,
    start_freq_hz DOUBLE NOT NULL,
    end_freq_hz DOUBLE NOT NULL,
    priority INTEGER NOT NULL DEFAULT 3,  -- 1=fine (known bands), 2=medium, 3=coarse (gaps)
    step_hz DOUBLE NOT NULL,
    dwell_time_ms DOUBLE NOT NULL DEFAULT 100,

    -- Status tracking
    status VARCHAR NOT NULL DEFAULT 'pending',  -- pending, in_progress, completed, failed, skipped
    scan_id VARCHAR,  -- Link to scan_sessions when executed

    -- Timing
    scheduled_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    -- Results
    signals_found INTEGER DEFAULT 0,
    noise_floor_db DOUBLE,
    scan_time_seconds DOUBLE,
    error_message VARCHAR
);

-- Auto-discovered signals (promoted to assets based on recurrence)
CREATE TABLE IF NOT EXISTS survey_signals (
    signal_id VARCHAR PRIMARY KEY,
    survey_id VARCHAR NOT NULL,  -- FK removed due to DuckDB UPDATE bug
    segment_id VARCHAR,

    -- Signal characteristics
    frequency_hz DOUBLE NOT NULL,
    power_db DOUBLE NOT NULL,
    bandwidth_hz DOUBLE,

    -- Tracking
    first_seen TIMESTAMP NOT NULL,
    last_seen TIMESTAMP NOT NULL,
    detection_count INTEGER DEFAULT 1,

    -- ServiceNow-style state management
    state VARCHAR NOT NULL DEFAULT 'discovered',  -- discovered, confirmed, dismissed, promoted
    promoted_asset_id VARCHAR,  -- FK removed due to DuckDB UPDATE bug
    notes VARCHAR
);

-- Survey indexes
CREATE INDEX IF NOT EXISTS idx_surveys_status ON spectrum_surveys(status);
CREATE INDEX IF NOT EXISTS idx_surveys_created ON spectrum_surveys(created_at);
CREATE INDEX IF NOT EXISTS idx_segments_survey ON survey_segments(survey_id);
CREATE INDEX IF NOT EXISTS idx_segments_status ON survey_segments(status, priority);
CREATE INDEX IF NOT EXISTS idx_segments_freq ON survey_segments(start_freq_hz);
CREATE INDEX IF NOT EXISTS idx_survey_signals_survey ON survey_signals(survey_id);
CREATE INDEX IF NOT EXISTS idx_survey_signals_freq ON survey_signals(frequency_hz);
CREATE INDEX IF NOT EXISTS idx_survey_signals_state ON survey_signals(state);

-- Phase 2: Reusable location definitions
CREATE TABLE IF NOT EXISTS survey_locations (
    location_id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE,
    description VARCHAR,
    gps_lat DOUBLE,
    gps_lon DOUBLE,
    environment VARCHAR,
    default_antenna VARCHAR,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_survey_at TIMESTAMP,
    total_surveys INTEGER DEFAULT 0
);

-- Phase 2 indexes
CREATE INDEX IF NOT EXISTS idx_surveys_location ON spectrum_surveys(location_name);
CREATE INDEX IF NOT EXISTS idx_locations_name ON survey_locations(name);

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

-- Phase 2: Survey comparison (baseline vs current)
CREATE OR REPLACE VIEW survey_comparison AS
SELECT
    s1.survey_id as current_id,
    s1.name as current_name,
    s1.location_name,
    s1.run_number,
    s1.total_signals_found as current_signals,
    s2.survey_id as baseline_id,
    s2.total_signals_found as baseline_signals,
    s1.total_signals_found - COALESCE(s2.total_signals_found, 0) as signal_delta
FROM spectrum_surveys s1
LEFT JOIN spectrum_surveys s2 ON s1.baseline_survey_id = s2.survey_id;
