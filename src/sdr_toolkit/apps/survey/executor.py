"""Survey segment executor.

Executes spectrum scans for survey segments and records
discovered signals with auto-promotion to assets.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any, Callable
from uuid import uuid4

from sdr_toolkit.apps.scanner import ScanResult, SpectrumScanner
from sdr_toolkit.storage.survey_models import (
    SegmentStatus,
    SpectrumSurvey,
    SurveySegment,
    SurveyStatus,
)
from sdr_toolkit.storage.models import Asset, RFProtocol, Signal, SignalState

if TYPE_CHECKING:
    from sdr_toolkit.apps.survey.manager import SurveyManager
    from sdr_toolkit.storage.unified_db import UnifiedDB

logger = logging.getLogger(__name__)

# Minimum detections before auto-promoting signal to asset
AUTO_PROMOTE_THRESHOLD = 3


class SurveyExecutor:
    """Executes survey segments with signal tracking.

    Handles the actual RF scanning for survey segments,
    records discovered signals, and manages auto-promotion
    to persistent assets.

    Example:
        >>> executor = SurveyExecutor(manager, db)
        >>> result = executor.execute_segment(segment)
        >>> print(f"Found {result.signals_found} signals")
    """

    def __init__(
        self,
        manager: SurveyManager,
        db: UnifiedDB,
        scanner: SpectrumScanner | None = None,
    ) -> None:
        """Initialize executor.

        Args:
            manager: SurveyManager for state updates.
            db: UnifiedDB for asset persistence.
            scanner: SpectrumScanner instance (created if None).
        """
        self.manager = manager
        self.db = db
        self.scanner = scanner or SpectrumScanner()

    def execute_segment(
        self,
        segment: SurveySegment,
        auto_promote: bool = True,
    ) -> SegmentResult:
        """Execute a single segment scan.

        Args:
            segment: Segment to scan.
            auto_promote: Whether to auto-promote recurring signals.

        Returns:
            SegmentResult with scan outcome.
        """
        logger.info(
            "Scanning segment: %s (%.1f-%.1f MHz)",
            segment.name or segment.segment_id[:8],
            segment.start_freq_hz / 1e6,
            segment.end_freq_hz / 1e6,
        )

        # Mark segment as in progress
        scan_id = str(uuid4())
        self.manager.start_segment(segment.segment_id, scan_id)

        # Update survey status
        survey = self.manager.get_survey(segment.survey_id)
        if survey and survey.status == SurveyStatus.PENDING:
            self.manager.update_survey_status(segment.survey_id, SurveyStatus.IN_PROGRESS)

        start_time = time.time()

        try:
            # Configure scanner
            self.scanner.threshold_db = -30.0  # Default threshold

            # Execute scan
            scan_result = self.scanner.scan(
                start_freq_hz=segment.start_freq_hz,
                end_freq_hz=segment.end_freq_hz,
                step_hz=segment.step_hz,
                dwell_time_ms=segment.dwell_time_ms,
            )

            scan_time = time.time() - start_time

            # Record signals
            signals_recorded = 0
            for peak in scan_result.peaks:
                self.manager.record_signal(
                    survey_id=segment.survey_id,
                    segment_id=segment.segment_id,
                    frequency_hz=peak.frequency_hz,
                    power_db=peak.power_db,
                    bandwidth_hz=peak.bandwidth_hz,
                )
                signals_recorded += 1

            # Complete segment
            self.manager.complete_segment(
                segment_id=segment.segment_id,
                signals_found=len(scan_result.peaks),
                noise_floor_db=scan_result.noise_floor_db,
                scan_time_seconds=scan_time,
            )

            # Auto-promote signals if enabled
            promoted_count = 0
            if auto_promote:
                promoted_count = self._auto_promote_signals(segment.survey_id)

            logger.info(
                "Segment complete: %d signals found in %.1fs",
                len(scan_result.peaks),
                scan_time,
            )

            return SegmentResult(
                segment_id=segment.segment_id,
                success=True,
                signals_found=len(scan_result.peaks),
                noise_floor_db=scan_result.noise_floor_db,
                scan_time_seconds=scan_time,
                promoted_count=promoted_count,
            )

        except Exception as e:
            error_msg = str(e)
            logger.error("Segment failed: %s", error_msg)

            self.manager.fail_segment(segment.segment_id, error_msg)

            return SegmentResult(
                segment_id=segment.segment_id,
                success=False,
                error=error_msg,
            )

    def execute_next(
        self,
        survey_id: str,
        auto_promote: bool = True,
    ) -> SegmentResult | None:
        """Execute the next pending segment.

        Args:
            survey_id: Survey to continue.
            auto_promote: Whether to auto-promote recurring signals.

        Returns:
            SegmentResult or None if no segments remain.
        """
        segment = self.manager.get_next_segment(survey_id)
        if segment is None:
            logger.info("Survey %s complete - no pending segments", survey_id)
            return None

        return self.execute_segment(segment, auto_promote=auto_promote)

    def run_continuous(
        self,
        survey_id: str,
        max_segments: int | None = None,
        callback: Callable[[SurveySegment, SegmentResult], None] | None = None,
        auto_promote: bool = True,
    ) -> SurveyResult:
        """Run survey continuously until complete or limit reached.

        Args:
            survey_id: Survey to run.
            max_segments: Maximum segments to scan (None = all).
            callback: Optional callback after each segment.
            auto_promote: Whether to auto-promote recurring signals.

        Returns:
            SurveyResult with overall outcome.
        """
        survey = self.manager.get_survey(survey_id)
        if not survey:
            return SurveyResult(
                survey_id=survey_id,
                success=False,
                error=f"Survey {survey_id} not found",
            )

        segments_completed = 0
        total_signals = 0
        errors: list[str] = []

        start_time = time.time()

        while True:
            # Check limits
            if max_segments and segments_completed >= max_segments:
                logger.info("Reached segment limit (%d)", max_segments)
                break

            # Get and execute next segment
            segment = self.manager.get_next_segment(survey_id)
            if segment is None:
                break

            result = self.execute_segment(segment, auto_promote=auto_promote)

            if result.success:
                segments_completed += 1
                total_signals += result.signals_found
            else:
                errors.append(f"{segment.name}: {result.error}")

            # Callback if provided
            if callback:
                callback(segment, result)

        total_time = time.time() - start_time

        # Check final status
        survey = self.manager.get_survey(survey_id)
        complete = survey and survey.status == SurveyStatus.COMPLETED

        return SurveyResult(
            survey_id=survey_id,
            success=len(errors) == 0,
            complete=complete,
            segments_completed=segments_completed,
            total_signals=total_signals,
            total_time_seconds=total_time,
            errors=errors if errors else None,
        )

    def _auto_promote_signals(self, survey_id: str) -> int:
        """Auto-promote signals that meet threshold.

        Args:
            survey_id: Survey to check signals for.

        Returns:
            Number of signals promoted.
        """
        # Get signals eligible for promotion
        signals = self.manager.get_signals(
            survey_id,
            state=SignalState.DISCOVERED,
            min_detections=AUTO_PROMOTE_THRESHOLD,
        )

        promoted = 0
        for signal in signals:
            if signal.should_auto_promote(AUTO_PROMOTE_THRESHOLD):
                asset = self._promote_signal_to_asset(signal)
                if asset:
                    # Update signal state
                    self.manager.update_signal_state(signal.signal_id, SignalState.PROMOTED)
                    self.db.conn.execute(
                        "UPDATE survey_signals SET promoted_asset_id = ? WHERE signal_id = ?",
                        [asset.id, signal.signal_id],
                    )
                    promoted += 1
                    logger.info(
                        "Auto-promoted signal at %.3f MHz to asset %s",
                        signal.frequency_mhz,
                        asset.id[:8],
                    )

        return promoted

    def _promote_signal_to_asset(self, signal: Signal) -> Asset | None:
        """Create an asset from a recurring signal.

        Args:
            signal: Signal to promote.

        Returns:
            Created Asset or None on failure.
        """
        try:
            # Check if asset already exists at this frequency
            existing = self.db.find_assets_by_frequency(
                signal.frequency_hz,
                tolerance_hz=50000,
            )
            if existing:
                # Update existing asset
                asset = existing[0]
                asset.update_last_seen()
                if signal.power_db > (asset.rf_signal_strength_db or -100):
                    asset.rf_signal_strength_db = signal.power_db
                self.db.update_asset(asset)
                return asset

            # Create new asset
            freq_mhz = signal.frequency_hz / 1e6
            asset = Asset(
                name=f"Signal at {freq_mhz:.3f} MHz",
                asset_type="rf_only",
                rf_frequency_hz=signal.frequency_hz,
                rf_signal_strength_db=signal.power_db,
                rf_bandwidth_hz=signal.bandwidth_hz,
                rf_protocol=RFProtocol.UNKNOWN,
                discovery_source="spectrum_survey",
                metadata={
                    "survey_id": signal.survey_id,
                    "detection_count": signal.detection_count,
                    "first_seen": signal.first_seen.isoformat(),
                },
            )

            self.db.insert_asset(asset)
            return asset

        except Exception as e:
            logger.error("Failed to promote signal: %s", e)
            return None


class SegmentResult:
    """Result of a segment scan."""

    def __init__(
        self,
        segment_id: str,
        success: bool,
        signals_found: int = 0,
        noise_floor_db: float | None = None,
        scan_time_seconds: float | None = None,
        promoted_count: int = 0,
        error: str | None = None,
    ) -> None:
        self.segment_id = segment_id
        self.success = success
        self.signals_found = signals_found
        self.noise_floor_db = noise_floor_db
        self.scan_time_seconds = scan_time_seconds
        self.promoted_count = promoted_count
        self.error = error

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "segment_id": self.segment_id,
            "success": self.success,
            "signals_found": self.signals_found,
            "noise_floor_db": self.noise_floor_db,
            "scan_time_seconds": self.scan_time_seconds,
            "promoted_count": self.promoted_count,
            "error": self.error,
        }


class SurveyResult:
    """Result of a survey execution."""

    def __init__(
        self,
        survey_id: str,
        success: bool,
        complete: bool = False,
        segments_completed: int = 0,
        total_signals: int = 0,
        total_time_seconds: float = 0,
        errors: list[str] | None = None,
    ) -> None:
        self.survey_id = survey_id
        self.success = success
        self.complete = complete
        self.segments_completed = segments_completed
        self.total_signals = total_signals
        self.total_time_seconds = total_time_seconds
        self.errors = errors or []

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "survey_id": self.survey_id,
            "success": self.success,
            "complete": self.complete,
            "segments_completed": self.segments_completed,
            "total_signals": self.total_signals,
            "total_time_seconds": self.total_time_seconds,
            "errors": self.errors,
        }
