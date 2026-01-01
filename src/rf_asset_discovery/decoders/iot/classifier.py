"""Protocol classification for rtl_433 decoded signals.

Maps rtl_433 model strings to IoTProtocolType and extracts
unique device identifiers from decoded packets.
"""

from __future__ import annotations

import hashlib
from typing import Any

from rf_asset_discovery.decoders.iot.models import IoTProtocolType
from rf_asset_discovery.storage.models import RFProtocol

# Pattern matching rules for protocol classification
# Format: (patterns, protocol_type) - patterns are case-insensitive
PROTOCOL_PATTERNS: list[tuple[list[str], IoTProtocolType]] = [
    # TPMS - Tire Pressure Monitoring Systems
    (
        ["schrader", "tpms", "toyota-tpms", "ford-tpms", "bmw-tpms", "citroen", "peugeot"],
        IoTProtocolType.TPMS,
    ),
    # Weather stations
    (
        [
            "acurite",
            "oregon",
            "fineoffset",
            "wh1080",
            "wh2",
            "wh3",
            "ws2032",
            "lacrosse",
            "ambient",
            "bresser",
            "davis",
            "ecowitt",
        ],
        IoTProtocolType.WEATHER_STATION,
    ),
    # Temperature sensors
    (
        ["th", "thermo", "temp", "thermopro", "inkbird", "govee-h"],
        IoTProtocolType.TEMPERATURE_SENSOR,
    ),
    # Humidity sensors
    (["humid", "hygrometer"], IoTProtocolType.HUMIDITY_SENSOR),
    # Door/window sensors
    (
        ["door", "window", "contact", "honeywell-door", "ge-door", "visonic"],
        IoTProtocolType.DOOR_SENSOR,
    ),
    # Motion sensors
    (["motion", "pir", "occupancy"], IoTProtocolType.MOTION_SENSOR),
    # Remote controls
    (
        ["remote", "garage", "keyfob", "fan-remote", "ceiling-fan", "rf-remote"],
        IoTProtocolType.REMOTE_CONTROL,
    ),
    # Smoke/fire detectors
    (["smoke", "fire", "co2", "carbon"], IoTProtocolType.SMOKE_DETECTOR),
    # Water leak sensors
    (["water", "leak", "flood", "moisture"], IoTProtocolType.WATER_LEAK),
    # Generic OOK
    (["ook", "generic", "pulse"], IoTProtocolType.GENERIC_OOK),
]


def classify_protocol(model: str) -> IoTProtocolType:
    """Classify protocol from rtl_433 model string.

    Uses pattern matching against known device model patterns
    to determine the IoT protocol family.

    Args:
        model: rtl_433 model name (e.g., "Acurite-Tower").

    Returns:
        Classified IoTProtocolType.

    Example:
        >>> classify_protocol("Acurite-Tower")
        IoTProtocolType.WEATHER_STATION
        >>> classify_protocol("Schrader-EG53MA4")
        IoTProtocolType.TPMS
    """
    model_lower = model.lower()

    for patterns, protocol_type in PROTOCOL_PATTERNS:
        for pattern in patterns:
            if pattern in model_lower:
                return protocol_type

    return IoTProtocolType.UNKNOWN


def extract_device_id(packet_json: dict[str, Any]) -> str:
    """Extract unique device identifier from rtl_433 packet.

    Uses a fallback chain to find the most reliable identifier:
    1. 'id' field (most common)
    2. 'sensor_id' field (alternative naming)
    3. Composite of model + channel
    4. Hash of stable fields

    Args:
        packet_json: Raw JSON from rtl_433.

    Returns:
        Unique device identifier string.

    Example:
        >>> extract_device_id({"model": "Acurite-Tower", "id": 12345})
        "Acurite-Tower_12345"
    """
    model = packet_json.get("model", "Unknown")

    # Try 'id' field first
    if "id" in packet_json:
        device_id = str(packet_json["id"])
        channel = packet_json.get("channel")
        if channel is not None:
            return f"{model}_{device_id}_ch{channel}"
        return f"{model}_{device_id}"

    # Try 'sensor_id' field
    if "sensor_id" in packet_json:
        device_id = str(packet_json["sensor_id"])
        channel = packet_json.get("channel")
        if channel is not None:
            return f"{model}_{device_id}_ch{channel}"
        return f"{model}_{device_id}"

    # Try composite with channel only
    if "channel" in packet_json:
        return f"{model}_ch{packet_json['channel']}"

    # Fallback: hash stable fields
    stable_fields = ["model", "subtype", "type"]
    hash_input = "_".join(str(packet_json.get(f, "")) for f in stable_fields)
    hash_value = hashlib.md5(hash_input.encode()).hexdigest()[:8]  # noqa: S324
    return f"{model}_{hash_value}"


def map_to_rf_protocol(iot_type: IoTProtocolType) -> RFProtocol:
    """Map IoTProtocolType to storage RFProtocol enum.

    Converts the IoT-specific protocol classification to
    the unified RFProtocol enum for database storage.

    Args:
        iot_type: IoT protocol classification.

    Returns:
        Corresponding RFProtocol value.
    """
    mapping = {
        IoTProtocolType.TPMS: RFProtocol.TPMS,
        IoTProtocolType.WEATHER_STATION: RFProtocol.WEATHER_STATION,
        IoTProtocolType.TEMPERATURE_SENSOR: RFProtocol.WEATHER_STATION,
        IoTProtocolType.HUMIDITY_SENSOR: RFProtocol.WEATHER_STATION,
        # Other sensor types map to generic
        IoTProtocolType.DOOR_SENSOR: RFProtocol.UNKNOWN,
        IoTProtocolType.MOTION_SENSOR: RFProtocol.UNKNOWN,
        IoTProtocolType.REMOTE_CONTROL: RFProtocol.UNKNOWN,
        IoTProtocolType.SMOKE_DETECTOR: RFProtocol.UNKNOWN,
        IoTProtocolType.WATER_LEAK: RFProtocol.UNKNOWN,
        IoTProtocolType.GENERIC_OOK: RFProtocol.UNKNOWN,
        IoTProtocolType.UNKNOWN: RFProtocol.UNKNOWN,
    }
    return mapping.get(iot_type, RFProtocol.UNKNOWN)


def extract_telemetry(packet_json: dict[str, Any]) -> dict[str, Any]:
    """Extract telemetry values from rtl_433 packet.

    Normalizes field names and units from various device formats.

    Args:
        packet_json: Raw JSON from rtl_433.

    Returns:
        Dict with normalized telemetry values.
    """
    telemetry: dict[str, Any] = {}

    # Temperature (various field names, always convert to Celsius)
    for temp_field in ["temperature_C", "temperature_c", "temp_C", "temp_c", "temperature"]:
        if temp_field in packet_json:
            telemetry["temperature_c"] = float(packet_json[temp_field])
            break

    # Temperature in Fahrenheit - convert to Celsius
    for temp_f_field in ["temperature_F", "temperature_f", "temp_F", "temp_f"]:
        if temp_f_field in packet_json and "temperature_c" not in telemetry:
            temp_f = float(packet_json[temp_f_field])
            telemetry["temperature_c"] = (temp_f - 32) * 5 / 9
            break

    # Humidity
    for humid_field in ["humidity", "humidity_pct", "rh"]:
        if humid_field in packet_json:
            telemetry["humidity_pct"] = float(packet_json[humid_field])
            break

    # Pressure (TPMS - typically in kPa or PSI)
    for pressure_field in ["pressure_kPa", "pressure_kpa", "pressure"]:
        if pressure_field in packet_json:
            telemetry["pressure_kpa"] = float(packet_json[pressure_field])
            break

    # Pressure in PSI - convert to kPa
    if "pressure_PSI" in packet_json and "pressure_kpa" not in telemetry:
        psi = float(packet_json["pressure_PSI"])
        telemetry["pressure_kpa"] = psi * 6.89476

    # Battery status
    for battery_field in ["battery_ok", "battery", "battery_low"]:
        if battery_field in packet_json:
            value = packet_json[battery_field]
            if battery_field == "battery_low":
                # battery_low=1 means battery NOT ok
                telemetry["battery_ok"] = not bool(value)
            else:
                telemetry["battery_ok"] = bool(value)
            break

    # Channel
    if "channel" in packet_json:
        telemetry["channel"] = int(packet_json["channel"])

    # RSSI/SNR (signal quality)
    for rssi_field in ["rssi", "snr", "noise"]:
        if rssi_field in packet_json:
            telemetry["rssi_db"] = float(packet_json[rssi_field])
            break

    return telemetry
