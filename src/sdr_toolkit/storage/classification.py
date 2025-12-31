"""Classification and inference logic for asset standards alignment.

Provides automatic inference of:
- ServiceNow CMDB CI class
- ISA-95/Purdue Model level
- NIST device category
- Security posture assessment
- Risk level calculation
"""

from __future__ import annotations

from sdr_toolkit.storage.models import (
    Asset,
    CMDBCIClass,
    DeviceCategory,
    PurdueLevel,
    RFProtocol,
    RiskLevel,
    SecurityPosture,
)


def infer_cmdb_ci_class(asset: Asset) -> CMDBCIClass:
    """Infer ServiceNow CMDB CI class from asset attributes.

    Args:
        asset: Asset to classify.

    Returns:
        Inferred CMDBCIClass.
    """
    protocol = asset.rf_protocol
    category = asset.device_category

    # WiFi access points
    if protocol == RFProtocol.WIFI:
        if category == DeviceCategory.GATEWAY:
            return CMDBCIClass.WAP
        return CMDBCIClass.NETWORK_GEAR

    # LoRaWAN gateways
    if protocol == RFProtocol.LORAWAN and category == DeviceCategory.GATEWAY:
        return CMDBCIClass.IOT_GATEWAY

    # Sensor devices
    if category == DeviceCategory.SENSOR:
        if protocol in (RFProtocol.ZIGBEE, RFProtocol.BLE, RFProtocol.ZWAVE):
            return CMDBCIClass.IOT_SENSOR
        return CMDBCIClass.IOT_DEVICE

    # Industrial/OT protocols
    if protocol in (RFProtocol.WIRELESSHART, RFProtocol.ISA100):
        if category == DeviceCategory.CONTROLLER:
            return CMDBCIClass.OT_CONTROLLER
        return CMDBCIClass.OT_DEVICE

    # Controllers
    if category == DeviceCategory.CONTROLLER:
        return CMDBCIClass.OT_CONTROLLER

    # Gateways
    if category == DeviceCategory.GATEWAY:
        return CMDBCIClass.IOT_GATEWAY

    # RF emitters (broadcast, ADS-B, etc.)
    if protocol in (RFProtocol.FM_BROADCAST, RFProtocol.AM_BROADCAST, RFProtocol.ADSB):
        return CMDBCIClass.RF_EMITTER

    # Default to IoT device
    return CMDBCIClass.IOT_DEVICE


def infer_purdue_level(asset: Asset) -> PurdueLevel | None:
    """Infer ISA-95/Purdue Model level from asset attributes.

    Args:
        asset: Asset to classify.

    Returns:
        Inferred PurdueLevel or None if not applicable.
    """
    protocol = asset.rf_protocol
    category = asset.device_category
    ot_protocol = asset.ot_protocol

    # Industrial wireless protocols
    if protocol in (RFProtocol.WIRELESSHART, RFProtocol.ISA100) or ot_protocol:
        # Field sensors
        if category == DeviceCategory.SENSOR:
            return PurdueLevel.PHYSICAL_PROCESS
        # Gateways for industrial protocols
        if category == DeviceCategory.GATEWAY:
            return PurdueLevel.BASIC_CONTROL
        # Controllers
        if category == DeviceCategory.CONTROLLER:
            return PurdueLevel.BASIC_CONTROL
        # Default industrial
        return PurdueLevel.PHYSICAL_PROCESS

    # LoRaWAN gateways typically at site operations
    if protocol == RFProtocol.LORAWAN and category == DeviceCategory.GATEWAY:
        return PurdueLevel.SITE_OPERATIONS

    # Consumer protocols typically at enterprise level
    if protocol in (RFProtocol.BLUETOOTH, RFProtocol.BLE, RFProtocol.WIFI):
        return PurdueLevel.ENTERPRISE_IT

    # Zigbee/Z-Wave in building automation
    if protocol in (RFProtocol.ZIGBEE, RFProtocol.ZWAVE):
        if category == DeviceCategory.CONTROLLER:
            return PurdueLevel.SUPERVISORY
        return PurdueLevel.ENTERPRISE_IT

    # No Purdue level for non-industrial assets
    return None


def infer_device_category(
    protocol: RFProtocol,
    frequency_hz: float | None = None,
) -> DeviceCategory:
    """Infer device category from protocol and frequency.

    Args:
        protocol: RF protocol type.
        frequency_hz: Optional frequency for context.

    Returns:
        Inferred DeviceCategory.
    """
    # Sensor protocols
    if protocol in (
        RFProtocol.TPMS,
        RFProtocol.WEATHER_STATION,
    ):
        return DeviceCategory.SENSOR

    # Industrial sensor protocols
    if protocol in (RFProtocol.WIRELESSHART, RFProtocol.ISA100):
        return DeviceCategory.SENSOR

    # LPWAN typically sensors or gateways
    if protocol == RFProtocol.LORA:
        return DeviceCategory.SENSOR

    if protocol == RFProtocol.LORAWAN:
        # Common gateway frequencies (US915)
        if frequency_hz and 902e6 <= frequency_hz <= 928e6:
            # Could be either - default to sensor
            return DeviceCategory.SENSOR
        return DeviceCategory.SENSOR

    # Consumer wireless endpoints
    if protocol in (RFProtocol.BLE, RFProtocol.BLUETOOTH):
        return DeviceCategory.ENDPOINT

    # Home automation
    if protocol in (RFProtocol.ZIGBEE, RFProtocol.ZWAVE):
        return DeviceCategory.ENDPOINT

    # WiFi - could be anything
    if protocol == RFProtocol.WIFI:
        return DeviceCategory.ENDPOINT

    # Default
    return DeviceCategory.ENDPOINT


def assess_security_posture(
    asset: Asset,
    known_macs: set[str] | None = None,
    known_fingerprints: set[str] | None = None,
) -> SecurityPosture:
    """Assess security posture of an asset.

    Args:
        asset: Asset to assess.
        known_macs: Set of known/authorized MAC addresses.
        known_fingerprints: Set of known RF fingerprints.

    Returns:
        Assessed SecurityPosture.
    """
    known_macs = known_macs or set()
    known_fingerprints = known_fingerprints or set()

    # Already synced with CMDB = verified
    if asset.cmdb_sys_id:
        return SecurityPosture.VERIFIED

    # MAC in known list = known
    if asset.net_mac_address and asset.net_mac_address.lower() in {
        m.lower() for m in known_macs
    }:
        return SecurityPosture.KNOWN

    # RF fingerprint in known list = known
    if asset.rf_fingerprint_hash and asset.rf_fingerprint_hash in known_fingerprints:
        return SecurityPosture.KNOWN

    # Unknown protocol with network access = suspicious
    if (
        asset.rf_protocol == RFProtocol.UNKNOWN
        and asset.net_ip_address
        and asset.asset_type == "correlated"
    ):
        return SecurityPosture.SUSPICIOUS

    # Default to unknown
    return SecurityPosture.UNKNOWN


def calculate_risk_level(
    asset: Asset,
    known_vulns: list[str] | None = None,
) -> RiskLevel:
    """Calculate risk level for an asset.

    Args:
        asset: Asset to assess.
        known_vulns: List of CVE IDs affecting this asset.

    Returns:
        Calculated RiskLevel.
    """
    known_vulns = known_vulns or []

    # Known vulnerabilities = critical or high
    if known_vulns:
        # Check for critical CVEs (simplified heuristic)
        if any("CRITICAL" in v.upper() for v in known_vulns):
            return RiskLevel.CRITICAL
        return RiskLevel.HIGH

    # Unauthorized devices = high risk
    if asset.security_posture == SecurityPosture.UNAUTHORIZED:
        return RiskLevel.CRITICAL

    # Suspicious devices = medium-high
    if asset.security_posture == SecurityPosture.SUSPICIOUS:
        return RiskLevel.HIGH

    # Industrial protocols = elevated baseline
    if asset.rf_protocol in (RFProtocol.WIRELESSHART, RFProtocol.ISA100):
        if asset.security_posture == SecurityPosture.UNKNOWN:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    # Unknown devices with network access = medium
    if (
        asset.security_posture == SecurityPosture.UNKNOWN
        and asset.net_ip_address
    ):
        return RiskLevel.MEDIUM

    # Consumer IoT
    if asset.rf_protocol in (
        RFProtocol.TPMS,
        RFProtocol.WEATHER_STATION,
        RFProtocol.FM_BROADCAST,
    ):
        return RiskLevel.LOW

    # Default
    return RiskLevel.INFORMATIONAL


def apply_nist_categorization(asset: Asset) -> dict[str, bool]:
    """Apply NIST SP 800-213A capability categorization.

    Evaluates which of the seven technical capability categories
    have data available for this asset.

    Args:
        asset: Asset to categorize.

    Returns:
        Dict mapping capability names to availability.
    """
    return {
        # Device has identifier (MAC or fingerprint)
        "device_identification": bool(
            asset.net_mac_address or asset.rf_fingerprint_hash
        ),
        # Device has configuration metadata
        "device_configuration": bool(asset.metadata),
        # Encryption/security info available
        "data_protection": "encryption" in asset.metadata or "secure" in (
            asset.rf_modulation_type or ""
        ).lower(),
        # Network ports/services known
        "logical_access": bool(asset.net_open_ports or asset.net_ip_address),
        # Firmware version tracked
        "software_update": "firmware" in asset.metadata or "version" in asset.metadata,
        # Security posture is not unknown
        "cybersecurity_state": asset.security_posture != SecurityPosture.UNKNOWN,
        # Device category determined
        "device_security": asset.device_category is not None,
    }


def auto_classify_asset(asset: Asset) -> Asset:
    """Apply all automatic classifications to an asset.

    Updates the asset in-place with inferred values for:
    - cmdb_ci_class
    - purdue_level
    - device_category
    - security_posture
    - risk_level

    Args:
        asset: Asset to classify.

    Returns:
        The same asset with updated fields.
    """
    # Infer device category first (used by other inferences)
    if asset.device_category is None:
        asset.device_category = infer_device_category(
            asset.rf_protocol,
            asset.rf_frequency_hz,
        )

    # Infer CMDB class
    if asset.cmdb_ci_class is None:
        asset.cmdb_ci_class = infer_cmdb_ci_class(asset)

    # Infer Purdue level
    if asset.purdue_level is None:
        asset.purdue_level = infer_purdue_level(asset)

    # Assess security posture (keep existing if not UNKNOWN)
    if asset.security_posture == SecurityPosture.UNKNOWN:
        asset.security_posture = assess_security_posture(asset)

    # Calculate risk level
    asset.risk_level = calculate_risk_level(asset)

    return asset
