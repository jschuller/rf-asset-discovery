"""Pydantic data models for spectrum survey functionality.

Defines models for multi-segment, resumable spectrum surveys
with ServiceNow-style state management for discovered signals.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


# ============================================================================
# Survey Enums
# ============================================================================


class SurveyStatus(str, Enum):
    """Survey lifecycle status."""

    PENDING = "pending"  # Created but not started
    IN_PROGRESS = "in_progress"  # Actively scanning
    PAUSED = "paused"  # Temporarily stopped, can resume
    COMPLETED = "completed"  # All segments finished
    FAILED = "failed"  # Error occurred


class SegmentStatus(str, Enum):
    """Individual segment scan status."""

    PENDING = "pending"  # Not yet scanned
    IN_PROGRESS = "in_progress"  # Currently scanning
    COMPLETED = "completed"  # Successfully scanned
    FAILED = "failed"  # Error during scan
    SKIPPED = "skipped"  # Intentionally skipped


class SegmentPriority(int, Enum):
    """Segment scan priority (lower = higher priority)."""

    FINE = 1  # Known active bands - detailed scan
    MEDIUM = 2  # Buffer zones around priority bands
    COARSE = 3  # Gap filling with wide steps


# NOTE: SignalState enum moved to models.py
# Import from there: from sdr_toolkit.storage.models import SignalState


# ============================================================================
# Survey Models
# ============================================================================


class SurveySegment(BaseModel):
    """Individual scan segment within a survey.

    Represents a contiguous frequency range to be scanned
    with specific parameters.
    """

    segment_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique segment identifier",
    )
    survey_id: str = Field(..., description="Parent survey ID")

    # Segment definition
    name: str | None = Field(default=None, description="Band or segment name")
    start_freq_hz: float = Field(..., description="Start frequency in Hz")
    end_freq_hz: float = Field(..., description="End frequency in Hz")
    priority: SegmentPriority = Field(
        default=SegmentPriority.COARSE,
        description="Scan priority (1=fine, 3=coarse)",
    )
    step_hz: float = Field(..., description="Frequency step size in Hz")
    dwell_time_ms: float = Field(
        default=100.0,
        description="Time at each frequency in ms",
    )

    # Status tracking
    status: SegmentStatus = Field(
        default=SegmentStatus.PENDING,
        description="Current segment status",
    )
    scan_id: str | None = Field(
        default=None,
        description="Link to scan_sessions when executed",
    )

    # Timing
    scheduled_at: datetime | None = Field(default=None, description="When scheduled")
    started_at: datetime | None = Field(default=None, description="Scan start time")
    completed_at: datetime | None = Field(default=None, description="Scan end time")

    # Results
    signals_found: int = Field(default=0, description="Number of signals detected")
    noise_floor_db: float | None = Field(default=None, description="Measured noise floor")
    scan_time_seconds: float | None = Field(default=None, description="Actual scan duration")
    error_message: str | None = Field(default=None, description="Error if failed")

    @property
    def bandwidth_mhz(self) -> float:
        """Return segment bandwidth in MHz."""
        return (self.end_freq_hz - self.start_freq_hz) / 1e6

    @property
    def estimated_steps(self) -> int:
        """Estimate number of frequency steps."""
        return int((self.end_freq_hz - self.start_freq_hz) / self.step_hz) + 1

    @property
    def estimated_duration_seconds(self) -> float:
        """Estimate scan duration in seconds."""
        # ~150ms per step (dwell + tune + process)
        return self.estimated_steps * 0.15


# NOTE: SurveySignal class removed - use Signal from models.py instead
# Import: from sdr_toolkit.storage.models import Signal, SignalState


class SpectrumSurvey(BaseModel):
    """Multi-segment spectrum survey.

    Represents a comprehensive frequency survey that can
    be paused, resumed, and tracked across sessions.
    """

    survey_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique survey identifier",
    )
    name: str = Field(..., description="Survey name/description")
    status: SurveyStatus = Field(
        default=SurveyStatus.PENDING,
        description="Current survey status",
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Survey creation time",
    )
    started_at: datetime | None = Field(default=None, description="First scan start")
    completed_at: datetime | None = Field(default=None, description="Survey completion")
    last_activity_at: datetime | None = Field(
        default=None,
        description="Last scan activity",
    )

    # Coverage configuration
    start_freq_hz: float = Field(
        default=24e6,
        description="Survey start frequency in Hz",
    )
    end_freq_hz: float = Field(
        default=1766e6,
        description="Survey end frequency in Hz",
    )

    # Progress tracking
    total_segments: int = Field(default=0, description="Total segment count")
    completed_segments: int = Field(default=0, description="Completed segments")
    completion_pct: float = Field(default=0.0, description="Completion percentage")

    # Results
    total_signals_found: int = Field(default=0, description="Total signals detected")
    unique_frequencies: int = Field(default=0, description="Unique frequencies found")

    # Configuration and results
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Survey configuration",
    )
    results_summary: dict[str, Any] = Field(
        default_factory=dict,
        description="Summary of findings",
    )

    # Phase 2: Location/Run Context
    location_name: str | None = Field(default=None, description="Location name")
    location_gps_lat: float | None = Field(default=None, description="GPS latitude")
    location_gps_lon: float | None = Field(default=None, description="GPS longitude")
    environment: str | None = Field(default=None, description="indoor/outdoor/mobile/rooftop")
    antenna_type: str | None = Field(default=None, description="Antenna type")
    sdr_device: str | None = Field(default=None, description="SDR device identifier")
    gain_setting: str | None = Field(default=None, description="Gain setting")
    run_number: int | None = Field(default=None, description="Auto-incremented per location")
    timezone: str | None = Field(default=None, description="Timezone")
    conditions_notes: str | None = Field(default=None, description="Conditions/weather notes")
    baseline_survey_id: str | None = Field(default=None, description="Baseline survey for comparison")

    @property
    def coverage_mhz(self) -> float:
        """Return total coverage in MHz."""
        return (self.end_freq_hz - self.start_freq_hz) / 1e6

    def update_progress(self, completed: int, signals: int) -> None:
        """Update survey progress counters.

        Args:
            completed: Number of completed segments.
            signals: Total signals found.
        """
        self.completed_segments = completed
        self.total_signals_found = signals
        if self.total_segments > 0:
            self.completion_pct = (completed / self.total_segments) * 100
        self.last_activity_at = datetime.now()

    def is_complete(self) -> bool:
        """Check if survey is complete."""
        return self.completed_segments >= self.total_segments


# ============================================================================
# Band Definition Model
# ============================================================================


class BandDefinition(BaseModel):
    """Definition of a frequency band for surveying.

    Used to configure priority bands with appropriate
    scan parameters.
    """

    name: str = Field(..., description="Band name")
    start_hz: float = Field(..., description="Start frequency in Hz")
    end_hz: float = Field(..., description="End frequency in Hz")
    step_hz: float = Field(..., description="Recommended step size in Hz")
    priority: SegmentPriority = Field(
        default=SegmentPriority.FINE,
        description="Scan priority",
    )
    description: str | None = Field(default=None, description="Band description")
    modulation: Literal["fm", "am", "nfm", "wfm", "digital"] | None = Field(
        default=None,
        description="Expected modulation type",
    )

    @property
    def bandwidth_mhz(self) -> float:
        """Return band width in MHz."""
        return (self.end_hz - self.start_hz) / 1e6

    def to_segment(self, survey_id: str) -> SurveySegment:
        """Convert band definition to survey segment.

        Args:
            survey_id: Parent survey ID.

        Returns:
            SurveySegment configured for this band.
        """
        return SurveySegment(
            survey_id=survey_id,
            name=self.name,
            start_freq_hz=self.start_hz,
            end_freq_hz=self.end_hz,
            priority=self.priority,
            step_hz=self.step_hz,
        )


# ============================================================================
# Phase 2: Location Model
# ============================================================================


class SurveyLocation(BaseModel):
    """Reusable location definition for multi-run surveys.

    Enables consistent location tracking across survey runs,
    similar to ServiceNow ITOM discovery locations.
    """

    location_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique location identifier",
    )
    name: str = Field(..., description="Location name (e.g., 'NYC Office')")
    description: str | None = Field(default=None, description="Location description")
    gps_lat: float | None = Field(default=None, description="GPS latitude")
    gps_lon: float | None = Field(default=None, description="GPS longitude")
    environment: Literal["indoor", "outdoor", "mobile", "rooftop"] | None = Field(
        default=None,
        description="Environment type",
    )
    default_antenna: str | None = Field(default=None, description="Default antenna for this location")
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Location creation time",
    )
    last_survey_at: datetime | None = Field(default=None, description="Last survey time")
    total_surveys: int = Field(default=0, description="Total surveys at this location")
