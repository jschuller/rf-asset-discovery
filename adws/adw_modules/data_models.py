"""Pydantic data models for SDR agentic workflows.

Defines the structure for tasks, results, and workflow states
used throughout the SDR Toolkit agentic system.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


class WorkflowPhase(str, Enum):
    """Phases of an agentic workflow."""

    PLAN = "plan"
    EXECUTE = "execute"
    VERIFY = "verify"
    COMPLETE = "complete"
    FAILED = "failed"


class TaskStatus(str, Enum):
    """Status of a task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class SignalType(str, Enum):
    """Types of detected signals."""

    FM_BROADCAST = "fm_broadcast"
    AM_BROADCAST = "am_broadcast"
    NARROWBAND = "narrowband"
    WIDEBAND = "wideband"
    DIGITAL = "digital"
    UNKNOWN = "unknown"


# ============================================================================
# SDR Task Models
# ============================================================================


class SDRTask(BaseModel):
    """Base model for SDR tasks."""

    adw_id: str = Field(..., description="Unique ADW ID for tracking")
    description: str = Field(..., description="Task description")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    phase: WorkflowPhase = Field(default=WorkflowPhase.PLAN)
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScanTask(SDRTask):
    """Task for spectrum scanning."""

    start_freq_mhz: float = Field(..., description="Start frequency in MHz")
    end_freq_mhz: float = Field(..., description="End frequency in MHz")
    step_khz: float = Field(default=200, description="Step size in kHz")
    threshold_db: float = Field(default=-30, description="Detection threshold in dB")


class RecordTask(SDRTask):
    """Task for signal recording."""

    center_freq_mhz: float = Field(..., description="Center frequency in MHz")
    duration_seconds: float = Field(..., description="Recording duration")
    output_dir: str = Field(default="./recordings")
    format: Literal["sigmf", "wav", "npy"] = Field(default="sigmf")


class AnalyzeTask(SDRTask):
    """Task for signal analysis."""

    recording_path: str = Field(..., description="Path to recording file")
    analysis_type: Literal["spectrum", "demod", "classify"] = Field(default="spectrum")


# ============================================================================
# Result Models
# ============================================================================


class SignalPeak(BaseModel):
    """A detected signal peak."""

    frequency_mhz: float = Field(..., description="Frequency in MHz")
    power_db: float = Field(..., description="Power in dB")
    bandwidth_khz: float | None = None
    signal_type: SignalType = Field(default=SignalType.UNKNOWN)
    label: str | None = None


class ScanResult(BaseModel):
    """Result of a spectrum scan."""

    adw_id: str
    start_freq_mhz: float
    end_freq_mhz: float
    peaks: list[SignalPeak] = Field(default_factory=list)
    noise_floor_db: float = -60.0
    scan_time_seconds: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)

    @property
    def num_signals(self) -> int:
        """Number of detected signals."""
        return len(self.peaks)

    def get_strongest(self, n: int = 5) -> list[SignalPeak]:
        """Get the N strongest signals."""
        return sorted(self.peaks, key=lambda p: p.power_db, reverse=True)[:n]

    def filter_by_type(self, signal_type: SignalType) -> list[SignalPeak]:
        """Filter peaks by signal type."""
        return [p for p in self.peaks if p.signal_type == signal_type]


class RecordingResult(BaseModel):
    """Result of a signal recording."""

    adw_id: str
    recording_path: str
    center_freq_mhz: float
    sample_rate_hz: float
    duration_seconds: float
    num_samples: int
    format: str
    file_size_bytes: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)

    @property
    def file_size_mb(self) -> float:
        """File size in megabytes."""
        return self.file_size_bytes / (1024 * 1024)


class AnalysisResult(BaseModel):
    """Result of signal analysis."""

    adw_id: str
    recording_path: str
    analysis_type: str
    signal_type: SignalType = Field(default=SignalType.UNKNOWN)
    signal_strength_db: float = -60.0
    snr_db: float = 0.0
    bandwidth_khz: float | None = None
    modulation: str | None = None
    summary: str = ""
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


# ============================================================================
# Workflow State Models
# ============================================================================


class WorkflowState(BaseModel):
    """State of a multi-phase workflow."""

    adw_id: str
    workflow_type: Literal["scan", "record", "analyze", "monitor"]
    phase: WorkflowPhase = Field(default=WorkflowPhase.PLAN)
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None
    current_task: SDRTask | None = None
    results: list[BaseModel] = Field(default_factory=list)
    error: str | None = None
    logs: list[str] = Field(default_factory=list)

    def log(self, message: str) -> None:
        """Add a log message."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"[{timestamp}] {message}")

    def advance_phase(self) -> None:
        """Advance to the next workflow phase."""
        phase_order = [
            WorkflowPhase.PLAN,
            WorkflowPhase.EXECUTE,
            WorkflowPhase.VERIFY,
            WorkflowPhase.COMPLETE,
        ]
        current_idx = phase_order.index(self.phase)
        if current_idx < len(phase_order) - 1:
            self.phase = phase_order[current_idx + 1]
            self.log(f"Advanced to phase: {self.phase.value}")

    def fail(self, error: str) -> None:
        """Mark workflow as failed."""
        self.phase = WorkflowPhase.FAILED
        self.status = TaskStatus.FAILED
        self.error = error
        self.log(f"Workflow failed: {error}")

    def complete(self) -> None:
        """Mark workflow as complete."""
        self.phase = WorkflowPhase.COMPLETE
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()
        self.log("Workflow completed successfully")


class WorkflowConfig(BaseModel):
    """Configuration for a workflow."""

    model: Literal["sonnet", "opus", "haiku"] = "sonnet"
    max_retries: int = 3
    timeout_seconds: int = 300
    auto_record: bool = False
    save_results: bool = True
    output_dir: Path = Field(default=Path("./adw_outputs"))

    # Database persistence (opt-in)
    db_path: Path | None = Field(
        default=None,
        description="Path to UnifiedDB for result persistence. If None, results are JSON only.",
    )
    survey_id: str | None = Field(
        default=None,
        description="Survey ID to link results. Requires db_path.",
    )

    @property
    def persist_to_db(self) -> bool:
        """Check if database persistence is enabled."""
        return self.db_path is not None


# ============================================================================
# FM Band Helpers
# ============================================================================


class FMStation(BaseModel):
    """FM broadcast station."""

    frequency_mhz: float
    call_sign: str | None = None
    name: str | None = None
    signal_strength_db: float = -60.0

    def __repr__(self) -> str:
        if self.call_sign:
            return f"FM {self.frequency_mhz:.1f} MHz ({self.call_sign})"
        return f"FM {self.frequency_mhz:.1f} MHz"


def classify_fm_signal(freq_mhz: float, power_db: float) -> SignalPeak:
    """Classify a detected FM broadcast signal."""
    return SignalPeak(
        frequency_mhz=freq_mhz,
        power_db=power_db,
        bandwidth_khz=200,  # FM broadcast bandwidth
        signal_type=SignalType.FM_BROADCAST,
    )
