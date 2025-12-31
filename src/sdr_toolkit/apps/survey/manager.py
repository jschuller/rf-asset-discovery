"""Survey lifecycle manager.

Handles creation, persistence, resumption, and status
tracking for spectrum surveys using DuckDB storage.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sdr_toolkit.storage.survey_models import (
    SegmentStatus,
    SignalState,
    SpectrumSurvey,
    SurveySegment,
    SurveySignal,
    SurveyStatus,
)
from sdr_toolkit.apps.survey.band_catalog import (
    RTL_SDR_MIN_HZ,
    RTL_SDR_MAX_HZ,
    generate_full_survey_segments,
    generate_priority_only_segments,
    estimate_survey_duration,
    format_duration,
)

if TYPE_CHECKING:
    from sdr_toolkit.storage.unified_db import UnifiedDB

logger = logging.getLogger(__name__)


class SurveyManager:
    """Manages spectrum survey lifecycle.

    Provides CRUD operations for surveys, segments, and signals
    with DuckDB persistence.

    Example:
        >>> with UnifiedDB() as db:
        ...     manager = SurveyManager(db)
        ...     survey = manager.create_survey("Full Sweep")
        ...     segment = manager.get_next_segment(survey.survey_id)
        ...     # Execute segment...
        ...     manager.complete_segment(segment.segment_id, signals=15)
    """

    def __init__(self, db: UnifiedDB) -> None:
        """Initialize survey manager.

        Args:
            db: UnifiedDB instance for persistence.
        """
        self.db = db

    # =========================================================================
    # Survey CRUD
    # =========================================================================

    def create_survey(
        self,
        name: str,
        start_hz: float = RTL_SDR_MIN_HZ,
        end_hz: float = RTL_SDR_MAX_HZ,
        full_coverage: bool = True,
        coarse_step_hz: float = 2e6,
        # Phase 2: Location/Run Context
        location_name: str | None = None,
        antenna_type: str | None = None,
        conditions_notes: str | None = None,
        baseline_survey_id: str | None = None,
    ) -> SpectrumSurvey:
        """Create a new spectrum survey with segments.

        Args:
            name: Survey name/description.
            start_hz: Start frequency in Hz.
            end_hz: End frequency in Hz.
            full_coverage: Include gap-filling segments.
            coarse_step_hz: Step size for gap segments.
            location_name: Location name for run differentiation.
            antenna_type: Antenna type/description.
            conditions_notes: Weather/conditions notes.
            baseline_survey_id: Baseline survey ID for comparison.

        Returns:
            Created SpectrumSurvey with segments.
        """
        survey_id = str(uuid4())
        now = datetime.now()

        # Phase 2: Auto-increment run_number per location
        run_number = None
        if location_name:
            result = self.db.conn.execute(
                "SELECT COALESCE(MAX(run_number), 0) + 1 FROM spectrum_surveys WHERE location_name = ?",
                [location_name],
            ).fetchone()
            run_number = result[0]

        # Generate segments
        if full_coverage:
            segments = generate_full_survey_segments(
                survey_id=survey_id,
                start_hz=start_hz,
                end_hz=end_hz,
                include_gaps=True,
                coarse_step_hz=coarse_step_hz,
            )
        else:
            segments = generate_priority_only_segments(survey_id)

        # Create survey
        survey = SpectrumSurvey(
            survey_id=survey_id,
            name=name,
            status=SurveyStatus.PENDING,
            created_at=now,
            start_freq_hz=start_hz,
            end_freq_hz=end_hz,
            total_segments=len(segments),
            config={
                "full_coverage": full_coverage,
                "coarse_step_hz": coarse_step_hz,
            },
            # Phase 2: Location/Run Context
            location_name=location_name,
            antenna_type=antenna_type,
            conditions_notes=conditions_notes,
            baseline_survey_id=baseline_survey_id,
            run_number=run_number,
        )

        # Persist survey
        self.db.conn.execute(
            """
            INSERT INTO spectrum_surveys (
                survey_id, name, status, created_at, start_freq_hz, end_freq_hz,
                total_segments, completed_segments, completion_pct,
                total_signals_found, unique_frequencies, config, results_summary,
                location_name, location_gps_lat, location_gps_lon, environment,
                antenna_type, sdr_device, gain_setting, run_number, timezone,
                conditions_notes, baseline_survey_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                survey.survey_id,
                survey.name,
                survey.status.value,
                survey.created_at,
                survey.start_freq_hz,
                survey.end_freq_hz,
                survey.total_segments,
                survey.completed_segments,
                survey.completion_pct,
                survey.total_signals_found,
                survey.unique_frequencies,
                json.dumps(survey.config),
                json.dumps(survey.results_summary),
                # Phase 2 fields
                survey.location_name,
                survey.location_gps_lat,
                survey.location_gps_lon,
                survey.environment,
                survey.antenna_type,
                survey.sdr_device,
                survey.gain_setting,
                survey.run_number,
                survey.timezone,
                survey.conditions_notes,
                survey.baseline_survey_id,
            ],
        )

        # Persist segments
        for segment in segments:
            self._insert_segment(segment)

        logger.info(
            "Created survey '%s' with %d segments (%s estimated)",
            name,
            len(segments),
            format_duration(estimate_survey_duration(segments)),
        )

        return survey

    def get_survey(self, survey_id: str) -> SpectrumSurvey | None:
        """Get survey by ID.

        Args:
            survey_id: Survey ID to retrieve.

        Returns:
            SpectrumSurvey if found, None otherwise.
        """
        result = self.db.conn.execute(
            "SELECT * FROM spectrum_surveys WHERE survey_id = ?",
            [survey_id],
        ).fetchone()

        if result is None:
            return None

        return self._row_to_survey(result)

    def list_surveys(
        self,
        status: SurveyStatus | None = None,
        limit: int = 100,
    ) -> list[SpectrumSurvey]:
        """List surveys with optional status filter.

        Args:
            status: Filter by status (optional).
            limit: Maximum number to return.

        Returns:
            List of SpectrumSurvey objects.
        """
        if status:
            results = self.db.conn.execute(
                """
                SELECT * FROM spectrum_surveys
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                [status.value, limit],
            ).fetchall()
        else:
            results = self.db.conn.execute(
                """
                SELECT * FROM spectrum_surveys
                ORDER BY created_at DESC
                LIMIT ?
                """,
                [limit],
            ).fetchall()

        return [self._row_to_survey(row) for row in results]

    def list_surveys_by_location(
        self,
        location_name: str,
        limit: int = 100,
    ) -> list[SpectrumSurvey]:
        """List surveys at a specific location.

        Args:
            location_name: Location name to filter by.
            limit: Maximum number to return.

        Returns:
            List of SpectrumSurvey objects at the location.
        """
        results = self.db.conn.execute(
            """
            SELECT * FROM spectrum_surveys
            WHERE location_name = ?
            ORDER BY run_number DESC, created_at DESC
            LIMIT ?
            """,
            [location_name, limit],
        ).fetchall()

        return [self._row_to_survey(row) for row in results]

    def update_survey_status(
        self,
        survey_id: str,
        status: SurveyStatus,
    ) -> None:
        """Update survey status.

        Args:
            survey_id: Survey to update.
            status: New status.
        """
        now = datetime.now()

        updates = {"status": status.value, "last_activity_at": now}

        if status == SurveyStatus.IN_PROGRESS:
            self.db.conn.execute(
                """
                UPDATE spectrum_surveys
                SET status = ?, last_activity_at = ?,
                    started_at = COALESCE(started_at, ?)
                WHERE survey_id = ?
                """,
                [status.value, now, now, survey_id],
            )
        elif status == SurveyStatus.COMPLETED:
            self.db.conn.execute(
                """
                UPDATE spectrum_surveys
                SET status = ?, last_activity_at = ?, completed_at = ?
                WHERE survey_id = ?
                """,
                [status.value, now, now, survey_id],
            )
        else:
            self.db.conn.execute(
                """
                UPDATE spectrum_surveys
                SET status = ?, last_activity_at = ?
                WHERE survey_id = ?
                """,
                [status.value, now, survey_id],
            )

        logger.debug("Updated survey %s status to %s", survey_id, status.value)

    def update_survey_progress(
        self,
        survey_id: str,
        completed_segments: int,
        total_signals: int,
    ) -> None:
        """Update survey progress counters.

        Args:
            survey_id: Survey to update.
            completed_segments: Number of completed segments.
            total_signals: Total signals found.
        """
        survey = self.get_survey(survey_id)
        if not survey:
            return

        completion_pct = 0.0
        if survey.total_segments > 0:
            completion_pct = (completed_segments / survey.total_segments) * 100

        self.db.conn.execute(
            """
            UPDATE spectrum_surveys
            SET completed_segments = ?,
                total_signals_found = ?,
                completion_pct = ?,
                last_activity_at = ?
            WHERE survey_id = ?
            """,
            [completed_segments, total_signals, completion_pct, datetime.now(), survey_id],
        )

    # =========================================================================
    # Segment Operations
    # =========================================================================

    def _insert_segment(self, segment: SurveySegment) -> None:
        """Insert a segment into the database.

        Args:
            segment: Segment to insert.
        """
        self.db.conn.execute(
            """
            INSERT INTO survey_segments (
                segment_id, survey_id, name, start_freq_hz, end_freq_hz,
                priority, step_hz, dwell_time_ms, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                segment.segment_id,
                segment.survey_id,
                segment.name,
                segment.start_freq_hz,
                segment.end_freq_hz,
                segment.priority.value,
                segment.step_hz,
                segment.dwell_time_ms,
                segment.status.value,
            ],
        )

    def get_segment(self, segment_id: str) -> SurveySegment | None:
        """Get segment by ID.

        Args:
            segment_id: Segment ID to retrieve.

        Returns:
            SurveySegment if found, None otherwise.
        """
        result = self.db.conn.execute(
            "SELECT * FROM survey_segments WHERE segment_id = ?",
            [segment_id],
        ).fetchone()

        if result is None:
            return None

        return self._row_to_segment(result)

    def get_segments(self, survey_id: str) -> list[SurveySegment]:
        """Get all segments for a survey.

        Args:
            survey_id: Parent survey ID.

        Returns:
            List of SurveySegment objects.
        """
        results = self.db.conn.execute(
            """
            SELECT * FROM survey_segments
            WHERE survey_id = ?
            ORDER BY priority, start_freq_hz
            """,
            [survey_id],
        ).fetchall()

        return [self._row_to_segment(row) for row in results]

    def get_next_segment(self, survey_id: str) -> SurveySegment | None:
        """Get next pending segment for a survey.

        Returns segments in priority order (lower priority value first),
        then by frequency.

        Args:
            survey_id: Survey to get next segment for.

        Returns:
            Next pending SurveySegment or None if complete.
        """
        result = self.db.conn.execute(
            """
            SELECT * FROM survey_segments
            WHERE survey_id = ? AND status = 'pending'
            ORDER BY priority, start_freq_hz
            LIMIT 1
            """,
            [survey_id],
        ).fetchone()

        if result is None:
            return None

        return self._row_to_segment(result)

    def start_segment(self, segment_id: str, scan_id: str | None = None) -> None:
        """Mark segment as in progress.

        Args:
            segment_id: Segment to start.
            scan_id: Optional link to scan_sessions.
        """
        self.db.conn.execute(
            """
            UPDATE survey_segments
            SET status = 'in_progress', started_at = ?, scan_id = ?
            WHERE segment_id = ?
            """,
            [datetime.now(), scan_id, segment_id],
        )

    def complete_segment(
        self,
        segment_id: str,
        signals_found: int = 0,
        noise_floor_db: float | None = None,
        scan_time_seconds: float | None = None,
    ) -> None:
        """Mark segment as completed.

        Args:
            segment_id: Segment to complete.
            signals_found: Number of signals detected.
            noise_floor_db: Measured noise floor.
            scan_time_seconds: Actual scan duration.
        """
        self.db.conn.execute(
            """
            UPDATE survey_segments
            SET status = 'completed',
                completed_at = ?,
                signals_found = ?,
                noise_floor_db = ?,
                scan_time_seconds = ?
            WHERE segment_id = ?
            """,
            [datetime.now(), signals_found, noise_floor_db, scan_time_seconds, segment_id],
        )

        # Update parent survey progress
        segment = self.get_segment(segment_id)
        if segment:
            self._update_survey_from_segment(segment.survey_id)

    def fail_segment(self, segment_id: str, error_message: str) -> None:
        """Mark segment as failed.

        Args:
            segment_id: Segment that failed.
            error_message: Error description.
        """
        self.db.conn.execute(
            """
            UPDATE survey_segments
            SET status = 'failed',
                completed_at = ?,
                error_message = ?
            WHERE segment_id = ?
            """,
            [datetime.now(), error_message, segment_id],
        )

    def _update_survey_from_segment(self, survey_id: str) -> None:
        """Update survey progress after segment completion.

        Args:
            survey_id: Survey to update.
        """
        # Count completed segments and total signals
        stats = self.db.conn.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                SUM(signals_found) as total_signals
            FROM survey_segments
            WHERE survey_id = ?
            """,
            [survey_id],
        ).fetchone()

        completed = stats[0] or 0
        signals = stats[1] or 0

        self.update_survey_progress(survey_id, completed, signals)

        # Check if survey is complete
        survey = self.get_survey(survey_id)
        if survey and completed >= survey.total_segments:
            self.update_survey_status(survey_id, SurveyStatus.COMPLETED)
            logger.info("Survey %s completed", survey_id)

    # =========================================================================
    # Signal Operations
    # =========================================================================

    def record_signal(
        self,
        survey_id: str,
        segment_id: str,
        frequency_hz: float,
        power_db: float,
        bandwidth_hz: float | None = None,
    ) -> SurveySignal:
        """Record a detected signal.

        If a signal at this frequency already exists, updates the detection
        count instead of creating a duplicate.

        Args:
            survey_id: Parent survey ID.
            segment_id: Segment where detected.
            frequency_hz: Signal frequency.
            power_db: Signal power.
            bandwidth_hz: Estimated bandwidth.

        Returns:
            Created or updated SurveySignal.
        """
        # Check for existing signal at this frequency (within 50 kHz)
        existing = self.db.conn.execute(
            """
            SELECT * FROM survey_signals
            WHERE survey_id = ?
              AND ABS(frequency_hz - ?) < 50000
            LIMIT 1
            """,
            [survey_id, frequency_hz],
        ).fetchone()

        now = datetime.now()

        if existing:
            # Update existing signal
            signal_id = existing[0]  # signal_id is first column
            new_count = existing[10] + 1  # detection_count
            new_power = max(existing[4], power_db)  # power_db

            self.db.conn.execute(
                """
                UPDATE survey_signals
                SET last_seen = ?,
                    detection_count = ?,
                    power_db = ?
                WHERE signal_id = ?
                """,
                [now, new_count, new_power, signal_id],
            )

            return self.get_signal(signal_id)  # type: ignore
        else:
            # Create new signal
            signal = SurveySignal(
                survey_id=survey_id,
                segment_id=segment_id,
                frequency_hz=frequency_hz,
                power_db=power_db,
                bandwidth_hz=bandwidth_hz,
                first_seen=now,
                last_seen=now,
            )

            self.db.conn.execute(
                """
                INSERT INTO survey_signals (
                    signal_id, survey_id, segment_id, frequency_hz, power_db,
                    bandwidth_hz, first_seen, last_seen, detection_count, state
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    signal.signal_id,
                    signal.survey_id,
                    signal.segment_id,
                    signal.frequency_hz,
                    signal.power_db,
                    signal.bandwidth_hz,
                    signal.first_seen,
                    signal.last_seen,
                    signal.detection_count,
                    signal.state.value,
                ],
            )

            return signal

    def get_signal(self, signal_id: str) -> SurveySignal | None:
        """Get signal by ID.

        Args:
            signal_id: Signal ID to retrieve.

        Returns:
            SurveySignal if found, None otherwise.
        """
        result = self.db.conn.execute(
            "SELECT * FROM survey_signals WHERE signal_id = ?",
            [signal_id],
        ).fetchone()

        if result is None:
            return None

        return self._row_to_signal(result)

    def get_signals(
        self,
        survey_id: str,
        state: SignalState | None = None,
        min_detections: int = 1,
    ) -> list[SurveySignal]:
        """Get signals for a survey.

        Args:
            survey_id: Survey ID.
            state: Filter by state (optional).
            min_detections: Minimum detection count.

        Returns:
            List of SurveySignal objects.
        """
        if state:
            results = self.db.conn.execute(
                """
                SELECT * FROM survey_signals
                WHERE survey_id = ?
                  AND state = ?
                  AND detection_count >= ?
                ORDER BY frequency_hz
                """,
                [survey_id, state.value, min_detections],
            ).fetchall()
        else:
            results = self.db.conn.execute(
                """
                SELECT * FROM survey_signals
                WHERE survey_id = ?
                  AND detection_count >= ?
                ORDER BY frequency_hz
                """,
                [survey_id, min_detections],
            ).fetchall()

        return [self._row_to_signal(row) for row in results]

    def update_signal_state(self, signal_id: str, state: SignalState) -> None:
        """Update signal state.

        Args:
            signal_id: Signal to update.
            state: New state.
        """
        self.db.conn.execute(
            "UPDATE survey_signals SET state = ? WHERE signal_id = ?",
            [state.value, signal_id],
        )

    # =========================================================================
    # Ralph Integration
    # =========================================================================

    def get_ralph_state(self, survey_id: str) -> dict[str, Any]:
        """Generate state dict for Ralph Wiggum iteration.

        Returns a JSON-serializable dict describing current survey
        state for Ralph loop consumption.

        Args:
            survey_id: Survey ID.

        Returns:
            Dict with survey state and next action.
        """
        survey = self.get_survey(survey_id)
        if not survey:
            return {"error": f"Survey {survey_id} not found"}

        next_segment = self.get_next_segment(survey_id)
        segments = self.get_segments(survey_id)

        # Calculate remaining time
        remaining = [s for s in segments if s.status == SegmentStatus.PENDING]
        remaining_time = estimate_survey_duration(remaining)

        state = {
            "survey_id": survey.survey_id,
            "survey_name": survey.name,
            "status": survey.status.value,
            "progress": {
                "completed_segments": survey.completed_segments,
                "total_segments": survey.total_segments,
                "completion_pct": round(survey.completion_pct, 1),
                "estimated_remaining": format_duration(remaining_time),
            },
            "findings": {
                "total_signals": survey.total_signals_found,
            },
        }

        if next_segment:
            state["current_segment"] = {
                "segment_id": next_segment.segment_id,
                "name": next_segment.name,
                "start_mhz": next_segment.start_freq_hz / 1e6,
                "end_mhz": next_segment.end_freq_hz / 1e6,
                "priority": next_segment.priority.value,
                "estimated_duration": format_duration(next_segment.estimated_duration_seconds),
            }
            state["next_action"] = {
                "type": "execute_segment",
                "command": f"uv run sdr-survey next {survey_id}",
            }
        else:
            state["next_action"] = {
                "type": "complete",
                "message": "Survey complete - all segments scanned",
            }

        return state

    # =========================================================================
    # Row Converters
    # =========================================================================

    def _row_to_survey(self, row: tuple[Any, ...]) -> SpectrumSurvey:
        """Convert database row to SpectrumSurvey."""
        columns = [desc[0] for desc in self.db.conn.description]
        data = dict(zip(columns, row, strict=False))

        # Parse JSON fields
        if data.get("config"):
            data["config"] = json.loads(data["config"]) if isinstance(data["config"], str) else data["config"]
        else:
            data["config"] = {}

        if data.get("results_summary"):
            data["results_summary"] = json.loads(data["results_summary"]) if isinstance(data["results_summary"], str) else data["results_summary"]
        else:
            data["results_summary"] = {}

        # Convert status enum
        data["status"] = SurveyStatus(data["status"])

        return SpectrumSurvey(**data)

    def _row_to_segment(self, row: tuple[Any, ...]) -> SurveySegment:
        """Convert database row to SurveySegment."""
        columns = [desc[0] for desc in self.db.conn.description]
        data = dict(zip(columns, row, strict=False))

        # Convert enums
        from sdr_toolkit.storage.survey_models import SegmentPriority, SegmentStatus
        data["priority"] = SegmentPriority(data["priority"])
        data["status"] = SegmentStatus(data["status"])

        return SurveySegment(**data)

    def _row_to_signal(self, row: tuple[Any, ...]) -> SurveySignal:
        """Convert database row to SurveySignal."""
        columns = [desc[0] for desc in self.db.conn.description]
        data = dict(zip(columns, row, strict=False))

        # Convert state enum
        data["state"] = SignalState(data["state"])

        return SurveySignal(**data)
