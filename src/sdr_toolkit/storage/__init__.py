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
    RFProtocol,
    RiskLevel,
    ScanSession,
    SecurityPosture,
    Signal,
    SignalState,
    derive_freq_band,
)
from sdr_toolkit.storage.unified_db import UnifiedDB

# Delta Lake support (optional dependency)
try:
    from sdr_toolkit.storage.delta_store import DeltaStore, signals_to_dataframe
except ImportError:
    DeltaStore = None  # type: ignore[misc, assignment]
    signals_to_dataframe = None  # type: ignore[misc, assignment]

__all__ = [
    # Main database class
    "UnifiedDB",
    # Delta Lake (optional)
    "DeltaStore",
    "signals_to_dataframe",
    # Core models
    "Asset",
    "RFAttributes",
    "NetworkAttributes",
    "Signal",
    "SignalState",
    "NetworkScan",
    "ScanSession",
    # Helper functions
    "derive_freq_band",
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
