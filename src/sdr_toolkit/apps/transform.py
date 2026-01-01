"""Medallion architecture transformations for SDR Toolkit.

Provides Bronze → Silver → Gold data transformations for the RF discovery data lake.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb

from sdr_toolkit.storage.classification import (
    CMDB_CLASS_CASE_SQL,
    PROTOCOL_CASE_SQL,
    PURDUE_LEVEL_CASE_SQL,
)

logger = logging.getLogger(__name__)


@dataclass
class TransformResult:
    """Result of a medallion transformation."""

    layer: str
    table: str
    rows_created: int
    rows_source: int
    duration_seconds: float
    success: bool
    error: str | None = None


@dataclass
class MedallionStatus:
    """Status of medallion architecture."""

    bronze_tables: dict[str, int]
    silver_tables: dict[str, int]
    gold_tables: dict[str, int]
    schemas_exist: dict[str, bool]


class MedallionTransformer:
    """Medallion architecture transformer for RF discovery data.

    Manages bronze/silver/gold schema creation and data transformations.

    Example:
        >>> transformer = MedallionTransformer("data/unified.duckdb")
        >>> transformer.create_schemas()
        >>> result = transformer.bronze_to_silver(min_power_db=0)
        >>> print(f"Created {result.rows_created} silver records")
    """

    def __init__(self, db_path: Path | str, read_only: bool = False) -> None:
        """Initialize transformer.

        Args:
            db_path: Path to DuckDB database.
            read_only: Open in read-only mode (for status checks).
        """
        self.db_path = Path(db_path)
        self.read_only = read_only
        self._conn: duckdb.DuckDBPyConnection | None = None

    def __enter__(self) -> MedallionTransformer:
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()

    def connect(self) -> None:
        """Open database connection."""
        self._conn = duckdb.connect(str(self.db_path), read_only=self.read_only)
        mode = "read-only" if self.read_only else "read-write"
        logger.info("Connected to: %s (%s)", self.db_path, mode)

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        """Get active connection."""
        if self._conn is None:
            raise RuntimeError("Not connected. Use context manager.")
        return self._conn

    # =========================================================================
    # Schema Management
    # =========================================================================

    def create_schemas(self) -> dict[str, bool]:
        """Create bronze, silver, gold schemas.

        Returns:
            Dict mapping schema names to creation success.
        """
        results = {}
        for schema in ["bronze", "silver", "gold"]:
            try:
                self.conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
                results[schema] = True
                logger.info("Created schema: %s", schema)
            except Exception as e:
                results[schema] = False
                logger.error("Failed to create schema %s: %s", schema, e)
        return results

    def schema_exists(self, schema: str) -> bool:
        """Check if a schema exists.

        Args:
            schema: Schema name to check.

        Returns:
            True if schema exists.
        """
        result = self.conn.execute(
            "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name = ?",
            [schema],
        ).fetchone()
        return result[0] > 0 if result else False

    def get_status(self) -> MedallionStatus:
        """Get current medallion architecture status.

        Returns:
            MedallionStatus with table counts and schema status.
        """

        def get_table_counts(schema: str) -> dict[str, int]:
            if not self.schema_exists(schema):
                return {}
            tables = self.conn.execute(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = ?
                """,
                [schema],
            ).fetchall()
            counts = {}
            for (table,) in tables:
                count = self.conn.execute(
                    f'SELECT COUNT(*) FROM {schema}."{table}"'
                ).fetchone()
                counts[table] = count[0] if count else 0
            return counts

        return MedallionStatus(
            bronze_tables=get_table_counts("bronze"),
            silver_tables=get_table_counts("silver"),
            gold_tables=get_table_counts("gold"),
            schemas_exist={
                "bronze": self.schema_exists("bronze"),
                "silver": self.schema_exists("silver"),
                "gold": self.schema_exists("gold"),
            },
        )

    # =========================================================================
    # Bronze Layer (Raw Ingestion)
    # =========================================================================

    def migrate_to_bronze(self) -> list[TransformResult]:
        """Migrate main schema tables to bronze layer.

        Returns:
            List of transformation results.
        """
        self.create_schemas()

        tables = ["signals", "scan_sessions", "survey_segments", "rf_captures", "network_scans"]
        results = []

        for table in tables:
            start_time = datetime.now()
            try:
                # Check if source table exists
                exists = self.conn.execute(
                    """
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_schema = 'main' AND table_name = ?
                    """,
                    [table],
                ).fetchone()

                if not exists or exists[0] == 0:
                    results.append(
                        TransformResult(
                            layer="bronze",
                            table=table,
                            rows_created=0,
                            rows_source=0,
                            duration_seconds=0,
                            success=False,
                            error=f"Source table {table} not found",
                        )
                    )
                    continue

                # Drop existing bronze table
                self.conn.execute(f'DROP TABLE IF EXISTS bronze."{table}"')

                # Copy to bronze
                self.conn.execute(
                    f'CREATE TABLE bronze."{table}" AS SELECT * FROM main."{table}"'
                )

                # Get row count
                count = self.conn.execute(
                    f'SELECT COUNT(*) FROM bronze."{table}"'
                ).fetchone()
                rows = count[0] if count else 0

                duration = (datetime.now() - start_time).total_seconds()
                results.append(
                    TransformResult(
                        layer="bronze",
                        table=table,
                        rows_created=rows,
                        rows_source=rows,
                        duration_seconds=duration,
                        success=True,
                    )
                )
                logger.info("Migrated %s to bronze.%s (%d rows)", table, table, rows)

            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                results.append(
                    TransformResult(
                        layer="bronze",
                        table=table,
                        rows_created=0,
                        rows_source=0,
                        duration_seconds=duration,
                        success=False,
                        error=str(e),
                    )
                )
                logger.error("Failed to migrate %s: %s", table, e)

        return results

    # =========================================================================
    # Silver Layer (Curated/Verified)
    # =========================================================================

    def bronze_to_silver(
        self,
        min_power_db: float = 0,
        min_detections: int = 1,
        exclude_bands: list[str] | None = None,
        dry_run: bool = False,
    ) -> TransformResult:
        """Transform bronze signals to silver verified_signals.

        Args:
            min_power_db: Minimum power threshold (dB above noise).
            min_detections: Minimum detection count.
            exclude_bands: Bands to exclude (default: unknown, gap).
            dry_run: If True, return count without creating table.

        Returns:
            TransformResult with row counts.
        """
        start_time = datetime.now()
        exclude_bands = exclude_bands or ["unknown", "gap"]
        exclude_list = ", ".join(f"'{b}'" for b in exclude_bands)

        # Check source (try bronze first, fall back to main)
        source_schema = "bronze" if self.schema_exists("bronze") else "main"

        # Build SQL
        sql = f"""
            SELECT
                signal_id,
                frequency_hz,
                power_db,
                bandwidth_hz,
                freq_band,
                detection_count,
                state,
                first_seen,
                last_seen,
                survey_id,
                segment_id,
                {PROTOCOL_CASE_SQL} AS rf_protocol,
                location_name,
                year,
                month
            FROM {source_schema}.signals
            WHERE power_db >= {min_power_db}
              AND detection_count >= {min_detections}
              AND freq_band IS NOT NULL
              AND freq_band NOT IN ({exclude_list})
        """

        try:
            # Count source rows
            count_sql = f"SELECT COUNT(*) FROM ({sql}) sub"
            source_count = self.conn.execute(count_sql).fetchone()[0]

            if dry_run:
                return TransformResult(
                    layer="silver",
                    table="verified_signals",
                    rows_created=0,
                    rows_source=source_count,
                    duration_seconds=(datetime.now() - start_time).total_seconds(),
                    success=True,
                    error="DRY RUN - no changes made",
                )

            # Create silver table
            self.create_schemas()
            self.conn.execute("DROP TABLE IF EXISTS silver.verified_signals")
            self.conn.execute(f"CREATE TABLE silver.verified_signals AS {sql}")

            # Get result count
            result_count = self.conn.execute(
                "SELECT COUNT(*) FROM silver.verified_signals"
            ).fetchone()[0]

            duration = (datetime.now() - start_time).total_seconds()
            logger.info(
                "Created silver.verified_signals: %d rows (from %d bronze)",
                result_count,
                source_count,
            )

            return TransformResult(
                layer="silver",
                table="verified_signals",
                rows_created=result_count,
                rows_source=source_count,
                duration_seconds=duration,
                success=True,
            )

        except Exception as e:
            return TransformResult(
                layer="silver",
                table="verified_signals",
                rows_created=0,
                rows_source=0,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                success=False,
                error=str(e),
            )

    def create_band_inventory(self) -> TransformResult:
        """Create silver.band_inventory aggregation table.

        Returns:
            TransformResult with row counts.
        """
        start_time = datetime.now()
        source_schema = "bronze" if self.schema_exists("bronze") else "main"

        try:
            self.create_schemas()
            self.conn.execute("DROP TABLE IF EXISTS silver.band_inventory")
            self.conn.execute(f"""
                CREATE TABLE silver.band_inventory AS
                SELECT
                    freq_band,
                    COUNT(*) as signal_count,
                    MIN(frequency_hz) as min_freq_hz,
                    MAX(frequency_hz) as max_freq_hz,
                    AVG(power_db) as avg_power_db,
                    MAX(power_db) as max_power_db,
                    MIN(first_seen) as earliest_detection,
                    MAX(last_seen) as latest_detection,
                    SUM(detection_count) as total_detections
                FROM {source_schema}.signals
                WHERE freq_band IS NOT NULL
                GROUP BY freq_band
                ORDER BY signal_count DESC
            """)

            count = self.conn.execute(
                "SELECT COUNT(*) FROM silver.band_inventory"
            ).fetchone()[0]

            duration = (datetime.now() - start_time).total_seconds()
            logger.info("Created silver.band_inventory: %d bands", count)

            return TransformResult(
                layer="silver",
                table="band_inventory",
                rows_created=count,
                rows_source=count,
                duration_seconds=duration,
                success=True,
            )

        except Exception as e:
            return TransformResult(
                layer="silver",
                table="band_inventory",
                rows_created=0,
                rows_source=0,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                success=False,
                error=str(e),
            )

    # =========================================================================
    # Gold Layer (Business-Ready Assets)
    # =========================================================================

    def silver_to_gold(
        self,
        min_power_db: float = 10,
        known_bands_only: bool = True,
        dry_run: bool = False,
    ) -> TransformResult:
        """Transform silver verified_signals to gold assets.

        Args:
            min_power_db: Minimum power for asset creation.
            known_bands_only: Exclude UNKNOWN protocol signals.
            dry_run: If True, return count without creating table.

        Returns:
            TransformResult with row counts.
        """
        start_time = datetime.now()

        # Check silver source
        if not self.schema_exists("silver"):
            return TransformResult(
                layer="gold",
                table="assets",
                rows_created=0,
                rows_source=0,
                duration_seconds=0,
                success=False,
                error="Silver layer not found. Run bronze_to_silver first.",
            )

        # Build SQL
        known_filter = "AND rf_protocol != 'UNKNOWN'" if known_bands_only else ""
        sql = f"""
            SELECT
                gen_random_uuid()::VARCHAR AS id,
                CONCAT(freq_band, '_', CAST(ROUND(frequency_hz/1e6, 1) AS VARCHAR), 'MHz') AS name,
                'RF_EMITTER' AS asset_type,
                first_seen,
                last_seen,
                1.0 AS correlation_confidence,

                -- RF fields
                frequency_hz AS rf_frequency_hz,
                power_db AS rf_signal_strength_db,
                bandwidth_hz AS rf_bandwidth_hz,
                rf_protocol,

                -- CMDB classification
                {CMDB_CLASS_CASE_SQL} AS cmdb_ci_class,

                -- Purdue level
                {PURDUE_LEVEL_CASE_SQL} AS purdue_level,

                -- Security assessment
                CASE
                    WHEN {PURDUE_LEVEL_CASE_SQL} <= 1 THEN 'REQUIRES_REVIEW'
                    ELSE 'COMPLIANT'
                END AS security_posture,

                CASE
                    WHEN {PURDUE_LEVEL_CASE_SQL} <= 1 THEN 'HIGH'
                    WHEN rf_protocol = 'UNKNOWN' THEN 'MEDIUM'
                    ELSE 'LOW'
                END AS risk_level,

                -- Lineage
                signal_id AS source_signal_id,
                location_name

            FROM silver.verified_signals
            WHERE power_db >= {min_power_db}
            {known_filter}
        """

        try:
            # Count source rows
            count_sql = f"SELECT COUNT(*) FROM ({sql}) sub"
            source_count = self.conn.execute(count_sql).fetchone()[0]

            if dry_run:
                return TransformResult(
                    layer="gold",
                    table="assets",
                    rows_created=0,
                    rows_source=source_count,
                    duration_seconds=(datetime.now() - start_time).total_seconds(),
                    success=True,
                    error="DRY RUN - no changes made",
                )

            # Create gold.assets (separate from main.assets)
            self.create_schemas()
            self.conn.execute("DROP TABLE IF EXISTS gold.rf_assets")
            self.conn.execute(f"CREATE TABLE gold.rf_assets AS {sql}")

            # Get result count
            result_count = self.conn.execute(
                "SELECT COUNT(*) FROM gold.rf_assets"
            ).fetchone()[0]

            duration = (datetime.now() - start_time).total_seconds()
            logger.info(
                "Created gold.rf_assets: %d assets (from %d silver)",
                result_count,
                source_count,
            )

            return TransformResult(
                layer="gold",
                table="rf_assets",
                rows_created=result_count,
                rows_source=source_count,
                duration_seconds=duration,
                success=True,
            )

        except Exception as e:
            return TransformResult(
                layer="gold",
                table="rf_assets",
                rows_created=0,
                rows_source=0,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                success=False,
                error=str(e),
            )

    # =========================================================================
    # Full Pipeline
    # =========================================================================

    def run_full_pipeline(
        self,
        min_silver_power: float = 0,
        min_silver_detections: int = 1,
        min_gold_power: float = 10,
        dry_run: bool = False,
    ) -> list[TransformResult]:
        """Run complete bronze → silver → gold pipeline.

        Args:
            min_silver_power: Min power for silver layer.
            min_silver_detections: Min detections for silver layer.
            min_gold_power: Min power for gold layer.
            dry_run: If True, preview without changes.

        Returns:
            List of all transformation results.
        """
        results = []

        # Bronze migration
        if not dry_run:
            bronze_results = self.migrate_to_bronze()
            results.extend(bronze_results)

        # Silver transformation
        silver_result = self.bronze_to_silver(
            min_power_db=min_silver_power,
            min_detections=min_silver_detections,
            dry_run=dry_run,
        )
        results.append(silver_result)

        # Band inventory
        if not dry_run:
            inventory_result = self.create_band_inventory()
            results.append(inventory_result)

        # Gold transformation
        gold_result = self.silver_to_gold(
            min_power_db=min_gold_power,
            dry_run=dry_run,
        )
        results.append(gold_result)

        return results
