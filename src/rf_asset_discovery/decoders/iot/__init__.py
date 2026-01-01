"""IoT protocol discovery using rtl_433.

This module provides ISM band signal decoding for IoT device discovery:
- TPMS (tire pressure monitoring)
- Weather stations
- Temperature/humidity sensors
- Door/window sensors
- Generic OOK/ASK remotes

Requires rtl_433 system binary (install via homebrew/apt).
"""

from __future__ import annotations

from rf_asset_discovery.decoders.iot.classifier import (
    classify_protocol,
    extract_device_id,
    map_to_rf_protocol,
)
from rf_asset_discovery.decoders.iot.device_registry import DeviceRegistry
from rf_asset_discovery.decoders.iot.models import (
    IoTDevice,
    IoTPacket,
    IoTProtocolType,
)
from rf_asset_discovery.decoders.iot.rtl433_wrapper import (
    RTL433Decoder,
    RTL433Error,
    check_rtl433_available,
)

__all__ = [
    # Main classes
    "RTL433Decoder",
    "DeviceRegistry",
    # Data models
    "IoTPacket",
    "IoTDevice",
    "IoTProtocolType",
    # Classifier functions
    "classify_protocol",
    "extract_device_id",
    "map_to_rf_protocol",
    # Utilities
    "RTL433Error",
    "check_rtl433_available",
]

__version__ = "1.0.0"
