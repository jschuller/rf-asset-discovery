"""Classification and inference logic for {{ cookiecutter.project_name }}.

Pattern: Define mappings as Python dicts, generate SQL CASE statements.
This ensures a single source of truth for classification logic.
"""

from __future__ import annotations

from typing import NamedTuple


class ClassificationInfo(NamedTuple):
    """Classification mapping for domain entities."""

    category: str
    quality_level: str
    risk_level: str
    description: str


# =============================================================================
# Domain Classification Map
# =============================================================================
# Customize this mapping for your domain.
# Keys are source categories, values are classification info.

DOMAIN_MAP: dict[str, ClassificationInfo] = {
    "type_a": ClassificationInfo(
        category="TYPE_A",
        quality_level="validated",
        risk_level="low",
        description="Type A entities",
    ),
    "type_b": ClassificationInfo(
        category="TYPE_B",
        quality_level="verified",
        risk_level="medium",
        description="Type B entities",
    ),
    "type_c": ClassificationInfo(
        category="TYPE_C",
        quality_level="certified",
        risk_level="high",
        description="Type C entities",
    ),
}

DEFAULT_INFO = ClassificationInfo(
    category="UNKNOWN",
    quality_level="raw",
    risk_level="informational",
    description="Unclassified",
)


def get_classification_info(source_category: str | None) -> ClassificationInfo:
    """Get classification info for a source category.

    Args:
        source_category: Source category identifier.

    Returns:
        ClassificationInfo with classification fields.
    """
    if not source_category:
        return DEFAULT_INFO
    return DOMAIN_MAP.get(source_category.lower(), DEFAULT_INFO)


# =============================================================================
# SQL CASE Statement Generation
# =============================================================================

def generate_case_sql(
    mapping: dict[str, ClassificationInfo],
    input_col: str,
    output_field: str,
    default_value: str,
) -> str:
    """Generate SQL CASE statement from Python mapping.

    Args:
        mapping: Classification mapping dictionary.
        input_col: Input column name.
        output_field: Which field to extract (category, quality_level, risk_level).
        default_value: Default value for unmatched cases.

    Returns:
        SQL CASE statement string.
    """
    cases = []
    for key, info in mapping.items():
        value = getattr(info, output_field)
        cases.append(f"    WHEN '{key}' THEN '{value}'")

    return f"""CASE {input_col}
{chr(10).join(cases)}
    ELSE '{default_value}'
END"""


# Pre-generated SQL CASE statements
CATEGORY_CASE_SQL = generate_case_sql(
    DOMAIN_MAP, "source_category", "category", "UNKNOWN"
)

QUALITY_CASE_SQL = generate_case_sql(
    DOMAIN_MAP, "source_category", "quality_level", "raw"
)

RISK_CASE_SQL = generate_case_sql(
    DOMAIN_MAP, "source_category", "risk_level", "informational"
)
