"""Domain models and enums for {{ cookiecutter.project_name }}.

Customize these enums for your specific domain.
"""

from enum import Enum


class DataCategory(str, Enum):
    """Categories for data classification.

    Customize these for your domain (e.g., SENSOR, EVENT, METRIC).
    """

    UNKNOWN = "unknown"
    TYPE_A = "type_a"
    TYPE_B = "type_b"
    TYPE_C = "type_c"


class QualityLevel(str, Enum):
    """Data quality levels for silver layer promotion."""

    RAW = "raw"
    VALIDATED = "validated"
    VERIFIED = "verified"
    CERTIFIED = "certified"


class RiskLevel(str, Enum):
    """Risk assessment levels for gold layer."""

    INFORMATIONAL = "informational"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
