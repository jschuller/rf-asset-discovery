"""Bridge ADW workflow results to survey database.

Provides opt-in persistence for agentic workflow results to the
UnifiedDB survey tables, enabling integrated discovery pipelines.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from adws.adw_modules.data_models import (
        AnalysisResult,
        RecordingResult,
        ScanResult,
    )

logger = logging.getLogger(__name__)


def persist_scan_result(
    result: ScanResult,
    db_path: str | Path,
    survey_id: str | None = None,
) -> str | None:
    """Store ADW scan result in database.

    Args:
        result: ScanResult from ADW workflow.
        db_path: Path to UnifiedDB database.
        survey_id: Optional survey ID to link signals.

    Returns:
        Scan session ID if successful, None otherwise.
    """
    try:
        from sdr_toolkit.storage import UnifiedDB
        from sdr_toolkit.storage.models import RFCapture

        with UnifiedDB(Path(db_path)) as db:
            # Start scan session
            scan_id = db.start_scan_session(
                "rf_spectrum",
                {
                    "start_freq_hz": result.start_freq_mhz * 1e6,
                    "end_freq_hz": result.end_freq_mhz * 1e6,
                    "source": "adw",
                    "adw_id": result.adw_id,
                    "survey_id": survey_id,
                },
            )

            # Record each peak as RF capture
            for peak in result.peaks:
                capture = RFCapture(
                    scan_id=scan_id,
                    frequency_hz=peak.frequency_mhz * 1e6,
                    power_db=peak.power_db,
                    annotations={
                        "noise_floor_db": result.noise_floor_db,
                        "snr_db": peak.power_db - result.noise_floor_db,
                        "signal_type": peak.signal_type.value,
                        "bandwidth_khz": peak.bandwidth_khz,
                        "label": peak.label,
                    },
                )
                db.record_rf_capture(capture)

            # End session with summary
            db.end_scan_session(
                scan_id,
                {
                    "signals_found": result.num_signals,
                    "noise_floor_db": result.noise_floor_db,
                    "scan_time_seconds": result.scan_time_seconds,
                },
            )

            logger.info(
                "Persisted scan result %s: %d signals -> %s",
                result.adw_id,
                result.num_signals,
                db_path,
            )
            return scan_id

    except ImportError as e:
        logger.warning("Storage module not available: %s", e)
        return None
    except Exception as e:
        logger.error("Failed to persist scan result: %s", e)
        return None


def persist_recording_result(
    result: RecordingResult,
    db_path: str | Path,
    survey_id: str | None = None,
) -> str | None:
    """Store ADW recording result in database.

    Args:
        result: RecordingResult from ADW workflow.
        db_path: Path to UnifiedDB database.
        survey_id: Optional survey ID for context.

    Returns:
        Scan session ID if successful, None otherwise.
    """
    try:
        from sdr_toolkit.storage import UnifiedDB
        from sdr_toolkit.storage.models import RFCapture

        with UnifiedDB(Path(db_path)) as db:
            # Start scan session
            scan_id = db.start_scan_session(
                "recording",
                {
                    "center_freq_hz": result.center_freq_mhz * 1e6,
                    "source": "adw",
                    "adw_id": result.adw_id,
                    "survey_id": survey_id,
                },
            )

            # Record capture with path
            capture = RFCapture(
                scan_id=scan_id,
                frequency_hz=result.center_freq_mhz * 1e6,
                power_db=0.0,  # Not measured during recording
                sigmf_path=Path(result.recording_path),
                annotations={
                    "duration_seconds": result.duration_seconds,
                    "num_samples": result.num_samples,
                    "sample_rate_hz": result.sample_rate_hz,
                    "format": result.format,
                    "file_size_bytes": result.file_size_bytes,
                },
            )
            db.record_rf_capture(capture)

            # End session
            db.end_scan_session(
                scan_id,
                {
                    "output_path": result.recording_path,
                    "duration_seconds": result.duration_seconds,
                    "num_samples": result.num_samples,
                    "file_size_mb": result.file_size_mb,
                },
            )

            logger.info(
                "Persisted recording %s: %s -> %s",
                result.adw_id,
                result.recording_path,
                db_path,
            )
            return scan_id

    except ImportError as e:
        logger.warning("Storage module not available: %s", e)
        return None
    except Exception as e:
        logger.error("Failed to persist recording result: %s", e)
        return None


def persist_analysis_result(
    result: AnalysisResult,
    db_path: str | Path,
    survey_id: str | None = None,
) -> str | None:
    """Store ADW analysis result in database.

    Args:
        result: AnalysisResult from ADW workflow.
        db_path: Path to UnifiedDB database.
        survey_id: Optional survey ID for context.

    Returns:
        Scan session ID if successful, None otherwise.
    """
    try:
        from sdr_toolkit.storage import UnifiedDB
        from sdr_toolkit.storage.models import RFCapture

        with UnifiedDB(Path(db_path)) as db:
            # Start scan session
            scan_id = db.start_scan_session(
                "analysis",
                {
                    "recording_path": result.recording_path,
                    "analysis_type": result.analysis_type,
                    "source": "adw",
                    "adw_id": result.adw_id,
                    "survey_id": survey_id,
                },
            )

            # Record analysis as capture with annotations
            capture = RFCapture(
                scan_id=scan_id,
                frequency_hz=0.0,  # Unknown without parsing recording
                power_db=result.signal_strength_db,
                sigmf_path=Path(result.recording_path),
                annotations={
                    "signal_type": result.signal_type.value,
                    "snr_db": result.snr_db,
                    "bandwidth_khz": result.bandwidth_khz,
                    "modulation": result.modulation,
                    "summary": result.summary,
                    **result.details,
                },
            )
            db.record_rf_capture(capture)

            # End session
            db.end_scan_session(
                scan_id,
                {
                    "signal_type": result.signal_type.value,
                    "signal_strength_db": result.signal_strength_db,
                    "snr_db": result.snr_db,
                    "summary": result.summary,
                },
            )

            logger.info(
                "Persisted analysis %s: %s -> %s",
                result.adw_id,
                result.recording_path,
                db_path,
            )
            return scan_id

    except ImportError as e:
        logger.warning("Storage module not available: %s", e)
        return None
    except Exception as e:
        logger.error("Failed to persist analysis result: %s", e)
        return None


def check_db_available(db_path: str | Path | None) -> bool:
    """Check if database persistence is available.

    Args:
        db_path: Path to database file.

    Returns:
        True if database can be used, False otherwise.
    """
    if not db_path:
        return False

    try:
        from sdr_toolkit.storage import UnifiedDB

        # Quick connection test
        with UnifiedDB(Path(db_path)) as db:
            db.conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.debug("Database not available: %s", e)
        return False
