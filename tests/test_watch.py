"""Tests for autonomous spectrum watch functionality."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

# =============================================================================
# Module Import Tests
# =============================================================================


class TestWatchImports:
    """Test that all watch modules can be imported."""

    def test_notifier_imports(self) -> None:
        """Test notifier module imports."""
        from adws.adw_modules.notifier import (
            ConsoleBackend,
            MultiBackend,
            Notification,
            NotificationPriority,
            NtfyBackend,
            create_notifier,
        )

        assert Notification is not None
        assert NotificationPriority.HIGH.value == 4

    def test_watch_config_imports(self) -> None:
        """Test watch config module imports."""
        from adws.adw_modules.watch_config import (
            Alert,
            AlertCondition,
            FrequencyBand,
            WatchConfig,
            WatchState,
            create_watch_for_band,
            create_watch_for_frequency,
            parse_natural_language,
        )

        assert FrequencyBand.FM_BROADCAST.value == "fm_broadcast"
        assert FrequencyBand.AIRCRAFT_VHF.value == "aircraft_vhf"

    def test_baseline_imports(self) -> None:
        """Test baseline module imports."""
        from adws.adw_modules.baseline import SignalHistory, SpectrumBaseline

        assert SpectrumBaseline is not None

    def test_observability_watch_types(self) -> None:
        """Test observability module watch event types."""
        from adws.adw_modules.observability import AuditEventType, is_frequency_legal

        assert AuditEventType.WATCH_STARTED.value == "watch_started"
        assert AuditEventType.ALERT_TRIGGERED.value == "alert_triggered"


# =============================================================================
# Notification Tests
# =============================================================================


class TestNotification:
    """Test Notification dataclass."""

    def test_notification_defaults(self) -> None:
        """Test notification with default values."""
        from adws.adw_modules.notifier import Notification, NotificationPriority

        n = Notification(title="Test", message="Test message")

        assert n.title == "Test"
        assert n.message == "Test message"
        assert n.priority == NotificationPriority.DEFAULT
        assert n.tags == []
        assert n.data is None

    def test_notification_full(self) -> None:
        """Test notification with all values."""
        from adws.adw_modules.notifier import Notification, NotificationPriority

        n = Notification(
            title="Alert",
            message="Signal detected",
            priority=NotificationPriority.URGENT,
            tags=["sdr", "alert"],
            data={"frequency_hz": 121.5e6},
        )

        assert n.priority == NotificationPriority.URGENT
        assert "sdr" in n.tags
        assert n.data["frequency_hz"] == 121.5e6

    def test_notification_to_dict(self) -> None:
        """Test notification serialization."""
        from adws.adw_modules.notifier import Notification

        n = Notification(title="Test", message="Message", tags=["tag1"])
        d = n.to_dict()

        assert d["title"] == "Test"
        assert d["message"] == "Message"
        assert d["tags"] == ["tag1"]
        assert "timestamp" in d


class TestConsoleBackend:
    """Test ConsoleBackend."""

    @pytest.mark.asyncio
    async def test_console_send(self) -> None:
        """Test console backend sends successfully."""
        from adws.adw_modules.notifier import (
            ConsoleBackend,
            Notification,
            NotificationPriority,
        )

        backend = ConsoleBackend(use_rich=False)
        notification = Notification(
            title="Test",
            message="Test message",
            priority=NotificationPriority.HIGH,
        )

        result = await backend.send(notification)
        assert result is True


class TestMultiBackend:
    """Test MultiBackend."""

    @pytest.mark.asyncio
    async def test_multi_backend_empty(self) -> None:
        """Test multi-backend with no backends."""
        from adws.adw_modules.notifier import MultiBackend, Notification

        multi = MultiBackend([])
        notification = Notification(title="Test", message="Test")

        results = await multi.send(notification)
        assert results == []

    @pytest.mark.asyncio
    async def test_multi_backend_with_console(self) -> None:
        """Test multi-backend with console backend."""
        from adws.adw_modules.notifier import ConsoleBackend, MultiBackend, Notification

        multi = MultiBackend([ConsoleBackend(use_rich=False)])
        notification = Notification(title="Test", message="Test")

        results = await multi.send(notification)
        assert results == [True]


class TestCreateNotifier:
    """Test create_notifier convenience function."""

    def test_create_notifier_console_only(self) -> None:
        """Test creating notifier with console only."""
        from adws.adw_modules.notifier import create_notifier

        notifier = create_notifier(console=True, ntfy_topic=None)
        assert len(notifier.backends) == 1

    def test_create_notifier_with_ntfy(self) -> None:
        """Test creating notifier with ntfy."""
        from adws.adw_modules.notifier import create_notifier

        notifier = create_notifier(console=True, ntfy_topic="test-topic")
        assert len(notifier.backends) == 2


# =============================================================================
# Watch Configuration Tests
# =============================================================================


class TestFrequencyBand:
    """Test FrequencyBand enum."""

    def test_all_bands_have_ranges(self) -> None:
        """Test that all bands have defined ranges."""
        from adws.adw_modules.watch_config import BAND_RANGES, FrequencyBand

        for band in FrequencyBand:
            if band != FrequencyBand.CUSTOM:
                assert band in BAND_RANGES, f"Missing range for {band}"


class TestAlertCondition:
    """Test AlertCondition model."""

    def test_new_signal_condition(self) -> None:
        """Test new signal condition."""
        from adws.adw_modules.watch_config import AlertCondition

        condition = AlertCondition(
            condition_type="new_signal",
            frequency_hz=121.5e6,
            threshold_db=-30,
        )

        assert condition.condition_type == "new_signal"
        assert condition.frequency_hz == 121.5e6
        assert condition.frequency_tolerance_hz == 50000

    def test_condition_describe(self) -> None:
        """Test condition description."""
        from adws.adw_modules.watch_config import AlertCondition

        c1 = AlertCondition(condition_type="new_signal")
        assert "new signal" in c1.describe().lower()

        c2 = AlertCondition(condition_type="threshold_breach", threshold_db=-10)
        assert "-10" in c2.describe()


class TestWatchConfig:
    """Test WatchConfig model."""

    def test_watch_config_defaults(self) -> None:
        """Test watch config with defaults."""
        from adws.adw_modules.watch_config import WatchConfig

        config = WatchConfig(name="test_watch")

        assert config.name == "test_watch"
        assert config.enabled is True
        assert config.scan_interval_seconds == 5.0
        assert config.threshold_db == -30.0

    def test_get_frequency_ranges(self) -> None:
        """Test getting frequency ranges from config."""
        from adws.adw_modules.watch_config import FrequencyBand, WatchConfig

        config = WatchConfig(
            name="test",
            bands=[FrequencyBand.FM_BROADCAST, FrequencyBand.AIRCRAFT_VHF],
        )

        ranges = config.get_frequency_ranges()
        assert len(ranges) == 2

    def test_get_alert_frequencies(self) -> None:
        """Test getting alert frequencies."""
        from adws.adw_modules.watch_config import AlertCondition, WatchConfig

        config = WatchConfig(
            name="test",
            alert_conditions=[
                AlertCondition(condition_type="new_signal", frequency_hz=121.5e6),
                AlertCondition(condition_type="new_signal"),  # No specific freq
            ],
        )

        freqs = config.get_alert_frequencies()
        assert len(freqs) == 1
        assert freqs[0] == 121.5e6


class TestNaturalLanguageParsing:
    """Test natural language intent parsing."""

    def test_parse_aircraft_band(self) -> None:
        """Test parsing aircraft band intent."""
        from adws.adw_modules.watch_config import FrequencyBand, parse_natural_language

        config = parse_natural_language("Watch the aircraft band")

        assert FrequencyBand.AIRCRAFT_VHF in config.bands

    def test_parse_fm_band(self) -> None:
        """Test parsing FM band intent."""
        from adws.adw_modules.watch_config import FrequencyBand, parse_natural_language

        config = parse_natural_language("Monitor FM radio stations")

        assert FrequencyBand.FM_BROADCAST in config.bands

    def test_parse_specific_frequency(self) -> None:
        """Test parsing specific frequency."""
        from adws.adw_modules.watch_config import parse_natural_language

        config = parse_natural_language("Alert me about signals at 121.5 MHz")

        alert_freqs = config.get_alert_frequencies()
        assert len(alert_freqs) == 1
        assert alert_freqs[0] == 121.5e6

    def test_parse_threshold(self) -> None:
        """Test parsing threshold from intent."""
        from adws.adw_modules.watch_config import parse_natural_language

        config = parse_natural_language("Alert if any signal exceeds -10 dB")

        assert config.threshold_db == -10.0

    def test_parse_new_signal_condition(self) -> None:
        """Test parsing new signal detection intent."""
        from adws.adw_modules.watch_config import parse_natural_language

        config = parse_natural_language("Detect any new signals on the aircraft band")

        condition_types = [c.condition_type for c in config.alert_conditions]
        assert "new_signal" in condition_types

    def test_parse_complex_intent(self) -> None:
        """Test parsing complex multi-part intent."""
        from adws.adw_modules.watch_config import FrequencyBand, parse_natural_language

        config = parse_natural_language(
            "Watch aircraft band and alert me if anything appears on 121.5 MHz emergency"
        )

        assert FrequencyBand.AIRCRAFT_VHF in config.bands
        assert 121.5e6 in config.get_alert_frequencies()


class TestCreateWatchForBand:
    """Test create_watch_for_band helper."""

    def test_create_fm_watch(self) -> None:
        """Test creating FM band watch."""
        from adws.adw_modules.watch_config import FrequencyBand, create_watch_for_band

        config = create_watch_for_band(FrequencyBand.FM_BROADCAST, threshold_db=-25)

        assert config.name == "fm_broadcast_watch"
        assert FrequencyBand.FM_BROADCAST in config.bands
        assert config.threshold_db == -25


class TestCreateWatchForFrequency:
    """Test create_watch_for_frequency helper."""

    def test_create_emergency_freq_watch(self) -> None:
        """Test creating watch for emergency frequency."""
        from adws.adw_modules.watch_config import create_watch_for_frequency

        config = create_watch_for_frequency(121.5e6)

        assert "121.5" in config.description or "emergency" in config.name.lower()
        assert len(config.alert_conditions) == 1
        assert config.alert_conditions[0].frequency_hz == 121.5e6


# =============================================================================
# Baseline Tests
# =============================================================================


class TestSpectrumBaseline:
    """Test SpectrumBaseline manager."""

    def test_baseline_init(self) -> None:
        """Test baseline initialization."""
        from adws.adw_modules.baseline import SpectrumBaseline

        baseline = SpectrumBaseline(tolerance_hz=50000, min_scans_required=10)

        assert baseline.tolerance_hz == 50000
        assert baseline.min_scans_required == 10
        assert baseline.established is False

    def test_baseline_add_scan(self) -> None:
        """Test adding scans to baseline."""
        from adws.adw_modules.baseline import SpectrumBaseline
        from rf_asset_discovery.apps.scanner import ScanResult, SignalPeak

        baseline = SpectrumBaseline(min_scans_required=3)

        for _ in range(4):
            result = ScanResult(
                start_freq_hz=87.5e6,
                end_freq_hz=108e6,
                step_hz=200e3,
                peaks=[SignalPeak(frequency_hz=101.9e6, power_db=-20)],
                noise_floor_db=-60,
                scan_time_seconds=1.0,
            )
            baseline.add_scan(result)

        assert baseline.established is True
        assert baseline.scan_count == 4

    def test_baseline_new_signal_detection(self) -> None:
        """Test detecting new signals."""
        from adws.adw_modules.baseline import SpectrumBaseline
        from rf_asset_discovery.apps.scanner import ScanResult, SignalPeak

        baseline = SpectrumBaseline(min_scans_required=3)

        # Establish baseline
        for _ in range(3):
            result = ScanResult(
                start_freq_hz=87.5e6,
                end_freq_hz=108e6,
                step_hz=200e3,
                peaks=[SignalPeak(frequency_hz=101.9e6, power_db=-20)],
                noise_floor_db=-60,
                scan_time_seconds=1.0,
            )
            baseline.add_scan(result)

        # Test new signal
        new_peak = SignalPeak(frequency_hz=93.9e6, power_db=-25)
        assert baseline.is_new_signal(new_peak) is True

        # Test existing signal
        existing_peak = SignalPeak(frequency_hz=101.9e6, power_db=-22)
        assert baseline.is_new_signal(existing_peak) is False

    def test_baseline_power_deviation(self) -> None:
        """Test power deviation calculation."""
        from adws.adw_modules.baseline import SpectrumBaseline
        from rf_asset_discovery.apps.scanner import ScanResult, SignalPeak

        baseline = SpectrumBaseline(min_scans_required=3)

        for _ in range(3):
            result = ScanResult(
                start_freq_hz=87.5e6,
                end_freq_hz=108e6,
                step_hz=200e3,
                peaks=[SignalPeak(frequency_hz=101.9e6, power_db=-20)],
                noise_floor_db=-60,
                scan_time_seconds=1.0,
            )
            baseline.add_scan(result)

        # Check deviation
        peak = SignalPeak(frequency_hz=101.9e6, power_db=-15)
        deviation = baseline.get_power_deviation(peak)

        assert deviation is not None
        assert deviation == 5.0  # -15 - (-20) = 5 dB

    def test_baseline_serialization(self) -> None:
        """Test baseline serialization/deserialization."""
        from adws.adw_modules.baseline import SpectrumBaseline
        from rf_asset_discovery.apps.scanner import ScanResult, SignalPeak

        baseline = SpectrumBaseline(min_scans_required=3)

        for _ in range(3):
            result = ScanResult(
                start_freq_hz=87.5e6,
                end_freq_hz=108e6,
                step_hz=200e3,
                peaks=[SignalPeak(frequency_hz=101.9e6, power_db=-20)],
                noise_floor_db=-60,
                scan_time_seconds=1.0,
            )
            baseline.add_scan(result)

        # Serialize
        data = baseline.to_dict()
        assert data["established"] is True

        # Deserialize
        restored = SpectrumBaseline.from_dict(data)
        assert restored.established is True
        assert restored.scan_count == 3


class TestSignalHistory:
    """Test SignalHistory dataclass."""

    def test_signal_history_average(self) -> None:
        """Test signal history power average."""
        from adws.adw_modules.baseline import SignalHistory

        history = SignalHistory(
            frequency_hz=101.9e6,
            power_samples=[-20, -22, -18],
        )

        assert history.average_power == -20.0

    def test_signal_history_stability(self) -> None:
        """Test signal history stability check."""
        from adws.adw_modules.baseline import SignalHistory

        # Stable signal
        stable = SignalHistory(
            frequency_hz=101.9e6,
            power_samples=[-20, -22, -18],
            consecutive_misses=0,
        )
        assert stable.is_stable is True

        # Unstable signal (not enough samples)
        unstable = SignalHistory(
            frequency_hz=101.9e6,
            power_samples=[-20],
            consecutive_misses=0,
        )
        assert unstable.is_stable is False


# =============================================================================
# Alert Tests
# =============================================================================


class TestAlert:
    """Test Alert model."""

    def test_alert_creation(self) -> None:
        """Test creating an alert."""
        from adws.adw_modules.watch_config import Alert, AlertCondition

        condition = AlertCondition(condition_type="new_signal")
        alert = Alert(
            watch_id="test123",
            condition=condition,
            frequency_hz=121.5e6,
            power_db=-22.4,
            message="New signal at 121.5 MHz",
        )

        assert alert.watch_id == "test123"
        assert alert.frequency_hz == 121.5e6
        assert alert.notified is False

    def test_alert_to_dict(self) -> None:
        """Test alert serialization."""
        from adws.adw_modules.watch_config import Alert, AlertCondition

        condition = AlertCondition(condition_type="new_signal")
        alert = Alert(
            watch_id="test123",
            condition=condition,
            frequency_hz=121.5e6,
            power_db=-22.4,
            message="Test alert",
        )

        d = alert.to_dict()
        assert d["watch_id"] == "test123"
        assert d["frequency_mhz"] == 121.5
        assert d["condition_type"] == "new_signal"


# =============================================================================
# Observability Watch Event Tests
# =============================================================================


class TestAuditEventType:
    """Test watch-related audit event types."""

    def test_watch_event_types_exist(self) -> None:
        """Test that watch event types are defined."""
        from adws.adw_modules.observability import AuditEventType

        assert hasattr(AuditEventType, "WATCH_STARTED")
        assert hasattr(AuditEventType, "WATCH_STOPPED")
        assert hasattr(AuditEventType, "BASELINE_ESTABLISHED")
        assert hasattr(AuditEventType, "ALERT_TRIGGERED")


class TestIsFrequencyLegal:
    """Test is_frequency_legal helper function."""

    def test_fm_frequency_legal(self) -> None:
        """Test FM frequency is legal."""
        from adws.adw_modules.observability import is_frequency_legal

        is_legal, message = is_frequency_legal(101.9e6)
        assert is_legal is True
        assert "FM Broadcast" in message

    def test_aircraft_frequency_legal(self) -> None:
        """Test aircraft frequency is legal."""
        from adws.adw_modules.observability import is_frequency_legal

        is_legal, message = is_frequency_legal(121.5e6)
        assert is_legal is True
        assert "Aircraft" in message


class TestAuditLoggerWatchEvents:
    """Test AuditLogger watch event methods."""

    def test_log_watch_event(self, tmp_path: Path) -> None:
        """Test logging a watch event."""
        from adws.adw_modules.observability import AuditEventType, AuditLogger

        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)

        entry = logger.log_watch_event(
            event_type=AuditEventType.WATCH_STARTED,
            watch_id="test123",
            details={"bands": ["fm_broadcast"]},
        )

        assert entry.operation == "watch_started"
        assert entry.adw_id == "watch_test123"

    def test_log_alert(self, tmp_path: Path) -> None:
        """Test logging an alert."""
        from adws.adw_modules.observability import AuditLogger

        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=log_path)

        entry = logger.log_alert(
            watch_id="test123",
            alert_id="alert456",
            condition_type="new_signal",
            frequency_hz=121.5e6,
            power_db=-22.4,
            message="New signal detected",
            notified=True,
        )

        assert entry.operation == "alert_triggered"
        assert entry.params["frequency_mhz"] == 121.5
