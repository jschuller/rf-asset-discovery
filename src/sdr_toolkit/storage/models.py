"""Pydantic data models for unified asset storage.

Defines enums and models for RF/network asset tracking with
industry standards alignment (ServiceNow CMDB, NIST, ISA-95).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

# ============================================================================
# Standards-Aligned Enums
# ============================================================================


class CMDBCIClass(str, Enum):
    """ServiceNow CMDB CI class mappings.

    Maps to ServiceNow's Configuration Item class hierarchy
    for enterprise asset management integration.
    """

    WAP = "cmdb_ci_wap"
    NETWORK_GEAR = "cmdb_ci_network_gear"
    IOT_DEVICE = "cmdb_ci_iot_device"
    IOT_SENSOR = "cmdb_ci_iot_sensor"
    IOT_GATEWAY = "cmdb_ci_iot_gateway"
    OT_DEVICE = "cmdb_ci_ot_device"
    OT_CONTROLLER = "cmdb_ci_ot_controller"
    RF_EMITTER = "cmdb_ci_rf_emitter"


class RFProtocol(str, Enum):
    """RF protocol classification.

    Covers consumer, industrial, and broadcast protocols
    detectable via SDR scanning.
    """

    # Consumer wireless
    WIFI = "wifi"
    BLUETOOTH = "bluetooth"
    BLE = "ble"
    ZIGBEE = "zigbee"
    ZWAVE = "zwave"

    # LPWAN
    LORA = "lora"
    LORAWAN = "lorawan"

    # Industrial
    WIRELESSHART = "wirelesshart"
    ISA100 = "isa100"

    # Consumer IoT
    TPMS = "tpms"
    WEATHER_STATION = "weather_station"

    # Broadcast
    FM_BROADCAST = "fm_broadcast"
    AM_BROADCAST = "am_broadcast"

    # Aviation
    ADSB = "adsb"

    # Unknown/unclassified
    UNKNOWN = "unknown"


class SecurityPosture(str, Enum):
    """NIST 800-213 aligned security posture.

    Tracks device authentication and authorization status
    for security assessment.
    """

    VERIFIED = "verified"  # Authenticated and authorized
    KNOWN = "known"  # Recognized but not verified
    UNKNOWN = "unknown"  # Unidentified device
    SUSPICIOUS = "suspicious"  # Anomalous behavior detected
    UNAUTHORIZED = "unauthorized"  # Known bad actor


class RiskLevel(str, Enum):
    """Risk classification aligned with NIST CSF.

    Used for prioritizing security response and
    compliance reporting.
    """

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class PurdueLevel(int, Enum):
    """ISA-95/Purdue Model levels for OT asset classification.

    Maps industrial assets to their functional level
    in the control system hierarchy.
    """

    PHYSICAL_PROCESS = 0  # Field devices, sensors
    BASIC_CONTROL = 1  # PLCs, RTUs
    SUPERVISORY = 2  # HMIs, SCADA servers
    SITE_OPERATIONS = 3  # Manufacturing ops
    DMZ = 35  # 3.5 - Security boundary (stored as 35)
    ENTERPRISE_IT = 4  # Business systems
    ENTERPRISE_NETWORK = 5  # Corporate network


class DeviceCategory(str, Enum):
    """NIST device category taxonomy.

    Classifies IoT/OT devices by their primary function
    for inventory management.
    """

    SENSOR = "sensor"  # Data collection
    ACTUATOR = "actuator"  # Physical action
    GATEWAY = "gateway"  # Protocol translation
    HUB = "hub"  # Local coordination
    CONTROLLER = "controller"  # Industrial control
    ENDPOINT = "endpoint"  # General device


# ============================================================================
# Attribute Models
# ============================================================================


class RFAttributes(BaseModel):
    """RF-specific attributes for an asset."""

    frequency_hz: float = Field(..., description="Center frequency in Hz")
    signal_strength_db: float = Field(..., description="Signal strength in dB")
    bandwidth_hz: float | None = Field(default=None, description="Signal bandwidth in Hz")
    modulation_type: str | None = Field(default=None, description="Detected modulation")
    rf_fingerprint_hash: str | None = Field(default=None, description="RF fingerprint for ID")
    rf_protocol: RFProtocol = Field(default=RFProtocol.UNKNOWN, description="Protocol type")


class NetworkAttributes(BaseModel):
    """Network-specific attributes for an asset."""

    mac_address: str | None = Field(default=None, description="MAC address")
    ip_address: str | None = Field(default=None, description="IP address")
    hostname: str | None = Field(default=None, description="Hostname")
    open_ports: list[int] = Field(default_factory=list, description="Open ports")
    vendor: str | None = Field(default=None, description="Vendor from OUI lookup")
    os_guess: str | None = Field(default=None, description="OS fingerprint guess")


# ============================================================================
# Core Models
# ============================================================================


class Asset(BaseModel):
    """Unified device asset model.

    Combines RF and network attributes for comprehensive
    asset tracking with standards compliance fields.
    """

    # Identity
    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique asset ID")
    name: str | None = Field(default=None, description="Asset name/label")
    asset_type: Literal["rf_only", "network_only", "correlated", "unknown"] = Field(
        default="unknown", description="Discovery type"
    )

    # Temporal
    first_seen: datetime = Field(default_factory=datetime.now, description="First observation")
    last_seen: datetime = Field(default_factory=datetime.now, description="Last observation")

    # Correlation
    correlation_confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="RF/network correlation confidence"
    )

    # RF attributes (optional)
    rf_frequency_hz: float | None = Field(default=None, description="RF frequency")
    rf_signal_strength_db: float | None = Field(default=None, description="Signal strength")
    rf_bandwidth_hz: float | None = Field(default=None, description="Bandwidth")
    rf_modulation_type: str | None = Field(default=None, description="Modulation")
    rf_fingerprint_hash: str | None = Field(default=None, description="RF fingerprint")

    # Network attributes (optional)
    net_mac_address: str | None = Field(default=None, description="MAC address")
    net_ip_address: str | None = Field(default=None, description="IP address")
    net_hostname: str | None = Field(default=None, description="Hostname")
    net_open_ports: list[int] = Field(default_factory=list, description="Open ports")
    net_vendor: str | None = Field(default=None, description="Vendor")
    net_os_guess: str | None = Field(default=None, description="OS guess")

    # Provenance
    discovery_source: str | None = Field(default=None, description="How discovered")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    # Standards alignment fields
    cmdb_ci_class: CMDBCIClass | None = Field(default=None, description="ServiceNow CI class")
    cmdb_sys_id: str | None = Field(default=None, description="ServiceNow sys_id when synced")
    rf_protocol: RFProtocol = Field(default=RFProtocol.UNKNOWN, description="RF protocol")
    security_posture: SecurityPosture = Field(
        default=SecurityPosture.UNKNOWN, description="Security status"
    )
    risk_level: RiskLevel = Field(
        default=RiskLevel.INFORMATIONAL, description="Risk classification"
    )
    purdue_level: PurdueLevel | None = Field(default=None, description="ISA-95 Purdue level")
    device_category: DeviceCategory | None = Field(default=None, description="Device function")
    ot_protocol: str | None = Field(default=None, description="OT protocol if applicable")
    ot_criticality: Literal["essential", "important", "standard"] | None = Field(
        default=None, description="OT asset criticality"
    )

    def update_last_seen(self) -> None:
        """Update last_seen to current time."""
        self.last_seen = datetime.now()


class RFCapture(BaseModel):
    """Individual RF signal capture record."""

    capture_id: str = Field(default_factory=lambda: str(uuid4()), description="Capture ID")
    asset_id: str | None = Field(default=None, description="Linked asset ID")
    scan_id: str = Field(..., description="Parent scan session ID")
    frequency_hz: float = Field(..., description="Capture frequency")
    power_db: float = Field(..., description="Signal power in dB")
    timestamp: datetime = Field(default_factory=datetime.now, description="Capture time")
    sigmf_path: Path | None = Field(default=None, description="Path to SigMF recording")
    rf_protocol: RFProtocol | None = Field(default=None, description="Detected protocol")
    annotations: dict[str, Any] = Field(default_factory=dict, description="Signal annotations")


class NetworkScan(BaseModel):
    """Network discovery scan record."""

    scan_id: str = Field(..., description="Parent scan session ID")
    asset_id: str | None = Field(default=None, description="Linked asset ID")
    mac_address: str = Field(..., description="Discovered MAC address")
    ip_address: str | None = Field(default=None, description="IP address")
    timestamp: datetime = Field(default_factory=datetime.now, description="Scan time")
    ports: list[int] = Field(default_factory=list, description="Open ports")
    services: dict[str, str] = Field(default_factory=dict, description="Detected services")


class ScanSession(BaseModel):
    """Scan session metadata."""

    scan_id: str = Field(default_factory=lambda: str(uuid4()), description="Session ID")
    scan_type: Literal["rf_spectrum", "network", "wifi", "iot", "combined"] = Field(
        ..., description="Type of scan"
    )
    start_time: datetime = Field(default_factory=datetime.now, description="Session start")
    end_time: datetime | None = Field(default=None, description="Session end")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Scan parameters")
    results_summary: dict[str, Any] = Field(default_factory=dict, description="Results summary")

    def end_session(self, summary: dict[str, Any] | None = None) -> None:
        """Mark session as ended with optional summary."""
        self.end_time = datetime.now()
        if summary:
            self.results_summary = summary
