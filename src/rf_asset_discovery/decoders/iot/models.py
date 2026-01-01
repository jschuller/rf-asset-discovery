"""Data models for IoT protocol discovery.

Defines IoTProtocolType enum and dataclasses for decoded packets
and tracked devices.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rf_asset_discovery.storage.models import Asset, Signal


class IoTProtocolType(str, Enum):
    """IoT protocol classification types.

    Maps rtl_433 decoded signals to protocol families
    for device categorization.
    """

    TPMS = "tpms"
    WEATHER_STATION = "weather_station"
    TEMPERATURE_SENSOR = "temperature_sensor"
    HUMIDITY_SENSOR = "humidity_sensor"
    DOOR_SENSOR = "door_sensor"
    MOTION_SENSOR = "motion_sensor"
    REMOTE_CONTROL = "remote_control"
    SMOKE_DETECTOR = "smoke_detector"
    WATER_LEAK = "water_leak"
    GENERIC_OOK = "generic_ook"
    UNKNOWN = "unknown"


@dataclass
class IoTPacket:
    """Decoded IoT packet from rtl_433.

    Represents a single decoded transmission with
    extracted device ID and protocol classification.
    """

    # Core fields
    raw_json: dict[str, Any]
    timestamp: datetime
    model: str
    device_id: str
    protocol_type: IoTProtocolType

    # Signal info
    frequency_mhz: float | None = None
    rssi_db: float | None = None

    # Protocol-specific telemetry (optional)
    temperature_c: float | None = None
    humidity_pct: float | None = None
    pressure_kpa: float | None = None
    battery_ok: bool | None = None
    channel: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "model": self.model,
            "device_id": self.device_id,
            "protocol_type": self.protocol_type.value,
            "frequency_mhz": self.frequency_mhz,
            "rssi_db": self.rssi_db,
            "temperature_c": self.temperature_c,
            "humidity_pct": self.humidity_pct,
            "pressure_kpa": self.pressure_kpa,
            "battery_ok": self.battery_ok,
            "channel": self.channel,
            "raw_json": self.raw_json,
        }

    def to_signal(
        self,
        survey_id: str,
        scan_id: str | None = None,
        location_name: str | None = None,
    ) -> Signal:
        """Convert to Signal for UnifiedDB storage.

        Args:
            survey_id: Parent survey ID.
            scan_id: Optional scan session ID.
            location_name: Location name for partition. Defaults to hostname.

        Returns:
            Signal model for database storage.
        """
        import socket

        from rf_asset_discovery.decoders.iot.classifier import map_to_rf_protocol
        from rf_asset_discovery.storage.models import Signal

        if not location_name:
            location_name = socket.gethostname() or "default"

        return Signal(
            survey_id=survey_id,
            scan_id=scan_id,
            frequency_hz=self.frequency_mhz * 1e6 if self.frequency_mhz else 433.92e6,
            power_db=self.rssi_db or -50.0,
            first_seen=self.timestamp,
            last_seen=self.timestamp,
            rf_protocol=map_to_rf_protocol(self.protocol_type),
            annotations={
                "iot_model": self.model,
                "iot_device_id": self.device_id,
                "iot_protocol": self.protocol_type.value,
                "temperature_c": self.temperature_c,
                "humidity_pct": self.humidity_pct,
                "pressure_kpa": self.pressure_kpa,
                "battery_ok": self.battery_ok,
            },
            # Partition columns
            location_name=location_name,
            year=self.timestamp.year,
            month=self.timestamp.month,
        )


@dataclass
class IoTDevice:
    """Tracked IoT device.

    Aggregates information from multiple packets
    for a unique device identified by device_id.
    """

    device_id: str
    model: str
    protocol_type: IoTProtocolType
    first_seen: datetime
    last_seen: datetime
    packet_count: int = 0
    last_rssi_db: float | None = None
    frequency_mhz: float | None = None

    # Latest telemetry values
    last_temperature_c: float | None = None
    last_humidity_pct: float | None = None
    last_pressure_kpa: float | None = None
    last_battery_ok: bool | None = None

    # Additional tracking
    channels_seen: set[int] = field(default_factory=set)

    def update_from_packet(self, packet: IoTPacket) -> None:
        """Update device state from a new packet.

        Args:
            packet: Decoded packet from this device.
        """
        self.last_seen = packet.timestamp
        self.packet_count += 1

        if packet.rssi_db is not None:
            self.last_rssi_db = packet.rssi_db
        if packet.frequency_mhz is not None:
            self.frequency_mhz = packet.frequency_mhz
        if packet.temperature_c is not None:
            self.last_temperature_c = packet.temperature_c
        if packet.humidity_pct is not None:
            self.last_humidity_pct = packet.humidity_pct
        if packet.pressure_kpa is not None:
            self.last_pressure_kpa = packet.pressure_kpa
        if packet.battery_ok is not None:
            self.last_battery_ok = packet.battery_ok
        if packet.channel is not None:
            self.channels_seen.add(packet.channel)

    def to_asset(self) -> Asset:
        """Convert to Asset model for UnifiedDB storage.

        Returns:
            Asset model with IoT device attributes.
        """
        from rf_asset_discovery.decoders.iot.classifier import map_to_rf_protocol
        from rf_asset_discovery.storage.models import Asset, DeviceCategory

        # Determine device category based on protocol
        category = DeviceCategory.SENSOR
        if self.protocol_type == IoTProtocolType.REMOTE_CONTROL:
            category = DeviceCategory.ENDPOINT

        return Asset(
            name=f"{self.model} ({self.device_id})",
            asset_type="rf_only",
            first_seen=self.first_seen,
            last_seen=self.last_seen,
            rf_frequency_hz=self.frequency_mhz * 1e6 if self.frequency_mhz else None,
            rf_signal_strength_db=self.last_rssi_db,
            rf_protocol=map_to_rf_protocol(self.protocol_type),
            device_category=category,
            discovery_source="rtl_433",
            metadata={
                "iot_device_id": self.device_id,
                "iot_model": self.model,
                "iot_protocol": self.protocol_type.value,
                "packet_count": self.packet_count,
                "channels_seen": list(self.channels_seen),
                "last_temperature_c": self.last_temperature_c,
                "last_humidity_pct": self.last_humidity_pct,
                "last_pressure_kpa": self.last_pressure_kpa,
                "last_battery_ok": self.last_battery_ok,
            },
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "device_id": self.device_id,
            "model": self.model,
            "protocol_type": self.protocol_type.value,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "packet_count": self.packet_count,
            "last_rssi_db": self.last_rssi_db,
            "frequency_mhz": self.frequency_mhz,
            "last_temperature_c": self.last_temperature_c,
            "last_humidity_pct": self.last_humidity_pct,
            "last_pressure_kpa": self.last_pressure_kpa,
            "last_battery_ok": self.last_battery_ok,
            "channels_seen": list(self.channels_seen),
        }

    @classmethod
    def from_packet(cls, packet: IoTPacket) -> IoTDevice:
        """Create new device from first packet.

        Args:
            packet: First decoded packet from device.

        Returns:
            New IoTDevice instance.
        """
        device = cls(
            device_id=packet.device_id,
            model=packet.model,
            protocol_type=packet.protocol_type,
            first_seen=packet.timestamp,
            last_seen=packet.timestamp,
        )
        device.update_from_packet(packet)
        return device
