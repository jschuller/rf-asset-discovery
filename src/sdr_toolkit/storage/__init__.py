"""Unified storage layer for RF and network asset tracking.

This module provides DuckDB-based storage for:
- Unified device inventory (RF + network assets)
- Signal captures with SigMF linkage
- Scan session history
- Standards compliance tracking (CMDB, NIST, Purdue)
"""

from __future__ import annotations

from sdr_toolkit.storage.classification import (
    apply_nist_categorization,
    assess_security_posture,
    auto_classify_asset,
    calculate_risk_level,
    infer_cmdb_ci_class,
    infer_device_category,
    infer_purdue_level,
)
from sdr_toolkit.storage.models import (
    Asset,
    CMDBCIClass,
    DeviceCategory,
    NetworkAttributes,
    NetworkScan,
    PurdueLevel,
    RFAttributes,
    RFCapture,
    RFProtocol,
    RiskLevel,
    ScanSession,
    SecurityPosture,
)
from sdr_toolkit.storage.unified_db import UnifiedDB

__all__ = [
    # Main database class
    "UnifiedDB",
    # Core models
    "Asset",
    "RFAttributes",
    "NetworkAttributes",
    "RFCapture",
    "NetworkScan",
    "ScanSession",
    # Enums
    "CMDBCIClass",
    "RFProtocol",
    "SecurityPosture",
    "RiskLevel",
    "PurdueLevel",
    "DeviceCategory",
    # Classification functions
    "infer_cmdb_ci_class",
    "infer_purdue_level",
    "infer_device_category",
    "assess_security_posture",
    "calculate_risk_level",
    "apply_nist_categorization",
    "auto_classify_asset",
]

__version__ = "1.0.0"
