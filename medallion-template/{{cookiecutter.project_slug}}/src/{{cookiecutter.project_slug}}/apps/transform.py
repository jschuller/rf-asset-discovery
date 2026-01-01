"""Medallion Architecture Transformer for {{ cookiecutter.project_name }}.

Bronze → Silver → Gold pipeline with quality gates.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import duckdb


@dataclass
class TransformResult:
    """Result of a layer transformation."""

    layer: str
    table: str
    rows_created: int
    rows_source: int
    duration_seconds: float
    success: bool
    error: str | None = None


@dataclass
class MedallionStatus:
    """Current state of medallion layers."""

    bronze_count: int
    silver_count: int
    gold_count: int
    bronze_table: str = "{{ cookiecutter.bronze_table }}"
    silver_table: str = "{{ cookiecutter.silver_table }}"
    gold_table: str = "{{ cookiecutter.gold_table }}"


class MedallionTransformer:
    """Transform data through Bronze → Silver → Gold layers.

    Quality Gates:
    - Bronze → Silver: Validation (e.g., duplicate removal, schema conformance)
    - Silver → Gold: Enrichment (e.g., classification, risk assessment)
    """

    def __init__(self, db_path: Path, read_only: bool = False) -> None:
        """Initialize transformer.

        Args:
            db_path: Path to DuckDB database.
            read_only: If True, open in read-only mode.
        """
        self.db_path = db_path
        self.conn = duckdb.connect(str(db_path), read_only=read_only)

    def __enter__(self) -> "MedallionTransformer":
        return self

    def __exit__(self, *args: object) -> None:
        self.conn.close()

    def create_schemas(self) -> dict[str, bool]:
        """Create medallion schemas if they don't exist.

        Returns:
            Dict mapping schema names to creation success.
        """
        results = {}
        for schema in ["bronze", "silver", "gold"]:
            try:
                self.conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
                results[schema] = True
            except Exception as e:
                results[schema] = False
                print(f"Error creating schema {schema}: {e}")
        return results

    def get_status(self) -> MedallionStatus:
        """Get current record counts for each layer.

        Returns:
            MedallionStatus with layer counts.
        """
        bronze = self._safe_count("bronze", "{{ cookiecutter.bronze_table }}")
        silver = self._safe_count("silver", "{{ cookiecutter.silver_table }}")
        gold = self._safe_count("gold", "{{ cookiecutter.gold_table }}")
        return MedallionStatus(
            bronze_count=bronze,
            silver_count=silver,
            gold_count=gold,
        )

    def _safe_count(self, schema: str, table: str) -> int:
        """Safely count rows in a table.

        Args:
            schema: Schema name.
            table: Table name.

        Returns:
            Row count or 0 if table doesn't exist.
        """
        try:
            result = self.conn.execute(
                f"SELECT COUNT(*) FROM {schema}.{table}"
            ).fetchone()
            return result[0] if result else 0
        except Exception:
            return 0

    def bronze_to_silver(self) -> TransformResult:
        """Transform Bronze → Silver with validation.

        Override this method with your domain-specific validation logic.

        Returns:
            TransformResult with operation details.
        """
        start = time.time()
        try:
            # Example: deduplicate and validate
            # Customize this SQL for your domain
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS silver.{{ cookiecutter.silver_table }} AS
                SELECT DISTINCT * FROM bronze.{{ cookiecutter.bronze_table }}
                WHERE id IS NOT NULL
            """)

            source_count = self._safe_count("bronze", "{{ cookiecutter.bronze_table }}")
            dest_count = self._safe_count("silver", "{{ cookiecutter.silver_table }}")

            return TransformResult(
                layer="bronze_to_silver",
                table="silver.{{ cookiecutter.silver_table }}",
                rows_created=dest_count,
                rows_source=source_count,
                duration_seconds=time.time() - start,
                success=True,
            )
        except Exception as e:
            return TransformResult(
                layer="bronze_to_silver",
                table="silver.{{ cookiecutter.silver_table }}",
                rows_created=0,
                rows_source=0,
                duration_seconds=time.time() - start,
                success=False,
                error=str(e),
            )

    def silver_to_gold(self) -> TransformResult:
        """Transform Silver → Gold with enrichment.

        Override this method with your domain-specific enrichment logic.

        Returns:
            TransformResult with operation details.
        """
        start = time.time()
        try:
            # Example: enrich with classification
            # Customize this SQL for your domain
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS gold.{{ cookiecutter.gold_table }} AS
                SELECT
                    *,
                    'CLASSIFIED' as status,
                    CURRENT_TIMESTAMP as promoted_at
                FROM silver.{{ cookiecutter.silver_table }}
            """)

            source_count = self._safe_count("silver", "{{ cookiecutter.silver_table }}")
            dest_count = self._safe_count("gold", "{{ cookiecutter.gold_table }}")

            return TransformResult(
                layer="silver_to_gold",
                table="gold.{{ cookiecutter.gold_table }}",
                rows_created=dest_count,
                rows_source=source_count,
                duration_seconds=time.time() - start,
                success=True,
            )
        except Exception as e:
            return TransformResult(
                layer="silver_to_gold",
                table="gold.{{ cookiecutter.gold_table }}",
                rows_created=0,
                rows_source=0,
                duration_seconds=time.time() - start,
                success=False,
                error=str(e),
            )

    def run_full_pipeline(self) -> list[TransformResult]:
        """Run complete Bronze → Silver → Gold pipeline.

        Returns:
            List of TransformResults for each layer.
        """
        results = []

        # Ensure schemas exist
        self.create_schemas()

        # Bronze → Silver
        results.append(self.bronze_to_silver())

        # Silver → Gold (only if silver succeeded)
        if results[-1].success:
            results.append(self.silver_to_gold())

        return results
