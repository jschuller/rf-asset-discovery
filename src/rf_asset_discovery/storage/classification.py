"""Classification and inference logic for asset standards alignment.

Provides automatic inference of:
- ServiceNow CMDB CI class
- ISA-95/Purdue Model level
- NIST device category
- Security posture assessment
- Risk level calculation
"""

from __future__ import annotations

from rf_asset_discovery.storage.models import (
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


# =============================================================================
# Band-to-Protocol Mapping (for Medallion Architecture Transformations)
# =============================================================================

from typing import NamedTuple


class BandProtocolInfo(NamedTuple):
    """Band to protocol mapping info for medallion transforms."""

    protocol: str
    modulation: str
    cmdb_ci_class: str
    purdue_level: int
    description: str


# Band to protocol mapping for silver layer transformation
BAND_PROTOCOL_MAP: dict[str, BandProtocolInfo] = {
    # Broadcast
    "fm_broadcast": BandProtocolInfo(
        "FM_BROADCAST", "WFM", "RF_BROADCAST_TRANSMITTER", 5, "FM broadcast (75 kHz)",
    ),
    # Aviation
    "aircraft": BandProtocolInfo(
        "AM_VOICE", "AM", "RF_AVIATION_TRANSPONDER", 5, "Civil aviation voice",
    ),
    "adsb": BandProtocolInfo(
        "ADS_B", "PPM", "RF_ADSB_TRANSPONDER", 5, "ADS-B Mode S",
    ),
    # ISM bands (IoT)
    "ism_433": BandProtocolInfo(
        "OOK", "OOK", "RF_IOT_DEVICE", 0, "433 MHz ISM",
    ),
    "ism_315": BandProtocolInfo(
        "OOK", "OOK", "RF_IOT_DEVICE", 0, "315 MHz ISM",
    ),
    "ism_868": BandProtocolInfo(
        "FSK", "GFSK", "RF_IOT_DEVICE", 0, "868 MHz EU IoT",
    ),
    "ism_900": BandProtocolInfo(
        "FSK", "GFSK", "RF_IOT_DEVICE", 1, "900 MHz US LoRa",
    ),
    # Two-way radio
    "frs_gmrs": BandProtocolInfo(
        "FM_VOICE", "NFM", "RF_TWO_WAY_RADIO", 4, "FRS/GMRS",
    ),
    "marine_vhf": BandProtocolInfo(
        "FM_VOICE", "NFM", "RF_MARINE_RADIO", 5, "Marine VHF",
    ),
    "noaa_weather": BandProtocolInfo(
        "FM_VOICE", "NFM", "RF_WEATHER_STATION", 5, "NOAA weather",
    ),
    # Amateur radio
    "uhf_amateur": BandProtocolInfo(
        "MIXED", "FM_SSB", "RF_AMATEUR_RADIO", 5, "UHF amateur (70cm)",
    ),
    "vhf_amateur": BandProtocolInfo(
        "MIXED", "FM_SSB", "RF_AMATEUR_RADIO", 5, "VHF amateur (2m)",
    ),
    # Cellular
    "cellular_700": BandProtocolInfo(
        "LTE", "OFDM", "RF_CELLULAR_TOWER", 5, "LTE 700 MHz",
    ),
    "cellular_850": BandProtocolInfo(
        "LTE", "OFDM", "RF_CELLULAR_TOWER", 5, "LTE 850 MHz",
    ),
    "cellular_1900": BandProtocolInfo(
        "LTE", "OFDM", "RF_CELLULAR_TOWER", 5, "LTE/PCS 1900 MHz",
    ),
    # Navigation
    "gps": BandProtocolInfo(
        "SPREAD_SPECTRUM", "CDMA", "RF_NAVIGATION_SATELLITE", 5, "GPS L1",
    ),
}

UNKNOWN_BAND_INFO = BandProtocolInfo(
    "UNKNOWN", "UNKNOWN", "RF_EMITTER", 5, "Unclassified",
)


def get_band_protocol_info(freq_band: str | None) -> BandProtocolInfo:
    """Get protocol info for a frequency band.

    Args:
        freq_band: Frequency band identifier.

    Returns:
        BandProtocolInfo with classification fields.
    """
    if not freq_band:
        return UNKNOWN_BAND_INFO
    return BAND_PROTOCOL_MAP.get(freq_band.lower(), UNKNOWN_BAND_INFO)


def classify_band_protocol(freq_band: str | None) -> str:
    """Get RF protocol for a frequency band.

    Args:
        freq_band: Frequency band identifier.

    Returns:
        RF protocol string.
    """
    return get_band_protocol_info(freq_band).protocol


def classify_band_cmdb_class(freq_band: str | None) -> str:
    """Get CMDB CI class for a frequency band.

    Args:
        freq_band: Frequency band identifier.

    Returns:
        CMDB CI class string.
    """
    return get_band_protocol_info(freq_band).cmdb_ci_class


def classify_band_purdue_level(freq_band: str | None) -> int:
    """Get Purdue level for a frequency band.

    Args:
        freq_band: Frequency band identifier.

    Returns:
        Purdue level (0-5).
    """
    return get_band_protocol_info(freq_band).purdue_level


def assess_band_security_posture(freq_band: str | None, power_db: float) -> str:
    """Assess security posture based on band and power.

    Args:
        freq_band: Frequency band identifier.
        power_db: Signal power in dB.

    Returns:
        Security posture string.
    """
    info = get_band_protocol_info(freq_band)

    # OT/IoT bands at lower Purdue levels need review
    if info.purdue_level <= 1:
        return "REQUIRES_REVIEW"

    # Strong unknown signals need review
    if info.protocol == "UNKNOWN" and power_db >= 10:
        return "REQUIRES_REVIEW"

    # Known protocols at higher levels are compliant
    if info.protocol != "UNKNOWN":
        return "COMPLIANT"

    return "NOT_ASSESSED"


def assess_band_risk_level(security_posture: str, purdue_level: int) -> str:
    """Assess risk level based on posture and Purdue level.

    Args:
        security_posture: Security posture string.
        purdue_level: Purdue level (0-5).

    Returns:
        Risk level string.
    """
    if security_posture == "REQUIRES_REVIEW":
        if purdue_level <= 1:
            return "HIGH"
        return "MEDIUM"
    return "LOW"


# SQL CASE statements for medallion transforms
PROTOCOL_CASE_SQL = """
CASE freq_band
    WHEN 'fm_broadcast' THEN 'FM_BROADCAST'
    WHEN 'aircraft' THEN 'AM_VOICE'
    WHEN 'adsb' THEN 'ADS_B'
    WHEN 'ism_433' THEN 'OOK'
    WHEN 'ism_315' THEN 'OOK'
    WHEN 'ism_868' THEN 'FSK'
    WHEN 'ism_900' THEN 'FSK'
    WHEN 'frs_gmrs' THEN 'FM_VOICE'
    WHEN 'marine_vhf' THEN 'FM_VOICE'
    WHEN 'noaa_weather' THEN 'FM_VOICE'
    WHEN 'uhf_amateur' THEN 'MIXED'
    WHEN 'vhf_amateur' THEN 'MIXED'
    WHEN 'cellular_700' THEN 'LTE'
    WHEN 'cellular_850' THEN 'LTE'
    WHEN 'cellular_1900' THEN 'LTE'
    WHEN 'gps' THEN 'SPREAD_SPECTRUM'
    ELSE 'UNKNOWN'
END
"""

CMDB_CLASS_CASE_SQL = """
CASE freq_band
    WHEN 'fm_broadcast' THEN 'RF_BROADCAST_TRANSMITTER'
    WHEN 'aircraft' THEN 'RF_AVIATION_TRANSPONDER'
    WHEN 'adsb' THEN 'RF_ADSB_TRANSPONDER'
    WHEN 'ism_433' THEN 'RF_IOT_DEVICE'
    WHEN 'ism_315' THEN 'RF_IOT_DEVICE'
    WHEN 'ism_868' THEN 'RF_IOT_DEVICE'
    WHEN 'ism_900' THEN 'RF_IOT_DEVICE'
    WHEN 'frs_gmrs' THEN 'RF_TWO_WAY_RADIO'
    WHEN 'marine_vhf' THEN 'RF_MARINE_RADIO'
    WHEN 'noaa_weather' THEN 'RF_WEATHER_STATION'
    WHEN 'uhf_amateur' THEN 'RF_AMATEUR_RADIO'
    WHEN 'vhf_amateur' THEN 'RF_AMATEUR_RADIO'
    WHEN 'cellular_700' THEN 'RF_CELLULAR_TOWER'
    WHEN 'cellular_850' THEN 'RF_CELLULAR_TOWER'
    WHEN 'cellular_1900' THEN 'RF_CELLULAR_TOWER'
    WHEN 'gps' THEN 'RF_NAVIGATION_SATELLITE'
    ELSE 'RF_EMITTER'
END
"""

PURDUE_LEVEL_CASE_SQL = """
CASE freq_band
    WHEN 'ism_433' THEN 0
    WHEN 'ism_315' THEN 0
    WHEN 'ism_868' THEN 0
    WHEN 'ism_900' THEN 1
    WHEN 'frs_gmrs' THEN 4
    ELSE 5
END
"""
