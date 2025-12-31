"""Tests for the storage module."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from sdr_toolkit.storage import (
    Asset,
    CMDBCIClass,
    DeviceCategory,
    NetworkScan,
    PurdueLevel,
    RFCapture,
    RFProtocol,
    RiskLevel,
    ScanSession,
    SecurityPosture,
    UnifiedDB,
    apply_nist_categorization,
    assess_security_posture,
    auto_classify_asset,
    calculate_risk_level,
    infer_cmdb_ci_class,
    infer_device_category,
    infer_purdue_level,
)


# ============================================================================
# Model Tests
# ============================================================================


class TestAssetModel:
    """Tests for Asset model."""

    def test_asset_creation_defaults(self) -> None:
        """Asset should have sensible defaults."""
        asset = Asset()
        assert asset.id is not None
        assert asset.asset_type == "unknown"
        assert asset.rf_protocol == RFProtocol.UNKNOWN
        assert asset.security_posture == SecurityPosture.UNKNOWN
        assert asset.risk_level == RiskLevel.INFORMATIONAL
        assert asset.first_seen is not None
        assert asset.last_seen is not None

    def test_asset_with_rf_attributes(self) -> None:
        """Asset with RF attributes."""
        asset = Asset(
            name="FM Station",
            asset_type="rf_only",
            rf_frequency_hz=101.9e6,
            rf_signal_strength_db=-25.0,
            rf_protocol=RFProtocol.FM_BROADCAST,
        )
        assert asset.rf_frequency_hz == 101.9e6
        assert asset.rf_protocol == RFProtocol.FM_BROADCAST

    def test_asset_with_network_attributes(self) -> None:
        """Asset with network attributes."""
        asset = Asset(
            name="IoT Gateway",
            asset_type="network_only",
            net_mac_address="AA:BB:CC:DD:EE:FF",
            net_ip_address="192.168.1.100",
            net_open_ports=[80, 443, 8080],
        )
        assert asset.net_mac_address == "AA:BB:CC:DD:EE:FF"
        assert 443 in asset.net_open_ports

    def test_asset_update_last_seen(self) -> None:
        """update_last_seen should update timestamp."""
        asset = Asset()
        old_time = asset.last_seen
        asset.update_last_seen()
        assert asset.last_seen >= old_time


class TestRFCapture:
    """Tests for RFCapture model."""

    def test_rf_capture_creation(self) -> None:
        """RFCapture should be created with required fields."""
        capture = RFCapture(
            scan_id="scan-123",
            frequency_hz=433.92e6,
            power_db=-30.5,
        )
        assert capture.capture_id is not None
        assert capture.frequency_hz == 433.92e6
        assert capture.scan_id == "scan-123"


class TestScanSession:
    """Tests for ScanSession model."""

    def test_scan_session_creation(self) -> None:
        """ScanSession should track scan metadata."""
        session = ScanSession(
            scan_type="rf_spectrum",
            parameters={"start_freq": 87.5e6, "end_freq": 108e6},
        )
        assert session.scan_id is not None
        assert session.scan_type == "rf_spectrum"
        assert session.end_time is None

    def test_scan_session_end(self) -> None:
        """end_session should set end_time and summary."""
        session = ScanSession(scan_type="rf_spectrum")
        session.end_session({"peaks_found": 10})
        assert session.end_time is not None
        assert session.results_summary["peaks_found"] == 10


# ============================================================================
# Enum Tests
# ============================================================================


class TestEnums:
    """Tests for enum values."""

    def test_rf_protocol_values(self) -> None:
        """RFProtocol should have expected values."""
        assert RFProtocol.WIFI.value == "wifi"
        assert RFProtocol.TPMS.value == "tpms"
        assert RFProtocol.WIRELESSHART.value == "wirelesshart"

    def test_cmdb_ci_class_values(self) -> None:
        """CMDBCIClass should map to ServiceNow classes."""
        assert CMDBCIClass.WAP.value == "cmdb_ci_wap"
        assert CMDBCIClass.IOT_SENSOR.value == "cmdb_ci_iot_sensor"
        assert CMDBCIClass.OT_DEVICE.value == "cmdb_ci_ot_device"

    def test_purdue_level_values(self) -> None:
        """PurdueLevel should have correct numeric values."""
        assert PurdueLevel.PHYSICAL_PROCESS.value == 0
        assert PurdueLevel.BASIC_CONTROL.value == 1
        assert PurdueLevel.DMZ.value == 35


# ============================================================================
# Classification Tests
# ============================================================================


class TestCMDBClassification:
    """Tests for CMDB CI class inference."""

    def test_wifi_gateway_to_wap(self) -> None:
        """WiFi gateway should map to WAP."""
        asset = Asset(
            rf_protocol=RFProtocol.WIFI,
            device_category=DeviceCategory.GATEWAY,
        )
        assert infer_cmdb_ci_class(asset) == CMDBCIClass.WAP

    def test_zigbee_sensor(self) -> None:
        """Zigbee sensor should map to IOT_SENSOR."""
        asset = Asset(
            rf_protocol=RFProtocol.ZIGBEE,
            device_category=DeviceCategory.SENSOR,
        )
        assert infer_cmdb_ci_class(asset) == CMDBCIClass.IOT_SENSOR

    def test_wirelesshart_device(self) -> None:
        """WirelessHART should map to OT_DEVICE."""
        asset = Asset(rf_protocol=RFProtocol.WIRELESSHART)
        assert infer_cmdb_ci_class(asset) == CMDBCIClass.OT_DEVICE

    def test_fm_broadcast_to_rf_emitter(self) -> None:
        """FM broadcast should map to RF_EMITTER."""
        asset = Asset(rf_protocol=RFProtocol.FM_BROADCAST)
        assert infer_cmdb_ci_class(asset) == CMDBCIClass.RF_EMITTER


class TestPurdueLevel:
    """Tests for Purdue level inference."""

    def test_wirelesshart_sensor_level_0(self) -> None:
        """WirelessHART sensor should be Level 0."""
        asset = Asset(
            rf_protocol=RFProtocol.WIRELESSHART,
            device_category=DeviceCategory.SENSOR,
        )
        assert infer_purdue_level(asset) == PurdueLevel.PHYSICAL_PROCESS

    def test_industrial_gateway_level_1(self) -> None:
        """Industrial gateway should be Level 1."""
        asset = Asset(
            rf_protocol=RFProtocol.ISA100,
            device_category=DeviceCategory.GATEWAY,
        )
        assert infer_purdue_level(asset) == PurdueLevel.BASIC_CONTROL

    def test_bluetooth_level_4(self) -> None:
        """Bluetooth should be enterprise level."""
        asset = Asset(rf_protocol=RFProtocol.BLUETOOTH)
        assert infer_purdue_level(asset) == PurdueLevel.ENTERPRISE_IT

    def test_unknown_protocol_no_level(self) -> None:
        """Unknown protocol should have no Purdue level."""
        asset = Asset(rf_protocol=RFProtocol.UNKNOWN)
        assert infer_purdue_level(asset) is None


class TestDeviceCategory:
    """Tests for device category inference."""

    def test_tpms_is_sensor(self) -> None:
        """TPMS should be classified as sensor."""
        assert infer_device_category(RFProtocol.TPMS) == DeviceCategory.SENSOR

    def test_weather_station_is_sensor(self) -> None:
        """Weather station should be sensor."""
        assert infer_device_category(RFProtocol.WEATHER_STATION) == DeviceCategory.SENSOR

    def test_ble_is_endpoint(self) -> None:
        """BLE should be endpoint."""
        assert infer_device_category(RFProtocol.BLE) == DeviceCategory.ENDPOINT


class TestSecurityPosture:
    """Tests for security posture assessment."""

    def test_cmdb_synced_is_verified(self) -> None:
        """CMDB synced asset should be verified."""
        asset = Asset(cmdb_sys_id="abc123")
        assert assess_security_posture(asset) == SecurityPosture.VERIFIED

    def test_known_mac_is_known(self) -> None:
        """Asset with known MAC should be known."""
        asset = Asset(net_mac_address="AA:BB:CC:DD:EE:FF")
        known_macs = {"aa:bb:cc:dd:ee:ff"}
        assert assess_security_posture(asset, known_macs) == SecurityPosture.KNOWN

    def test_unknown_correlated_is_suspicious(self) -> None:
        """Unknown protocol with network = suspicious."""
        asset = Asset(
            rf_protocol=RFProtocol.UNKNOWN,
            net_ip_address="192.168.1.100",
            asset_type="correlated",
        )
        assert assess_security_posture(asset) == SecurityPosture.SUSPICIOUS


class TestRiskLevel:
    """Tests for risk level calculation."""

    def test_unauthorized_is_critical(self) -> None:
        """Unauthorized device should be critical risk."""
        asset = Asset(security_posture=SecurityPosture.UNAUTHORIZED)
        assert calculate_risk_level(asset) == RiskLevel.CRITICAL

    def test_suspicious_is_high(self) -> None:
        """Suspicious device should be high risk."""
        asset = Asset(security_posture=SecurityPosture.SUSPICIOUS)
        assert calculate_risk_level(asset) == RiskLevel.HIGH

    def test_consumer_iot_is_low(self) -> None:
        """Consumer IoT should be low risk."""
        asset = Asset(rf_protocol=RFProtocol.TPMS)
        assert calculate_risk_level(asset) == RiskLevel.LOW


class TestAutoClassify:
    """Tests for auto_classify_asset."""

    def test_auto_classify_sets_all_fields(self) -> None:
        """auto_classify should set all classification fields."""
        asset = Asset(
            rf_protocol=RFProtocol.ZIGBEE,
            rf_frequency_hz=2.4e9,
        )
        classified = auto_classify_asset(asset)

        assert classified.device_category is not None
        assert classified.cmdb_ci_class is not None
        assert classified.risk_level is not None


class TestNISTCategorization:
    """Tests for NIST categorization."""

    def test_nist_with_mac(self) -> None:
        """Asset with MAC should have device_identification."""
        asset = Asset(net_mac_address="AA:BB:CC:DD:EE:FF")
        categories = apply_nist_categorization(asset)
        assert categories["device_identification"] is True

    def test_nist_with_ports(self) -> None:
        """Asset with ports should have logical_access."""
        asset = Asset(net_open_ports=[80, 443])
        categories = apply_nist_categorization(asset)
        assert categories["logical_access"] is True


# ============================================================================
# Database Tests
# ============================================================================


class TestUnifiedDB:
    """Tests for UnifiedDB operations."""

    @pytest.fixture
    def db(self) -> UnifiedDB:
        """Create in-memory database for testing."""
        db = UnifiedDB(":memory:")
        db.connect()
        yield db
        db.close()

    def test_db_connect_initializes_schema(self, db: UnifiedDB) -> None:
        """Database should initialize schema on connect."""
        # Check tables exist
        result = db.query("SELECT name FROM sqlite_master WHERE type='table'")
        table_names = {row["name"] for row in result}
        assert "assets" in table_names
        assert "rf_captures" in table_names

    def test_insert_and_get_asset(self, db: UnifiedDB) -> None:
        """Should insert and retrieve asset."""
        asset = Asset(
            name="Test Device",
            asset_type="rf_only",
            rf_frequency_hz=101.9e6,
        )
        asset_id = db.insert_asset(asset)

        retrieved = db.get_asset(asset_id)
        assert retrieved is not None
        assert retrieved.name == "Test Device"
        assert retrieved.rf_frequency_hz == 101.9e6

    def test_update_asset(self, db: UnifiedDB) -> None:
        """Should update existing asset."""
        asset = Asset(name="Original Name", asset_type="rf_only")
        asset_id = db.insert_asset(asset)

        asset.name = "Updated Name"
        asset.rf_signal_strength_db = -30.0
        db.update_asset(asset)

        retrieved = db.get_asset(asset_id)
        assert retrieved is not None
        assert retrieved.name == "Updated Name"
        assert retrieved.rf_signal_strength_db == -30.0

    def test_find_by_frequency(self, db: UnifiedDB) -> None:
        """Should find assets by frequency."""
        # Insert assets at different frequencies
        db.insert_asset(Asset(rf_frequency_hz=101.9e6, asset_type="rf_only"))
        db.insert_asset(Asset(rf_frequency_hz=102.1e6, asset_type="rf_only"))
        db.insert_asset(Asset(rf_frequency_hz=200.0e6, asset_type="rf_only"))

        # Find near 102 MHz
        results = db.find_assets_by_frequency(102e6, tolerance_hz=500_000)
        assert len(results) == 2

    def test_find_by_mac(self, db: UnifiedDB) -> None:
        """Should find assets by MAC address."""
        db.insert_asset(
            Asset(
                net_mac_address="AA:BB:CC:DD:EE:FF",
                asset_type="network_only",
            )
        )

        # Case insensitive search
        results = db.find_assets_by_mac("aa:bb:cc:dd:ee:ff")
        assert len(results) == 1

    def test_find_by_protocol(self, db: UnifiedDB) -> None:
        """Should find assets by protocol."""
        db.insert_asset(Asset(rf_protocol=RFProtocol.WIFI, asset_type="rf_only"))
        db.insert_asset(Asset(rf_protocol=RFProtocol.WIFI, asset_type="rf_only"))
        db.insert_asset(Asset(rf_protocol=RFProtocol.TPMS, asset_type="rf_only"))

        results = db.find_assets_by_protocol(RFProtocol.WIFI)
        assert len(results) == 2

    def test_record_rf_capture(self, db: UnifiedDB) -> None:
        """Should record RF capture."""
        scan_id = db.start_scan_session("rf_spectrum")
        capture = RFCapture(
            scan_id=scan_id,
            frequency_hz=433.92e6,
            power_db=-35.0,
            rf_protocol=RFProtocol.TPMS,
        )
        capture_id = db.record_rf_capture(capture)

        captures = db.get_captures_by_scan(scan_id)
        assert len(captures) == 1
        assert captures[0].capture_id == capture_id

    def test_scan_session_lifecycle(self, db: UnifiedDB) -> None:
        """Should manage scan session lifecycle."""
        scan_id = db.start_scan_session(
            "rf_spectrum",
            parameters={"start_freq": 87.5e6},
        )

        session = db.get_scan_session(scan_id)
        assert session is not None
        assert session.end_time is None

        db.end_scan_session(scan_id, {"peaks_found": 5})

        session = db.get_scan_session(scan_id)
        assert session is not None
        assert session.end_time is not None
        assert session.results_summary["peaks_found"] == 5

    def test_get_statistics(self, db: UnifiedDB) -> None:
        """Should return database statistics."""
        db.insert_asset(Asset(rf_protocol=RFProtocol.WIFI, asset_type="rf_only"))
        db.insert_asset(Asset(rf_protocol=RFProtocol.WIFI, asset_type="rf_only"))

        stats = db.get_statistics()
        assert stats["assets_count"] == 2
        assert "wifi" in stats["protocol_distribution"]

    def test_export_to_parquet(self, db: UnifiedDB, tmp_path: Path) -> None:
        """Should export tables to Parquet."""
        db.insert_asset(Asset(name="Test", asset_type="rf_only"))

        exported = db.export_to_parquet(tmp_path, tables=["assets"])
        assert "assets" in exported
        assert exported["assets"].exists()


class TestUnifiedDBContextManager:
    """Tests for UnifiedDB context manager."""

    def test_context_manager_connects(self) -> None:
        """Context manager should connect and close."""
        with UnifiedDB(":memory:") as db:
            assert db._conn is not None
            db.insert_asset(Asset(name="Test", asset_type="rf_only"))

    def test_connection_required_error(self) -> None:
        """Should raise error when not connected."""
        db = UnifiedDB(":memory:")
        with pytest.raises(RuntimeError, match="not connected"):
            db.insert_asset(Asset())
