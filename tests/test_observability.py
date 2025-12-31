"""Tests for observability module."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest


class TestAuditLogger:
    """Tests for AuditLogger class."""

    def test_audit_logger_import(self):
        """Test that AuditLogger imports correctly."""
        from adws.adw_modules.observability import AuditLogger

        assert AuditLogger is not None

    def test_audit_logger_init(self, temp_dir: Path):
        """Test AuditLogger initialization."""
        from adws.adw_modules.observability import AuditLogger

        log_path = temp_dir / "test_audit.jsonl"
        logger = AuditLogger(log_path=log_path, enabled=True)

        assert logger.log_path == log_path
        assert logger.enabled is True

    def test_audit_logger_disabled(self, temp_dir: Path):
        """Test disabled AuditLogger."""
        from adws.adw_modules.observability import AuditLogger

        log_path = temp_dir / "test_audit.jsonl"
        logger = AuditLogger(log_path=log_path, enabled=False)

        # Should not write when disabled
        logger.log_operation(
            adw_id="test_001",
            operation="test",
            params={"key": "value"},
        )

        assert not log_path.exists()

    def test_log_operation(self, temp_dir: Path):
        """Test logging an operation."""
        from adws.adw_modules.observability import AuditLogger

        log_path = temp_dir / "test_audit.jsonl"
        logger = AuditLogger(log_path=log_path)

        entry = logger.log_operation(
            adw_id="test_001",
            operation="scan",
            params={"start_mhz": 87.5, "end_mhz": 108.0},
            result={"num_signals": 10},
            duration_seconds=5.5,
        )

        assert entry.adw_id == "test_001"
        assert entry.operation == "scan"
        assert log_path.exists()

        # Verify JSON was written
        with open(log_path) as f:
            line = f.readline()
            data = json.loads(line)
            assert data["adw_id"] == "test_001"
            assert data["operation"] == "scan"

    def test_log_scan(self, temp_dir: Path):
        """Test logging a scan operation."""
        from adws.adw_modules.observability import AuditLogger

        log_path = temp_dir / "test_audit.jsonl"
        logger = AuditLogger(log_path=log_path)

        entry = logger.log_scan(
            adw_id="scan_001",
            start_freq_hz=87.5e6,
            end_freq_hz=108e6,
            num_signals=15,
            duration_seconds=10.0,
        )

        assert entry.operation == "scan"
        assert entry.compliance_status in ["ok", "warning"]

    def test_get_entries(self, temp_dir: Path):
        """Test retrieving entries."""
        from adws.adw_modules.observability import AuditLogger

        log_path = temp_dir / "test_audit.jsonl"
        logger = AuditLogger(log_path=log_path)

        # Log multiple operations
        logger.log_operation(adw_id="test_1", operation="op1", params={})
        logger.log_operation(adw_id="test_2", operation="op2", params={})

        entries = logger.get_entries(limit=10)
        assert len(entries) == 2


class TestComplianceChecker:
    """Tests for ComplianceChecker class."""

    def test_compliance_checker_import(self):
        """Test that ComplianceChecker imports correctly."""
        from adws.adw_modules.observability import ComplianceChecker

        assert ComplianceChecker is not None

    def test_check_fm_frequency(self):
        """Test checking FM broadcast frequency."""
        from adws.adw_modules.observability import ComplianceChecker

        checker = ComplianceChecker()
        is_legal, message = checker.check_frequency(100.1)

        assert is_legal is True
        assert "FM Broadcast" in message

    def test_check_aircraft_frequency(self):
        """Test checking aircraft band frequency."""
        from adws.adw_modules.observability import ComplianceChecker

        checker = ComplianceChecker()
        is_legal, message = checker.check_frequency(119.1)

        assert is_legal is True
        assert "Aircraft" in message

    def test_check_unknown_frequency(self):
        """Test checking unknown frequency."""
        from adws.adw_modules.observability import ComplianceChecker

        checker = ComplianceChecker()
        is_legal, message = checker.check_frequency(50.0)

        # Unknown band - informational only
        assert is_legal is False
        assert "Unknown" in message or "verify" in message.lower()

    def test_check_caution_frequency(self):
        """Test checking caution band frequency."""
        from adws.adw_modules.observability import ComplianceChecker

        checker = ComplianceChecker()
        is_legal, message = checker.check_frequency(390.0)  # Government/Military

        assert is_legal is False
        assert "Caution" in message or "verify" in message.lower()

    def test_check_range(self):
        """Test checking frequency range."""
        from adws.adw_modules.observability import ComplianceChecker

        checker = ComplianceChecker()
        all_ok, messages = checker.check_range(87.5, 108.0)

        assert isinstance(all_ok, bool)
        assert isinstance(messages, list)
        assert len(messages) >= 2  # At least start and end messages

    def test_get_band_info(self):
        """Test getting band information."""
        from adws.adw_modules.observability import ComplianceChecker

        checker = ComplianceChecker()
        info = checker.get_band_info(100.1)

        assert "frequency_mhz" in info
        assert "band_name" in info
        assert "status" in info
        assert info["status"] == "legal"


class TestAuditEntry:
    """Tests for AuditEntry dataclass."""

    def test_audit_entry_to_dict(self):
        """Test converting entry to dictionary."""
        from adws.adw_modules.observability import AuditEntry

        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            adw_id="test_001",
            operation="scan",
            params={"freq": 100.1},
        )

        d = entry.to_dict()
        assert d["adw_id"] == "test_001"
        assert d["operation"] == "scan"

    def test_audit_entry_to_json(self):
        """Test converting entry to JSON."""
        from adws.adw_modules.observability import AuditEntry

        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            adw_id="test_001",
            operation="scan",
            params={"freq": 100.1},
        )

        json_str = entry.to_json()
        parsed = json.loads(json_str)
        assert parsed["adw_id"] == "test_001"


class TestSessionStats:
    """Tests for SessionStats class."""

    def test_session_stats_import(self):
        """Test that SessionStats imports correctly."""
        from adws.adw_modules.observability import SessionStats

        assert SessionStats is not None

    def test_session_stats_init(self):
        """Test SessionStats initialization."""
        from adws.adw_modules.observability import SessionStats

        stats = SessionStats(start_time=datetime.now())
        assert stats.num_scans == 0
        assert stats.num_recordings == 0

    def test_add_scan(self):
        """Test adding a scan."""
        from adws.adw_modules.observability import SessionStats

        stats = SessionStats(start_time=datetime.now())
        stats.add_scan(duration_seconds=5.0, start_mhz=87.5, end_mhz=108.0)

        assert stats.num_scans == 1
        assert stats.total_scan_time_seconds == 5.0

    def test_add_recording(self):
        """Test adding a recording."""
        from adws.adw_modules.observability import SessionStats

        stats = SessionStats(start_time=datetime.now())
        stats.add_recording(duration_seconds=10.0, freq_mhz=100.1, size_bytes=1024000)

        assert stats.num_recordings == 1
        assert stats.total_recording_seconds == 10.0
        assert stats.total_bytes_recorded == 1024000

    def test_get_summary(self):
        """Test getting session summary."""
        from adws.adw_modules.observability import SessionStats

        stats = SessionStats(start_time=datetime.now())
        stats.add_scan(duration_seconds=5.0, start_mhz=87.5, end_mhz=108.0)

        summary = stats.get_summary()
        assert "num_scans" in summary
        assert "num_recordings" in summary
        assert summary["num_scans"] == 1
