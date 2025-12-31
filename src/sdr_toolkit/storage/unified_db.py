"""Unified database for RF and network asset storage.

DuckDB-based storage with Parquet export support.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import duckdb

from sdr_toolkit.storage.models import (
    Asset,
    NetworkScan,
    RFCapture,
    RFProtocol,
    ScanSession,
)

if TYPE_CHECKING:
    from duckdb import DuckDBPyConnection

logger = logging.getLogger(__name__)

# Path to schema.sql relative to this file
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


class UnifiedDB:
    """Unified database for RF and network asset tracking.

    Provides CRUD operations for assets, captures, and scans
    with DuckDB storage and Parquet export.

    Example:
        >>> with UnifiedDB() as db:
        ...     asset = Asset(name="Test Device", asset_type="rf_only")
        ...     asset_id = db.insert_asset(asset)
        ...     retrieved = db.get_asset(asset_id)
    """

    def __init__(self, db_path: Path | str = "data/unified.duckdb") -> None:
        """Initialize database connection.

        Args:
            db_path: Path to DuckDB file. Use ":memory:" for in-memory DB.
        """
        self.db_path = Path(db_path) if db_path != ":memory:" else db_path
        self._conn: DuckDBPyConnection | None = None

        # Create parent directory if needed
        if isinstance(self.db_path, Path):
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def __enter__(self) -> UnifiedDB:
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Context manager exit."""
        self.close()

    def connect(self) -> None:
        """Open database connection and initialize schema."""
        db_path_str = str(self.db_path) if isinstance(self.db_path, Path) else self.db_path
        self._conn = duckdb.connect(db_path_str)
        self.initialize_schema()
        logger.info("Connected to database: %s", db_path_str)

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    @property
    def conn(self) -> DuckDBPyConnection:
        """Get active connection, raising if not connected."""
        if self._conn is None:
            raise RuntimeError("Database not connected. Use context manager or call connect().")
        return self._conn

    def initialize_schema(self) -> None:
        """Create tables from schema.sql if not exists."""
        if SCHEMA_PATH.exists():
            schema_sql = SCHEMA_PATH.read_text()
            self.conn.execute(schema_sql)
            logger.debug("Schema initialized from %s", SCHEMA_PATH)
        else:
            logger.warning("Schema file not found: %s", SCHEMA_PATH)

    # =========================================================================
    # Asset Operations
    # =========================================================================

    def insert_asset(self, asset: Asset) -> str:
        """Insert a new asset.

        Args:
            asset: Asset model to insert.

        Returns:
            Asset ID.
        """
        self.conn.execute(
            """
            INSERT INTO assets (
                id, name, asset_type, first_seen, last_seen, correlation_confidence,
                rf_frequency_hz, rf_signal_strength_db, rf_bandwidth_hz,
                rf_modulation_type, rf_fingerprint_hash,
                net_mac_address, net_ip_address, net_hostname, net_open_ports,
                net_vendor, net_os_guess, discovery_source, metadata,
                cmdb_ci_class, cmdb_sys_id, rf_protocol, security_posture,
                risk_level, purdue_level, device_category, ot_protocol, ot_criticality
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            [
                asset.id,
                asset.name,
                asset.asset_type,
                asset.first_seen,
                asset.last_seen,
                asset.correlation_confidence,
                asset.rf_frequency_hz,
                asset.rf_signal_strength_db,
                asset.rf_bandwidth_hz,
                asset.rf_modulation_type,
                asset.rf_fingerprint_hash,
                asset.net_mac_address,
                asset.net_ip_address,
                asset.net_hostname,
                asset.net_open_ports if asset.net_open_ports else None,
                asset.net_vendor,
                asset.net_os_guess,
                asset.discovery_source,
                json.dumps(asset.metadata) if asset.metadata else None,
                asset.cmdb_ci_class.value if asset.cmdb_ci_class else None,
                asset.cmdb_sys_id,
                asset.rf_protocol.value if asset.rf_protocol else "unknown",
                asset.security_posture.value if asset.security_posture else "unknown",
                asset.risk_level.value if asset.risk_level else "informational",
                asset.purdue_level.value if asset.purdue_level else None,
                asset.device_category.value if asset.device_category else None,
                asset.ot_protocol,
                asset.ot_criticality,
            ],
        )
        logger.debug("Inserted asset: %s", asset.id)
        return asset.id

    def get_asset(self, asset_id: str) -> Asset | None:
        """Get asset by ID.

        Args:
            asset_id: Asset ID to retrieve.

        Returns:
            Asset if found, None otherwise.
        """
        result = self.conn.execute(
            "SELECT * FROM assets WHERE id = ?", [asset_id]
        ).fetchone()

        if result is None:
            return None

        return self._row_to_asset(result)

    def update_asset(self, asset: Asset) -> None:
        """Update existing asset.

        Args:
            asset: Asset with updated fields.
        """
        self.conn.execute(
            """
            UPDATE assets SET
                name = ?, asset_type = ?, last_seen = ?, correlation_confidence = ?,
                rf_frequency_hz = ?, rf_signal_strength_db = ?, rf_bandwidth_hz = ?,
                rf_modulation_type = ?, rf_fingerprint_hash = ?,
                net_mac_address = ?, net_ip_address = ?, net_hostname = ?,
                net_open_ports = ?, net_vendor = ?, net_os_guess = ?,
                discovery_source = ?, metadata = ?,
                cmdb_ci_class = ?, cmdb_sys_id = ?, rf_protocol = ?,
                security_posture = ?, risk_level = ?, purdue_level = ?,
                device_category = ?, ot_protocol = ?, ot_criticality = ?
            WHERE id = ?
            """,
            [
                asset.name,
                asset.asset_type,
                asset.last_seen,
                asset.correlation_confidence,
                asset.rf_frequency_hz,
                asset.rf_signal_strength_db,
                asset.rf_bandwidth_hz,
                asset.rf_modulation_type,
                asset.rf_fingerprint_hash,
                asset.net_mac_address,
                asset.net_ip_address,
                asset.net_hostname,
                asset.net_open_ports if asset.net_open_ports else None,
                asset.net_vendor,
                asset.net_os_guess,
                asset.discovery_source,
                json.dumps(asset.metadata) if asset.metadata else None,
                asset.cmdb_ci_class.value if asset.cmdb_ci_class else None,
                asset.cmdb_sys_id,
                asset.rf_protocol.value if asset.rf_protocol else "unknown",
                asset.security_posture.value if asset.security_posture else "unknown",
                asset.risk_level.value if asset.risk_level else "informational",
                asset.purdue_level.value if asset.purdue_level else None,
                asset.device_category.value if asset.device_category else None,
                asset.ot_protocol,
                asset.ot_criticality,
                asset.id,
            ],
        )
        logger.debug("Updated asset: %s", asset.id)

    def find_assets_by_frequency(
        self,
        freq_hz: float,
        tolerance_hz: float = 100_000,
    ) -> list[Asset]:
        """Find assets near a frequency.

        Args:
            freq_hz: Target frequency in Hz.
            tolerance_hz: Frequency tolerance (default 100 kHz).

        Returns:
            List of matching assets.
        """
        results = self.conn.execute(
            """
            SELECT * FROM assets
            WHERE rf_frequency_hz BETWEEN ? AND ?
            ORDER BY ABS(rf_frequency_hz - ?)
            """,
            [freq_hz - tolerance_hz, freq_hz + tolerance_hz, freq_hz],
        ).fetchall()

        return [self._row_to_asset(row) for row in results]

    def find_assets_by_mac(self, mac: str) -> list[Asset]:
        """Find assets by MAC address.

        Args:
            mac: MAC address (case-insensitive).

        Returns:
            List of matching assets.
        """
        results = self.conn.execute(
            "SELECT * FROM assets WHERE LOWER(net_mac_address) = LOWER(?)",
            [mac],
        ).fetchall()

        return [self._row_to_asset(row) for row in results]

    def find_assets_by_protocol(self, protocol: RFProtocol) -> list[Asset]:
        """Find assets by RF protocol.

        Args:
            protocol: RFProtocol to filter by.

        Returns:
            List of matching assets.
        """
        results = self.conn.execute(
            "SELECT * FROM assets WHERE rf_protocol = ?",
            [protocol.value],
        ).fetchall()

        return [self._row_to_asset(row) for row in results]

    def get_all_assets(self, limit: int = 1000) -> list[Asset]:
        """Get all assets up to limit.

        Args:
            limit: Maximum number of assets to return.

        Returns:
            List of assets.
        """
        results = self.conn.execute(
            "SELECT * FROM assets ORDER BY last_seen DESC LIMIT ?",
            [limit],
        ).fetchall()

        return [self._row_to_asset(row) for row in results]

    def _row_to_asset(self, row: tuple[Any, ...]) -> Asset:
        """Convert database row to Asset model."""
        # Get column names from the connection
        columns = [desc[0] for desc in self.conn.description]
        data = dict(zip(columns, row, strict=False))

        # Parse JSON metadata
        if data.get("metadata"):
            data["metadata"] = json.loads(data["metadata"])
        else:
            data["metadata"] = {}

        # Handle ports array
        if data.get("net_open_ports") is None:
            data["net_open_ports"] = []

        return Asset(**data)

    # =========================================================================
    # RF Capture Operations
    # =========================================================================

    def record_rf_capture(self, capture: RFCapture) -> str:
        """Record an RF signal capture.

        Args:
            capture: RFCapture to store.

        Returns:
            Capture ID.
        """
        self.conn.execute(
            """
            INSERT INTO rf_captures (
                capture_id, asset_id, scan_id, frequency_hz, power_db,
                timestamp, sigmf_path, rf_protocol, annotations
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                capture.capture_id,
                capture.asset_id,
                capture.scan_id,
                capture.frequency_hz,
                capture.power_db,
                capture.timestamp,
                str(capture.sigmf_path) if capture.sigmf_path else None,
                capture.rf_protocol.value if capture.rf_protocol else None,
                json.dumps(capture.annotations) if capture.annotations else None,
            ],
        )
        logger.debug("Recorded RF capture: %s", capture.capture_id)
        return capture.capture_id

    def get_captures_by_scan(self, scan_id: str) -> list[RFCapture]:
        """Get all captures from a scan session.

        Args:
            scan_id: Scan session ID.

        Returns:
            List of RF captures.
        """
        results = self.conn.execute(
            "SELECT * FROM rf_captures WHERE scan_id = ? ORDER BY frequency_hz",
            [scan_id],
        ).fetchall()

        captures = []
        for row in results:
            columns = [desc[0] for desc in self.conn.description]
            data = dict(zip(columns, row, strict=False))
            if data.get("annotations"):
                data["annotations"] = json.loads(data["annotations"])
            else:
                data["annotations"] = {}
            if data.get("sigmf_path"):
                data["sigmf_path"] = Path(data["sigmf_path"])
            captures.append(RFCapture(**data))

        return captures

    # =========================================================================
    # Network Scan Operations
    # =========================================================================

    def record_network_scan(self, scan: NetworkScan) -> None:
        """Record network scan results.

        Args:
            scan: NetworkScan to store.
        """
        self.conn.execute(
            """
            INSERT INTO network_scans (
                scan_id, asset_id, mac_address, ip_address, timestamp, ports, services
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                scan.scan_id,
                scan.asset_id,
                scan.mac_address,
                scan.ip_address,
                scan.timestamp,
                scan.ports if scan.ports else None,
                json.dumps(scan.services) if scan.services else None,
            ],
        )
        logger.debug("Recorded network scan for MAC: %s", scan.mac_address)

    # =========================================================================
    # Scan Session Operations
    # =========================================================================

    def start_scan_session(
        self,
        scan_type: str,
        parameters: dict[str, Any] | None = None,
    ) -> str:
        """Start a new scan session.

        Args:
            scan_type: Type of scan (rf_spectrum, network, wifi, iot, combined).
            parameters: Scan configuration parameters.

        Returns:
            New scan session ID.
        """
        session = ScanSession(
            scan_id=str(uuid4()),
            scan_type=scan_type,  # type: ignore[arg-type]
            parameters=parameters or {},
        )

        self.conn.execute(
            """
            INSERT INTO scan_sessions (scan_id, scan_type, start_time, parameters)
            VALUES (?, ?, ?, ?)
            """,
            [
                session.scan_id,
                session.scan_type,
                session.start_time,
                json.dumps(session.parameters),
            ],
        )
        logger.info("Started scan session: %s (%s)", session.scan_id, scan_type)
        return session.scan_id

    def end_scan_session(self, scan_id: str, summary: dict[str, Any] | None = None) -> None:
        """End a scan session.

        Args:
            scan_id: Session ID to end.
            summary: Results summary to store.
        """
        self.conn.execute(
            """
            UPDATE scan_sessions
            SET end_time = ?, results_summary = ?
            WHERE scan_id = ?
            """,
            [datetime.now(), json.dumps(summary or {}), scan_id],
        )
        logger.info("Ended scan session: %s", scan_id)

    def get_scan_session(self, scan_id: str) -> ScanSession | None:
        """Get scan session by ID.

        Args:
            scan_id: Session ID.

        Returns:
            ScanSession if found.
        """
        result = self.conn.execute(
            "SELECT * FROM scan_sessions WHERE scan_id = ?", [scan_id]
        ).fetchone()

        if result is None:
            return None

        columns = [desc[0] for desc in self.conn.description]
        data = dict(zip(columns, result, strict=False))
        if data.get("parameters"):
            data["parameters"] = json.loads(data["parameters"])
        else:
            data["parameters"] = {}
        if data.get("results_summary"):
            data["results_summary"] = json.loads(data["results_summary"])
        else:
            data["results_summary"] = {}

        return ScanSession(**data)

    # =========================================================================
    # Export Operations
    # =========================================================================

    def export_to_parquet(
        self,
        output_dir: Path,
        tables: list[str] | None = None,
    ) -> dict[str, Path]:
        """Export tables to Parquet files.

        Args:
            output_dir: Directory for output files.
            tables: Tables to export (default: all).

        Returns:
            Dict mapping table names to output paths.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if tables is None:
            tables = ["assets", "rf_captures", "network_scans", "scan_sessions"]

        exported: dict[str, Path] = {}

        for table in tables:
            output_path = output_dir / f"{table}.parquet"
            self.conn.execute(
                f"COPY {table} TO '{output_path}' (FORMAT PARQUET)"  # noqa: S608
            )
            exported[table] = output_path
            logger.info("Exported %s to %s", table, output_path)

        return exported

    def export_assets_csv(self, output_path: Path) -> None:
        """Export assets to CSV.

        Args:
            output_path: Output CSV path.
        """
        self.conn.execute(
            f"COPY assets TO '{output_path}' (FORMAT CSV, HEADER)"  # noqa: S608
        )
        logger.info("Exported assets to %s", output_path)

    # =========================================================================
    # Query Operations
    # =========================================================================

    def query(self, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        """Execute raw SQL query.

        Args:
            sql: SQL query string.
            params: Query parameters.

        Returns:
            List of result rows as dicts.
        """
        result = self.conn.execute(sql, params or [])
        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()

        return [dict(zip(columns, row, strict=False)) for row in rows]

    def get_statistics(self) -> dict[str, Any]:
        """Get database statistics.

        Returns:
            Dict with counts and summaries.
        """
        stats: dict[str, Any] = {}

        # Table counts
        for table in ["assets", "rf_captures", "network_scans", "scan_sessions"]:
            count = self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # noqa: S608
            stats[f"{table}_count"] = count

        # Protocol distribution
        protocol_dist = self.conn.execute(
            """
            SELECT rf_protocol, COUNT(*) as count
            FROM assets
            GROUP BY rf_protocol
            ORDER BY count DESC
            """
        ).fetchall()
        stats["protocol_distribution"] = {row[0]: row[1] for row in protocol_dist}

        # Security posture summary
        security_dist = self.conn.execute(
            """
            SELECT security_posture, COUNT(*) as count
            FROM assets
            GROUP BY security_posture
            """
        ).fetchall()
        stats["security_summary"] = {row[0]: row[1] for row in security_dist}

        return stats
