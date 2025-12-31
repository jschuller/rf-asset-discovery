"""Observability and compliance module for SDR Toolkit.

Provides:
- Structured audit logging (JSON Lines format)
- Compliance checking for frequency bands
- Session tracking and cost estimation
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# US Legal Frequency Bands (receive-only, no license required)
LEGAL_BANDS_US = [
    (0.5, 1.7, "AM Broadcast"),
    (87.5, 108.0, "FM Broadcast"),
    (108.0, 117.975, "VOR Navigation"),
    (118.0, 137.0, "Aircraft VHF"),
    (137.0, 138.0, "NOAA Satellites"),
    (144.0, 148.0, "Amateur 2m"),
    (156.0, 162.025, "Marine VHF"),
    (162.4, 162.55, "NOAA Weather"),
    (420.0, 450.0, "Amateur 70cm"),
    (462.5625, 467.7125, "FRS/GMRS"),
    (470.0, 608.0, "UHF TV"),
    (824.0, 849.0, "Cellular (850 MHz)"),
    (869.0, 894.0, "Cellular (850 MHz)"),
    (1090.0, 1090.0, "ADS-B"),
]

# Frequencies that require caution or may be encrypted
CAUTION_BANDS = [
    (380.0, 400.0, "Government/Military"),
    (406.0, 420.0, "Federal Land Mobile"),
    (851.0, 869.0, "Public Safety"),
]


@dataclass
class AuditEntry:
    """A single audit log entry."""

    timestamp: str
    adw_id: str
    operation: str
    params: dict[str, Any]
    result: dict[str, Any] | None = None
    duration_seconds: float | None = None
    compliance_status: str = "ok"
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


class AuditLogger:
    """Structured audit logger for SDR operations.

    Logs all operations to a JSON Lines file for later analysis.
    """

    def __init__(
        self,
        log_path: str | Path = "audit.jsonl",
        enabled: bool = True,
    ) -> None:
        """Initialize audit logger.

        Args:
            log_path: Path to the audit log file.
            enabled: Whether logging is enabled.
        """
        self.log_path = Path(log_path)
        self.enabled = enabled

        # Ensure parent directory exists
        if self.enabled:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_operation(
        self,
        adw_id: str,
        operation: str,
        params: dict[str, Any],
        result: dict[str, Any] | None = None,
        duration_seconds: float | None = None,
        compliance_status: str = "ok",
        warnings: list[str] | None = None,
    ) -> AuditEntry:
        """Log an SDR operation.

        Args:
            adw_id: Agentic Developer Workflow ID.
            operation: Operation name (e.g., "scan", "record", "tune").
            params: Operation parameters.
            result: Operation result.
            duration_seconds: How long the operation took.
            compliance_status: "ok", "warning", or "violation".
            warnings: List of warning messages.

        Returns:
            The audit entry that was logged.
        """
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            adw_id=adw_id,
            operation=operation,
            params=params,
            result=result,
            duration_seconds=duration_seconds,
            compliance_status=compliance_status,
            warnings=warnings or [],
        )

        if self.enabled:
            try:
                with open(self.log_path, "a") as f:
                    f.write(entry.to_json() + "\n")
            except Exception as e:
                logger.warning("Failed to write audit log: %s", e)

        return entry

    def log_scan(
        self,
        adw_id: str,
        start_freq_hz: float,
        end_freq_hz: float,
        num_signals: int,
        duration_seconds: float,
    ) -> AuditEntry:
        """Log a spectrum scan operation.

        Args:
            adw_id: Workflow ID.
            start_freq_hz: Start frequency in Hz.
            end_freq_hz: End frequency in Hz.
            num_signals: Number of signals detected.
            duration_seconds: Scan duration.

        Returns:
            The audit entry.
        """
        checker = ComplianceChecker()
        start_ok, start_msg = checker.check_frequency(start_freq_hz / 1e6)
        end_ok, end_msg = checker.check_frequency(end_freq_hz / 1e6)

        warnings = []
        if not start_ok:
            warnings.append(f"Start frequency: {start_msg}")
        if not end_ok:
            warnings.append(f"End frequency: {end_msg}")

        compliance = "ok" if not warnings else "warning"

        return self.log_operation(
            adw_id=adw_id,
            operation="scan",
            params={
                "start_freq_mhz": start_freq_hz / 1e6,
                "end_freq_mhz": end_freq_hz / 1e6,
            },
            result={"num_signals": num_signals},
            duration_seconds=duration_seconds,
            compliance_status=compliance,
            warnings=warnings,
        )

    def log_recording(
        self,
        adw_id: str,
        freq_hz: float,
        duration_seconds: float,
        file_path: str,
        file_size_bytes: int,
    ) -> AuditEntry:
        """Log a signal recording operation.

        Args:
            adw_id: Workflow ID.
            freq_hz: Center frequency in Hz.
            duration_seconds: Recording duration.
            file_path: Path to the recording file.
            file_size_bytes: Size of the recording file.

        Returns:
            The audit entry.
        """
        checker = ComplianceChecker()
        freq_ok, freq_msg = checker.check_frequency(freq_hz / 1e6)

        warnings = []
        if not freq_ok:
            warnings.append(freq_msg)

        compliance = "ok" if not warnings else "warning"

        return self.log_operation(
            adw_id=adw_id,
            operation="record",
            params={"freq_mhz": freq_hz / 1e6},
            result={
                "duration_seconds": duration_seconds,
                "file_path": file_path,
                "file_size_bytes": file_size_bytes,
            },
            duration_seconds=duration_seconds,
            compliance_status=compliance,
            warnings=warnings,
        )

    def get_entries(self, limit: int = 100) -> list[AuditEntry]:
        """Read recent audit entries.

        Args:
            limit: Maximum number of entries to return.

        Returns:
            List of audit entries (most recent first).
        """
        if not self.log_path.exists():
            return []

        entries = []
        with open(self.log_path) as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    entries.append(AuditEntry(**data))
                except Exception:
                    continue

        # Return most recent first
        return entries[-limit:][::-1]


class ComplianceChecker:
    """Check frequency compliance with US regulations.

    Note: This is for informational purposes only.
    Always verify with local regulations.
    """

    def __init__(self) -> None:
        """Initialize compliance checker."""
        self.legal_bands = LEGAL_BANDS_US
        self.caution_bands = CAUTION_BANDS

    def check_frequency(self, freq_mhz: float) -> tuple[bool, str]:
        """Check if a frequency is in a legal receive band.

        Args:
            freq_mhz: Frequency in MHz.

        Returns:
            Tuple of (is_legal, message).
        """
        # Check legal bands
        for start, end, name in self.legal_bands:
            if start <= freq_mhz <= end:
                return True, f"Legal: {name}"

        # Check caution bands
        for start, end, name in self.caution_bands:
            if start <= freq_mhz <= end:
                return False, f"Caution: {name} - verify local regulations"

        # Unknown band
        return False, "Unknown band - verify local regulations"

    def check_range(
        self,
        start_mhz: float,
        end_mhz: float,
    ) -> tuple[bool, list[str]]:
        """Check if a frequency range is compliant.

        Args:
            start_mhz: Start frequency in MHz.
            end_mhz: End frequency in MHz.

        Returns:
            Tuple of (all_ok, list of messages).
        """
        messages = []
        all_ok = True

        # Check endpoints
        start_ok, start_msg = self.check_frequency(start_mhz)
        end_ok, end_msg = self.check_frequency(end_mhz)

        if not start_ok:
            all_ok = False
            messages.append(f"Start ({start_mhz} MHz): {start_msg}")
        else:
            messages.append(f"Start ({start_mhz} MHz): {start_msg}")

        if not end_ok:
            all_ok = False
            messages.append(f"End ({end_mhz} MHz): {end_msg}")
        else:
            messages.append(f"End ({end_mhz} MHz): {end_msg}")

        # Check for caution bands within range
        for start, end, name in self.caution_bands:
            if start_mhz <= end and end_mhz >= start:
                all_ok = False
                messages.append(f"Warning: Range includes {name} ({start}-{end} MHz)")

        return all_ok, messages

    def get_band_info(self, freq_mhz: float) -> dict[str, Any]:
        """Get detailed information about a frequency band.

        Args:
            freq_mhz: Frequency in MHz.

        Returns:
            Dictionary with band information.
        """
        for start, end, name in self.legal_bands:
            if start <= freq_mhz <= end:
                return {
                    "frequency_mhz": freq_mhz,
                    "band_name": name,
                    "band_start_mhz": start,
                    "band_end_mhz": end,
                    "status": "legal",
                    "receive_only": True,
                }

        for start, end, name in self.caution_bands:
            if start <= freq_mhz <= end:
                return {
                    "frequency_mhz": freq_mhz,
                    "band_name": name,
                    "band_start_mhz": start,
                    "band_end_mhz": end,
                    "status": "caution",
                    "receive_only": True,
                    "note": "Verify local regulations",
                }

        return {
            "frequency_mhz": freq_mhz,
            "band_name": "Unknown",
            "status": "unknown",
            "note": "Verify local regulations",
        }


@dataclass
class SessionStats:
    """Statistics for an SDR session."""

    start_time: datetime
    end_time: datetime | None = None
    num_scans: int = 0
    num_recordings: int = 0
    total_scan_time_seconds: float = 0
    total_recording_seconds: float = 0
    total_bytes_recorded: int = 0
    frequencies_accessed: list[float] = field(default_factory=list)
    warnings_count: int = 0

    def add_scan(self, duration_seconds: float, start_mhz: float, end_mhz: float) -> None:
        """Record a scan operation."""
        self.num_scans += 1
        self.total_scan_time_seconds += duration_seconds
        self.frequencies_accessed.extend([start_mhz, end_mhz])

    def add_recording(
        self,
        duration_seconds: float,
        freq_mhz: float,
        size_bytes: int,
    ) -> None:
        """Record a recording operation."""
        self.num_recordings += 1
        self.total_recording_seconds += duration_seconds
        self.total_bytes_recorded += size_bytes
        self.frequencies_accessed.append(freq_mhz)

    def get_summary(self) -> dict[str, Any]:
        """Get session summary."""
        unique_freqs = len(set(self.frequencies_accessed))
        total_time = self.total_scan_time_seconds + self.total_recording_seconds

        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": (
                (self.end_time - self.start_time).total_seconds()
                if self.end_time
                else None
            ),
            "num_scans": self.num_scans,
            "num_recordings": self.num_recordings,
            "total_active_time_seconds": total_time,
            "total_bytes_recorded": self.total_bytes_recorded,
            "unique_frequencies": unique_freqs,
            "warnings_count": self.warnings_count,
        }
