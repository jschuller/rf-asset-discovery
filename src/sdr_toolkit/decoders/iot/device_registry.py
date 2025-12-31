"""Device registry for tracking unique IoT devices.

Maintains a registry of discovered devices, updating state
as new packets arrive and optionally syncing to UnifiedDB.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sdr_toolkit.decoders.iot.models import IoTDevice, IoTPacket, IoTProtocolType

if TYPE_CHECKING:
    from sdr_toolkit.storage.unified_db import UnifiedDB

logger = logging.getLogger(__name__)


class DeviceRegistry:
    """Registry for tracking unique IoT devices.

    Maintains device state across multiple packets and provides
    statistics, filtering, and persistence capabilities.

    Example:
        >>> registry = DeviceRegistry()
        >>> for packet in decoder.stream_packets():
        ...     device = registry.process_packet(packet)
        ...     print(f"Device {device.device_id}: {device.packet_count} packets")
    """

    def __init__(self, db: UnifiedDB | None = None) -> None:
        """Initialize device registry.

        Args:
            db: Optional UnifiedDB for persistent storage.
        """
        self._devices: dict[str, IoTDevice] = {}
        self._db = db
        self._packet_count = 0
        self._scan_id: str | None = None

    @property
    def device_count(self) -> int:
        """Number of unique devices tracked."""
        return len(self._devices)

    @property
    def packet_count(self) -> int:
        """Total packets processed."""
        return self._packet_count

    def set_scan_id(self, scan_id: str) -> None:
        """Set scan session ID for database storage.

        Args:
            scan_id: Scan session ID from UnifiedDB.
        """
        self._scan_id = scan_id

    def process_packet(self, packet: IoTPacket) -> IoTDevice:
        """Process a decoded packet.

        Updates existing device or creates new one.
        Optionally records to database.

        Args:
            packet: Decoded IoT packet.

        Returns:
            Updated or new IoTDevice.
        """
        self._packet_count += 1
        device_id = packet.device_id

        if device_id in self._devices:
            device = self._devices[device_id]
            device.update_from_packet(packet)
            logger.debug("Updated device %s (packets: %d)", device_id, device.packet_count)
        else:
            device = IoTDevice.from_packet(packet)
            self._devices[device_id] = device
            logger.info("New device discovered: %s (%s)", device_id, packet.protocol_type.value)

        # Record to database if configured
        if self._db and self._scan_id:
            self._record_to_db(packet, device)

        return device

    def _record_to_db(self, packet: IoTPacket, device: IoTDevice) -> None:
        """Record packet and device to database.

        Args:
            packet: Decoded packet.
            device: Updated device.
        """
        try:
            # Record the RF capture
            capture = packet.to_rf_capture(self._scan_id)  # type: ignore[arg-type]
            self._db.record_rf_capture(capture)  # type: ignore[union-attr]

            # Upsert device as asset (update existing or create new)
            asset = device.to_asset()
            existing = self._db.find_assets_by_frequency(  # type: ignore[union-attr]
                asset.rf_frequency_hz or 433.92e6,
                tolerance_hz=1e6,
            )

            # Check if we have this device already (by metadata)
            found = False
            for existing_asset in existing:
                if existing_asset.metadata.get("iot_device_id") == device.device_id:
                    # Update existing
                    existing_asset.last_seen = device.last_seen
                    existing_asset.rf_signal_strength_db = device.last_rssi_db
                    existing_asset.metadata.update(asset.metadata)
                    self._db.update_asset(existing_asset)  # type: ignore[union-attr]
                    found = True
                    break

            if not found:
                self._db.insert_asset(asset)  # type: ignore[union-attr]

        except Exception as e:
            logger.warning("Failed to record to database: %s", e)

    def get_device(self, device_id: str) -> IoTDevice | None:
        """Get device by ID.

        Args:
            device_id: Device identifier.

        Returns:
            IoTDevice if found.
        """
        return self._devices.get(device_id)

    def get_all_devices(self) -> list[IoTDevice]:
        """Get all devices sorted by last_seen descending.

        Returns:
            List of all tracked devices.
        """
        return sorted(
            self._devices.values(),
            key=lambda d: d.last_seen,
            reverse=True,
        )

    def get_devices_by_protocol(self, protocol: IoTProtocolType) -> list[IoTDevice]:
        """Get devices filtered by protocol type.

        Args:
            protocol: Protocol type to filter by.

        Returns:
            List of matching devices.
        """
        return [d for d in self._devices.values() if d.protocol_type == protocol]

    def get_new_devices_since(self, since: datetime) -> list[IoTDevice]:
        """Get devices first seen since a given time.

        Args:
            since: Cutoff datetime.

        Returns:
            List of new devices.
        """
        return [d for d in self._devices.values() if d.first_seen >= since]

    def get_active_devices(self, within_seconds: int = 300) -> list[IoTDevice]:
        """Get devices seen within recent time window.

        Args:
            within_seconds: Time window in seconds (default 5 minutes).

        Returns:
            List of recently active devices.
        """
        cutoff = datetime.now()
        return [
            d
            for d in self._devices.values()
            if (cutoff - d.last_seen).total_seconds() <= within_seconds
        ]

    def get_stats(self) -> dict[str, Any]:
        """Get registry statistics.

        Returns:
            Dict with device and packet counts.
        """
        devices_by_protocol: dict[str, int] = {}
        for device in self._devices.values():
            proto = device.protocol_type.value
            devices_by_protocol[proto] = devices_by_protocol.get(proto, 0) + 1

        newest = max(self._devices.values(), key=lambda d: d.first_seen, default=None)
        oldest = min(self._devices.values(), key=lambda d: d.first_seen, default=None)

        return {
            "total_devices": len(self._devices),
            "total_packets": self._packet_count,
            "devices_by_protocol": devices_by_protocol,
            "newest_device": newest.to_dict() if newest else None,
            "oldest_device": oldest.to_dict() if oldest else None,
        }

    def to_json(self, output_path: Path) -> None:
        """Export registry to JSON file.

        Args:
            output_path: Output file path.
        """
        data = {
            "exported_at": datetime.now().isoformat(),
            "total_devices": len(self._devices),
            "total_packets": self._packet_count,
            "devices": [d.to_dict() for d in self.get_all_devices()],
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        logger.info("Exported %d devices to %s", len(self._devices), output_path)

    @classmethod
    def from_json(cls, input_path: Path, db: UnifiedDB | None = None) -> DeviceRegistry:
        """Load registry from JSON file.

        Args:
            input_path: Input file path.
            db: Optional UnifiedDB for future persistence.

        Returns:
            Loaded DeviceRegistry.
        """
        with open(input_path) as f:
            data = json.load(f)

        registry = cls(db=db)
        registry._packet_count = data.get("total_packets", 0)

        for device_data in data.get("devices", []):
            # Reconstruct IoTDevice
            device = IoTDevice(
                device_id=device_data["device_id"],
                model=device_data["model"],
                protocol_type=IoTProtocolType(device_data["protocol_type"]),
                first_seen=datetime.fromisoformat(device_data["first_seen"]),
                last_seen=datetime.fromisoformat(device_data["last_seen"]),
                packet_count=device_data.get("packet_count", 0),
                last_rssi_db=device_data.get("last_rssi_db"),
                frequency_mhz=device_data.get("frequency_mhz"),
                last_temperature_c=device_data.get("last_temperature_c"),
                last_humidity_pct=device_data.get("last_humidity_pct"),
                last_pressure_kpa=device_data.get("last_pressure_kpa"),
                last_battery_ok=device_data.get("last_battery_ok"),
                channels_seen=set(device_data.get("channels_seen", [])),
            )
            registry._devices[device.device_id] = device

        logger.info("Loaded %d devices from %s", len(registry._devices), input_path)
        return registry

    def sync_to_db(self) -> int:
        """Sync all devices to UnifiedDB as Assets.

        Returns:
            Number of devices synced.
        """
        if self._db is None:
            logger.warning("No database configured for sync")
            return 0

        synced = 0
        for device in self._devices.values():
            try:
                asset = device.to_asset()
                self._db.insert_asset(asset)
                synced += 1
            except Exception as e:
                logger.warning("Failed to sync device %s: %s", device.device_id, e)

        logger.info("Synced %d devices to database", synced)
        return synced

    def clear(self) -> None:
        """Clear all tracked devices."""
        self._devices.clear()
        self._packet_count = 0
        logger.info("Registry cleared")
