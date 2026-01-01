"""Delta Lake storage for signals with time travel.

Provides partitioned storage for RF signal detections with:
- Location-first partitioning (location_name/year/month)
- Time travel queries for baseline comparison
- Version history for audit trails
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)


class DeltaStore:
    """Delta Lake storage for signals with time travel.

    Partitions signals by location_name/year/month for efficient
    location-based queries while supporting time travel for
    baseline comparison.

    Example:
        >>> store = DeltaStore(Path("data/delta"))
        >>> store.write_signals(df)  # Append signals
        >>> current = store.read_signals()  # Latest version
        >>> baseline = store.read_signals(timestamp="2025-12-01")  # Historical
        >>> new_signals = store.compare_versions(1, 2)
    """

    # Partition columns in order (location-first)
    PARTITION_BY = ["location_name", "year", "month"]

    def __init__(self, base_path: Path = Path("data/delta")) -> None:
        """Initialize Delta store.

        Args:
            base_path: Base directory for Delta tables.
        """
        self.base_path = Path(base_path)
        self.signals_path = self.base_path / "signals"

    def write_signals(
        self,
        df: pd.DataFrame,
        mode: str = "append",
    ) -> None:
        """Write signals to Delta table.

        Args:
            df: DataFrame with signal data. Must include partition columns.
            mode: Write mode ('append' or 'overwrite').

        Raises:
            ImportError: If deltalake is not installed.
            ValueError: If required columns are missing.
        """
        try:
            from deltalake import write_deltalake
        except ImportError as e:
            raise ImportError(
                "deltalake not installed. Run: uv pip install deltalake"
            ) from e

        # Validate required columns
        required = {"signal_id", "frequency_hz", "power_db", "survey_id"} | set(
            self.PARTITION_BY
        )
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        # Ensure partition columns are present and correct type
        df = df.copy()
        df["year"] = df["year"].astype(int)
        df["month"] = df["month"].astype(int)
        df["location_name"] = df["location_name"].astype(str)

        # Create directory if needed
        self.signals_path.mkdir(parents=True, exist_ok=True)

        write_deltalake(
            str(self.signals_path),
            df,
            mode=mode,
            partition_by=self.PARTITION_BY,
        )
        logger.info(
            "Wrote %d signals to Delta table at %s",
            len(df),
            self.signals_path,
        )

    def read_signals(
        self,
        version: int | None = None,
        timestamp: str | None = None,
        location: str | None = None,
    ) -> pd.DataFrame:
        """Read signals with optional time travel.

        Args:
            version: Specific version number to read.
            timestamp: Read as of this timestamp (ISO format).
            location: Filter by location name (uses partition pruning).

        Returns:
            DataFrame with signals.

        Raises:
            ImportError: If deltalake is not installed.
            FileNotFoundError: If Delta table doesn't exist.
        """
        try:
            from deltalake import DeltaTable
        except ImportError as e:
            raise ImportError(
                "deltalake not installed. Run: uv pip install deltalake"
            ) from e

        if not self.signals_path.exists():
            raise FileNotFoundError(f"Delta table not found: {self.signals_path}")

        dt = DeltaTable(str(self.signals_path))

        # Apply time travel
        if version is not None:
            dt.load_version(version)
            logger.debug("Loaded version %d", version)
        elif timestamp:
            dt.load_as_of(timestamp)
            logger.debug("Loaded as of %s", timestamp)

        # Read with optional filter
        if location:
            # Use partition filter for efficiency
            return dt.to_pandas(
                filters=[("location_name", "=", location)]
            )

        return dt.to_pandas()

    def history(self) -> list[dict[str, Any]]:
        """Get version history for audit.

        Returns:
            List of version metadata dicts.

        Raises:
            ImportError: If deltalake is not installed.
        """
        try:
            from deltalake import DeltaTable
        except ImportError as e:
            raise ImportError(
                "deltalake not installed. Run: uv pip install deltalake"
            ) from e

        if not self.signals_path.exists():
            return []

        dt = DeltaTable(str(self.signals_path))
        return dt.history()

    def compare_versions(
        self,
        v1: int,
        v2: int,
    ) -> dict[str, Any]:
        """Compare two versions for baseline analysis.

        Args:
            v1: First version (typically baseline).
            v2: Second version (typically current).

        Returns:
            Dict with 'new', 'removed', 'unchanged' signal counts and dataframes.
        """
        df1 = self.read_signals(version=v1)
        df2 = self.read_signals(version=v2)

        # Compare by frequency (within 10 kHz tolerance)
        freq1 = set(df1["frequency_hz"].round(-4))  # Round to 10 kHz
        freq2 = set(df2["frequency_hz"].round(-4))

        new_freqs = freq2 - freq1
        removed_freqs = freq1 - freq2
        unchanged_freqs = freq1 & freq2

        # Get actual signals for new/removed
        new_signals = df2[df2["frequency_hz"].round(-4).isin(new_freqs)]
        removed_signals = df1[df1["frequency_hz"].round(-4).isin(removed_freqs)]

        return {
            "v1": v1,
            "v2": v2,
            "new_count": len(new_freqs),
            "removed_count": len(removed_freqs),
            "unchanged_count": len(unchanged_freqs),
            "new_signals": new_signals,
            "removed_signals": removed_signals,
        }

    def get_locations(self) -> list[str]:
        """Get list of unique locations in the table.

        Returns:
            List of location names.
        """
        try:
            df = self.read_signals()
            return sorted(df["location_name"].unique().tolist())
        except (FileNotFoundError, ImportError):
            return []

    def vacuum(self, retention_hours: int = 168) -> None:
        """Clean up old files to reclaim storage.

        Args:
            retention_hours: Keep files newer than this (default 7 days).
        """
        try:
            from deltalake import DeltaTable
        except ImportError as e:
            raise ImportError(
                "deltalake not installed. Run: uv pip install deltalake"
            ) from e

        if not self.signals_path.exists():
            return

        dt = DeltaTable(str(self.signals_path))
        dt.vacuum(retention_hours=retention_hours, enforce_retention_duration=False)
        logger.info("Vacuumed Delta table with %dh retention", retention_hours)

    def optimize(self) -> None:
        """Optimize table by compacting small files.

        Useful after many small writes to improve read performance.
        """
        try:
            from deltalake import DeltaTable
        except ImportError as e:
            raise ImportError(
                "deltalake not installed. Run: uv pip install deltalake"
            ) from e

        if not self.signals_path.exists():
            return

        dt = DeltaTable(str(self.signals_path))
        dt.optimize.compact()
        logger.info("Optimized Delta table at %s", self.signals_path)


def signals_to_dataframe(signals: list[Any]) -> pd.DataFrame:
    """Convert Signal models to DataFrame for Delta write.

    Args:
        signals: List of Signal model instances.

    Returns:
        DataFrame ready for write_signals().
    """
    import pandas as pd

    records = []
    for sig in signals:
        record = {
            "signal_id": sig.signal_id,
            "frequency_hz": sig.frequency_hz,
            "power_db": sig.power_db,
            "bandwidth_hz": sig.bandwidth_hz,
            "freq_band": sig.freq_band,
            "first_seen": sig.first_seen,
            "last_seen": sig.last_seen,
            "detection_count": sig.detection_count,
            "state": sig.state.value if hasattr(sig.state, "value") else sig.state,
            "survey_id": sig.survey_id,
            "segment_id": sig.segment_id,
            "scan_id": sig.scan_id,
            "sigmf_path": str(sig.sigmf_path) if sig.sigmf_path else None,
            "rf_protocol": (
                sig.rf_protocol.value
                if hasattr(sig.rf_protocol, "value")
                else sig.rf_protocol
            ),
            "notes": sig.notes,
            "promoted_asset_id": sig.promoted_asset_id,
            "location_name": sig.location_name,
            "year": sig.year,
            "month": sig.month,
        }
        records.append(record)

    return pd.DataFrame(records)
