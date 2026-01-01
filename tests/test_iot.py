"""Tests for IoT protocol discovery module."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from rf_asset_discovery.decoders.iot import (
    DeviceRegistry,
    IoTDevice,
    IoTPacket,
    IoTProtocolType,
    classify_protocol,
    extract_device_id,
    map_to_rf_protocol,
)
from rf_asset_discovery.decoders.iot.classifier import extract_telemetry
from rf_asset_discovery.storage.models import RFProtocol


# ============================================================================
# Protocol Classification Tests
# ============================================================================


class TestProtocolClassification:
    """Tests for protocol classification from model strings."""

    @pytest.mark.parametrize(
        "model,expected",
        [
            ("Schrader-EG53MA4", IoTProtocolType.TPMS),
            ("Toyota-TPMS", IoTProtocolType.TPMS),
            ("Ford-TPMS", IoTProtocolType.TPMS),
            ("BMW-TPMS", IoTProtocolType.TPMS),
            ("Acurite-Tower", IoTProtocolType.WEATHER_STATION),
            ("Acurite-986", IoTProtocolType.WEATHER_STATION),
            ("Oregon-THN132N", IoTProtocolType.WEATHER_STATION),
            ("Fineoffset-WHx080", IoTProtocolType.WEATHER_STATION),
            ("WH2", IoTProtocolType.WEATHER_STATION),
            ("LaCrosse-TX141", IoTProtocolType.WEATHER_STATION),
            ("Ambient-Weather", IoTProtocolType.WEATHER_STATION),
            ("ThermoPro-TX2", IoTProtocolType.TEMPERATURE_SENSOR),
            ("Inkbird-ITH", IoTProtocolType.TEMPERATURE_SENSOR),
            ("Generic-Remote", IoTProtocolType.REMOTE_CONTROL),
            ("Garage-Remote", IoTProtocolType.REMOTE_CONTROL),
            ("Honeywell-Door", IoTProtocolType.DOOR_SENSOR),
            ("Visonic-Contact", IoTProtocolType.DOOR_SENSOR),
            ("PIR-Motion", IoTProtocolType.MOTION_SENSOR),
            ("Smoke-Alarm", IoTProtocolType.SMOKE_DETECTOR),
            ("Water-Leak", IoTProtocolType.WATER_LEAK),
            ("Generic-OOK", IoTProtocolType.GENERIC_OOK),
            ("UnknownDevice", IoTProtocolType.UNKNOWN),
        ],
    )
    def test_classify_protocol(self, model: str, expected: IoTProtocolType) -> None:
        """Protocol classification should match expected types."""
        result = classify_protocol(model)
        assert result == expected

    def test_classify_protocol_case_insensitive(self) -> None:
        """Classification should be case-insensitive."""
        assert classify_protocol("ACURITE-TOWER") == IoTProtocolType.WEATHER_STATION
        assert classify_protocol("acurite-tower") == IoTProtocolType.WEATHER_STATION
        assert classify_protocol("AcuRite-Tower") == IoTProtocolType.WEATHER_STATION


class TestDeviceIdExtraction:
    """Tests for device ID extraction from packets."""

    def test_extract_id_field(self) -> None:
        """Should extract from 'id' field."""
        packet = {"model": "Acurite-Tower", "id": 12345}
        result = extract_device_id(packet)
        assert result == "Acurite-Tower_12345"

    def test_extract_sensor_id_field(self) -> None:
        """Should fall back to 'sensor_id' field."""
        packet = {"model": "Oregon-THN132N", "sensor_id": 99}
        result = extract_device_id(packet)
        assert result == "Oregon-THN132N_99"

    def test_extract_with_channel(self) -> None:
        """Should include channel in ID when present."""
        packet = {"model": "Acurite-Tower", "id": 12345, "channel": "A"}
        result = extract_device_id(packet)
        assert result == "Acurite-Tower_12345_chA"

    def test_extract_channel_only(self) -> None:
        """Should use channel when no id available."""
        packet = {"model": "Generic-Remote", "channel": 3}
        result = extract_device_id(packet)
        assert result == "Generic-Remote_ch3"

    def test_extract_hash_fallback(self) -> None:
        """Should hash stable fields as fallback."""
        packet = {"model": "Unknown", "subtype": "A", "type": "sensor"}
        result = extract_device_id(packet)
        assert result.startswith("Unknown_")
        assert len(result) > len("Unknown_")


class TestRFProtocolMapping:
    """Tests for mapping IoT types to RFProtocol."""

    def test_tpms_mapping(self) -> None:
        """TPMS should map to TPMS."""
        assert map_to_rf_protocol(IoTProtocolType.TPMS) == RFProtocol.TPMS

    def test_weather_station_mapping(self) -> None:
        """Weather station should map to WEATHER_STATION."""
        assert map_to_rf_protocol(IoTProtocolType.WEATHER_STATION) == RFProtocol.WEATHER_STATION

    def test_temperature_sensor_mapping(self) -> None:
        """Temperature sensor should map to WEATHER_STATION."""
        assert map_to_rf_protocol(IoTProtocolType.TEMPERATURE_SENSOR) == RFProtocol.WEATHER_STATION

    def test_unknown_mapping(self) -> None:
        """Unknown types should map to UNKNOWN."""
        assert map_to_rf_protocol(IoTProtocolType.UNKNOWN) == RFProtocol.UNKNOWN
        assert map_to_rf_protocol(IoTProtocolType.DOOR_SENSOR) == RFProtocol.UNKNOWN


class TestTelemetryExtraction:
    """Tests for telemetry value extraction."""

    def test_extract_temperature_celsius(self) -> None:
        """Should extract temperature in Celsius."""
        packet = {"temperature_C": 22.5}
        result = extract_telemetry(packet)
        assert result["temperature_c"] == 22.5

    def test_extract_temperature_fahrenheit(self) -> None:
        """Should convert Fahrenheit to Celsius."""
        packet = {"temperature_F": 72.5}
        result = extract_telemetry(packet)
        assert abs(result["temperature_c"] - 22.5) < 0.1

    def test_extract_humidity(self) -> None:
        """Should extract humidity."""
        packet = {"humidity": 65}
        result = extract_telemetry(packet)
        assert result["humidity_pct"] == 65

    def test_extract_pressure_kpa(self) -> None:
        """Should extract pressure in kPa."""
        packet = {"pressure_kPa": 230}
        result = extract_telemetry(packet)
        assert result["pressure_kpa"] == 230

    def test_extract_battery_ok(self) -> None:
        """Should extract battery status."""
        packet = {"battery_ok": 1}
        result = extract_telemetry(packet)
        assert result["battery_ok"] is True

    def test_extract_battery_low(self) -> None:
        """Should handle battery_low field (inverted)."""
        packet = {"battery_low": 1}
        result = extract_telemetry(packet)
        assert result["battery_ok"] is False

    def test_extract_channel(self) -> None:
        """Should extract channel."""
        packet = {"channel": 2}
        result = extract_telemetry(packet)
        assert result["channel"] == 2


# ============================================================================
# IoTPacket Tests
# ============================================================================


class TestIoTPacket:
    """Tests for IoTPacket dataclass."""

    @pytest.fixture
    def sample_packet(self) -> IoTPacket:
        """Create sample packet for testing."""
        return IoTPacket(
            raw_json={"model": "Acurite-Tower", "id": 12345},
            timestamp=datetime.now(),
            model="Acurite-Tower",
            device_id="Acurite-Tower_12345",
            protocol_type=IoTProtocolType.WEATHER_STATION,
            frequency_mhz=433.92,
            temperature_c=22.5,
            humidity_pct=65,
        )

    def test_packet_to_dict(self, sample_packet: IoTPacket) -> None:
        """to_dict should include all fields."""
        result = sample_packet.to_dict()
        assert result["model"] == "Acurite-Tower"
        assert result["device_id"] == "Acurite-Tower_12345"
        assert result["protocol_type"] == "weather_station"
        assert result["temperature_c"] == 22.5

    def test_packet_to_signal(self, sample_packet: IoTPacket) -> None:
        """to_signal should create valid Signal."""
        signal = sample_packet.to_signal(survey_id="survey-123", scan_id="scan-123")
        assert signal.survey_id == "survey-123"
        assert signal.scan_id == "scan-123"
        assert signal.frequency_hz == 433.92e6
        assert signal.rf_protocol == RFProtocol.WEATHER_STATION
        assert signal.annotations["iot_model"] == "Acurite-Tower"


# ============================================================================
# IoTDevice Tests
# ============================================================================


class TestIoTDevice:
    """Tests for IoTDevice dataclass."""

    @pytest.fixture
    def sample_device(self) -> IoTDevice:
        """Create sample device for testing."""
        return IoTDevice(
            device_id="Acurite-Tower_12345",
            model="Acurite-Tower",
            protocol_type=IoTProtocolType.WEATHER_STATION,
            first_seen=datetime.now(),
            last_seen=datetime.now(),
        )

    def test_device_from_packet(self) -> None:
        """from_packet should create device from packet."""
        packet = IoTPacket(
            raw_json={},
            timestamp=datetime.now(),
            model="Acurite-986",
            device_id="Acurite-986_999",
            protocol_type=IoTProtocolType.WEATHER_STATION,
            temperature_c=20.0,
        )
        device = IoTDevice.from_packet(packet)
        assert device.device_id == "Acurite-986_999"
        assert device.model == "Acurite-986"
        assert device.packet_count == 1
        assert device.last_temperature_c == 20.0

    def test_device_update_from_packet(self, sample_device: IoTDevice) -> None:
        """update_from_packet should update device state."""
        old_last_seen = sample_device.last_seen

        packet = IoTPacket(
            raw_json={},
            timestamp=datetime.now() + timedelta(seconds=10),
            model="Acurite-Tower",
            device_id="Acurite-Tower_12345",
            protocol_type=IoTProtocolType.WEATHER_STATION,
            temperature_c=25.0,
            channel=2,
        )
        sample_device.update_from_packet(packet)

        assert sample_device.packet_count == 1
        assert sample_device.last_seen > old_last_seen
        assert sample_device.last_temperature_c == 25.0
        assert 2 in sample_device.channels_seen

    def test_device_to_asset(self, sample_device: IoTDevice) -> None:
        """to_asset should create valid Asset."""
        asset = sample_device.to_asset()
        assert asset.name == "Acurite-Tower (Acurite-Tower_12345)"
        assert asset.asset_type == "rf_only"
        assert asset.rf_protocol == RFProtocol.WEATHER_STATION
        assert asset.discovery_source == "rtl_433"

    def test_device_to_dict(self, sample_device: IoTDevice) -> None:
        """to_dict should serialize device."""
        result = sample_device.to_dict()
        assert result["device_id"] == "Acurite-Tower_12345"
        assert result["protocol_type"] == "weather_station"


# ============================================================================
# DeviceRegistry Tests
# ============================================================================


class TestDeviceRegistry:
    """Tests for DeviceRegistry."""

    @pytest.fixture
    def registry(self) -> DeviceRegistry:
        """Create empty registry for testing."""
        return DeviceRegistry()

    @pytest.fixture
    def sample_packet(self) -> IoTPacket:
        """Create sample packet."""
        return IoTPacket(
            raw_json={},
            timestamp=datetime.now(),
            model="Acurite-Tower",
            device_id="Acurite-Tower_12345",
            protocol_type=IoTProtocolType.WEATHER_STATION,
        )

    def test_process_packet_creates_device(
        self, registry: DeviceRegistry, sample_packet: IoTPacket
    ) -> None:
        """process_packet should create new device."""
        device = registry.process_packet(sample_packet)
        assert device.device_id == "Acurite-Tower_12345"
        assert registry.device_count == 1
        assert registry.packet_count == 1

    def test_process_packet_updates_existing(
        self, registry: DeviceRegistry, sample_packet: IoTPacket
    ) -> None:
        """process_packet should update existing device."""
        registry.process_packet(sample_packet)
        registry.process_packet(sample_packet)

        assert registry.device_count == 1
        assert registry.packet_count == 2

        device = registry.get_device("Acurite-Tower_12345")
        assert device is not None
        assert device.packet_count == 2

    def test_get_all_devices(self, registry: DeviceRegistry) -> None:
        """get_all_devices should return sorted list."""
        for i in range(3):
            packet = IoTPacket(
                raw_json={},
                timestamp=datetime.now() + timedelta(seconds=i),
                model=f"Device-{i}",
                device_id=f"Device-{i}_id",
                protocol_type=IoTProtocolType.UNKNOWN,
            )
            registry.process_packet(packet)

        devices = registry.get_all_devices()
        assert len(devices) == 3
        # Should be sorted by last_seen descending
        assert devices[0].device_id == "Device-2_id"

    def test_get_devices_by_protocol(self, registry: DeviceRegistry) -> None:
        """get_devices_by_protocol should filter correctly."""
        for proto, count in [(IoTProtocolType.TPMS, 2), (IoTProtocolType.WEATHER_STATION, 3)]:
            for i in range(count):
                packet = IoTPacket(
                    raw_json={},
                    timestamp=datetime.now(),
                    model=f"{proto.value}-{i}",
                    device_id=f"{proto.value}-{i}_id",
                    protocol_type=proto,
                )
                registry.process_packet(packet)

        tpms_devices = registry.get_devices_by_protocol(IoTProtocolType.TPMS)
        weather_devices = registry.get_devices_by_protocol(IoTProtocolType.WEATHER_STATION)

        assert len(tpms_devices) == 2
        assert len(weather_devices) == 3

    def test_get_stats(self, registry: DeviceRegistry, sample_packet: IoTPacket) -> None:
        """get_stats should return correct counts."""
        registry.process_packet(sample_packet)
        registry.process_packet(sample_packet)

        stats = registry.get_stats()
        assert stats["total_devices"] == 1
        assert stats["total_packets"] == 2
        assert "weather_station" in stats["devices_by_protocol"]

    def test_to_json_and_from_json(
        self, registry: DeviceRegistry, sample_packet: IoTPacket, tmp_path: Path
    ) -> None:
        """Registry should serialize and deserialize correctly."""
        registry.process_packet(sample_packet)
        registry.process_packet(sample_packet)

        output_path = tmp_path / "registry.json"
        registry.to_json(output_path)

        loaded = DeviceRegistry.from_json(output_path)
        assert loaded.device_count == 1
        assert loaded.packet_count == 2

        device = loaded.get_device("Acurite-Tower_12345")
        assert device is not None
        assert device.packet_count == 2

    def test_clear(self, registry: DeviceRegistry, sample_packet: IoTPacket) -> None:
        """clear should remove all devices."""
        registry.process_packet(sample_packet)
        assert registry.device_count == 1

        registry.clear()
        assert registry.device_count == 0
        assert registry.packet_count == 0


# ============================================================================
# RTL433 Wrapper Tests
# ============================================================================


class TestRTL433Wrapper:
    """Tests for RTL433Decoder (without actual hardware)."""

    def test_check_rtl433_available(self) -> None:
        """check_rtl433_available should not crash."""
        from rf_asset_discovery.decoders.iot import check_rtl433_available

        # Just verify it returns bool without error
        result = check_rtl433_available()
        assert isinstance(result, bool)

    def test_decoder_build_command(self) -> None:
        """Decoder should build correct command line."""
        from rf_asset_discovery.decoders.iot.rtl433_wrapper import RTL433Decoder

        decoder = RTL433Decoder(
            frequencies=["433.92M", "315M"],
            hop_time_seconds=15,
            device_index=1,
            gain=40,
        )
        cmd = decoder._build_command()

        assert "rtl_433" in cmd
        assert "-f" in cmd
        assert "433.92M" in cmd
        assert "315M" in cmd
        assert "-H" in cmd
        assert "15" in cmd
        assert "-d" in cmd
        assert "1" in cmd
        assert "-g" in cmd
        assert "40" in cmd
        assert "-F" in cmd
        assert "json" in cmd

    def test_decoder_not_started_error(self) -> None:
        """stream_raw should raise if decoder not started."""
        from rf_asset_discovery.decoders.iot import RTL433Decoder, RTL433Error

        decoder = RTL433Decoder()
        with pytest.raises(RTL433Error, match="not started"):
            list(decoder.stream_raw())
