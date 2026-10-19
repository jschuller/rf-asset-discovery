"""Tests for autonomous spectrum watch functionality."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from adws.adw_modules.baseline import SpectrumBaseline
    from adws.adw_modules.notifier import MultiBackend
    from adws.adw_modules.watch_config import WatchConfig
    from adws.adw_spectrum_watch import SpectrumWatch
    from rf_asset_discovery.apps.scanner import ScanResult

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


def _fm_scan(
    *freqs_hz: float, start_hz: float = 87.5e6, end_hz: float = 108e6
) -> ScanResult:
    """A ScanResult over the given range with a -20 dB peak at each frequency."""
    from rf_asset_discovery.apps.scanner import ScanResult, SignalPeak

    return ScanResult(
        start_freq_hz=start_hz,
        end_freq_hz=end_hz,
        step_hz=200e3,
        peaks=[SignalPeak(frequency_hz=f, power_db=-20) for f in freqs_hz],
        noise_floor_db=-60,
        scan_time_seconds=1.0,
    )


def _make_watch(
    tmp_path: Path, config: WatchConfig, notifier: MultiBackend | None = None
) -> SpectrumWatch:
    """A SpectrumWatch that keeps its state and audit log under tmp_path."""
    from adws.adw_modules.observability import AuditLogger
    from adws.adw_spectrum_watch import SpectrumWatch

    return SpectrumWatch(
        config,
        notifier=notifier,
        audit_logger=AuditLogger(log_path=tmp_path / "audit.jsonl"),
        state_dir=tmp_path / "state",
    )


class TestSignalLoss:
    """Test signal-loss tracking during the watching phase."""

    def _established_baseline(self) -> SpectrumBaseline:
        from adws.adw_modules.baseline import SpectrumBaseline

        baseline = SpectrumBaseline(min_scans_required=3, miss_threshold=3)
        for _ in range(3):
            baseline.add_scan(_fm_scan(101.9e6, 93.9e6))
        assert baseline.established is True
        return baseline

    def test_signal_reported_missing_after_miss_threshold(self) -> None:
        """Test a baseline signal is reported once absent for miss_threshold scans."""
        baseline = self._established_baseline()

        for _ in range(2):
            scan = _fm_scan(93.9e6)
            baseline.update_presence(scan)
            assert baseline.get_missing_signals(scan) == []

        scan = _fm_scan(93.9e6)
        baseline.update_presence(scan)
        missing = baseline.get_missing_signals(scan)

        assert len(missing) == 1
        freq_hz, last_power = missing[0]
        assert abs(freq_hz - 101.9e6) < baseline.tolerance_hz
        assert last_power == -20.0

    def test_signal_reappearing_resets_misses(self) -> None:
        """Test a signal seen again starts counting misses from zero."""
        baseline = self._established_baseline()

        for _ in range(2):
            baseline.update_presence(_fm_scan(93.9e6))
        baseline.update_presence(_fm_scan(101.9e6, 93.9e6))
        scan = _fm_scan(93.9e6)
        baseline.update_presence(scan)

        assert baseline.get_missing_signals(scan) == []

    def test_scans_of_other_ranges_do_not_count_as_misses(self) -> None:
        """Test only scans covering a signal's frequency affect its misses."""
        baseline = self._established_baseline()
        aircraft = _fm_scan(121.5e6, start_hz=118e6, end_hz=137e6)

        for _ in range(5):
            baseline.update_presence(aircraft)
            assert baseline.get_missing_signals(aircraft) == []

        assert all(s.consecutive_misses == 0 for s in baseline.signals.values())

    def test_update_presence_learns_no_new_signals(self) -> None:
        """Test watching-phase scans do not add signals to the baseline."""
        baseline = self._established_baseline()

        baseline.update_presence(_fm_scan(101.9e6, 93.9e6, 99.5e6))

        assert len(baseline.signals) == 2

    def test_add_scan_counts_misses_only_in_scanned_range(self) -> None:
        """Test baseline-phase scans of another range leave a signal's misses alone."""
        from adws.adw_modules.baseline import SpectrumBaseline

        baseline = SpectrumBaseline(min_scans_required=20)
        baseline.add_scan(_fm_scan(101.9e6))
        (fm_signal,) = baseline.signals.values()

        for _ in range(4):
            baseline.add_scan(_fm_scan(121.5e6, start_hz=118e6, end_hz=137e6))
        assert fm_signal.consecutive_misses == 0

        for _ in range(2):
            baseline.add_scan(_fm_scan())
        assert fm_signal.consecutive_misses == 2

    def test_signal_gone_at_establishment_is_not_reported(self) -> None:
        """Test a signal seen only early in the baseline is not reported lost at once."""
        from adws.adw_modules.baseline import SpectrumBaseline

        baseline = SpectrumBaseline(min_scans_required=12, miss_threshold=3)
        for i in range(12):
            baseline.add_scan(_fm_scan(93.9e6, 101.9e6) if i < 3 else _fm_scan(93.9e6))
        assert baseline.established is True

        scan = _fm_scan(93.9e6)
        baseline.update_presence(scan)
        assert baseline.get_missing_signals(scan) == []

        # Once it comes back, losing it again is reported
        baseline.update_presence(_fm_scan(93.9e6, 101.9e6))
        for _ in range(3):
            baseline.update_presence(scan)
        assert len(baseline.get_missing_signals(scan)) == 1

    @pytest.mark.asyncio
    async def test_lost_signal_alerts_once_per_loss(self, tmp_path: Path) -> None:
        """Test a lost signal alerts once, and again only after it returns and is lost."""
        from adws.adw_modules.notifier import MultiBackend
        from adws.adw_modules.watch_config import AlertCondition, WatchConfig

        config = WatchConfig(
            name="fm",
            custom_range=(87.5e6, 108e6),
            baseline_scans=3,
            alert_conditions=[
                AlertCondition(condition_type="signal_loss", cooldown_seconds=0)
            ],
        )
        watch = _make_watch(tmp_path, config, notifier=MultiBackend([]))
        for _ in range(3):
            await watch._process_baseline_scan(_fm_scan(101.9e6, 93.9e6))

        async def alert_counts(*scans: ScanResult) -> list[int]:
            return [len(await watch._check_alerts(scan)) for scan in scans]

        lost = _fm_scan(93.9e6)
        back = _fm_scan(101.9e6, 93.9e6)

        assert await alert_counts(lost, lost, lost, lost, lost, lost) == [0, 0, 1, 0, 0, 0]
        assert await alert_counts(back, lost, lost, lost, lost) == [0, 0, 0, 1, 0]

    @pytest.mark.asyncio
    async def test_watch_raises_signal_loss_alert(self, tmp_path: Path) -> None:
        """Test SpectrumWatch alerts when a baseline signal disappears."""
        from adws.adw_modules.notifier import MultiBackend
        from adws.adw_modules.watch_config import AlertCondition, WatchConfig

        config = WatchConfig(
            name="fm",
            custom_range=(87.5e6, 108e6),
            baseline_scans=3,
            alert_conditions=[AlertCondition(condition_type="signal_loss")],
        )
        watch = _make_watch(tmp_path, config, notifier=MultiBackend([]))
        for _ in range(3):
            await watch._process_baseline_scan(_fm_scan(101.9e6, 93.9e6))
        assert watch.state.status == "watching"

        assert await watch._check_alerts(_fm_scan(93.9e6)) == []
        assert await watch._check_alerts(_fm_scan(93.9e6)) == []
        alerts = await watch._check_alerts(_fm_scan(93.9e6))

        assert len(alerts) == 1
        assert alerts[0].condition.condition_type == "signal_loss"
        assert "101.9" in alerts[0].message


class TestWatchNotifierSetup:
    """Test SpectrumWatch builds its notifier from config.notifications."""

    def _capture_create_notifier(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> list[str | None]:
        """Record the ntfy_topic of each create_notifier call."""
        import adws.adw_spectrum_watch as watch_module
        from adws.adw_modules.notifier import create_notifier

        topics: list[str | None] = []

        def fake_create_notifier(
            ntfy_topic: str | None = None, console: bool = True
        ) -> MultiBackend:
            topics.append(ntfy_topic)
            return create_notifier(ntfy_topic=ntfy_topic, console=console)

        monkeypatch.setattr(watch_module, "create_notifier", fake_create_notifier)
        return topics

    def test_ntfy_topic_entry_enables_ntfy(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test an "ntfy:<topic>" entry, as the watch helpers add, reaches create_notifier."""
        from adws.adw_modules.notifier import NtfyBackend
        from adws.adw_modules.watch_config import FrequencyBand, create_watch_for_band

        topics = self._capture_create_notifier(monkeypatch)
        config = create_watch_for_band(FrequencyBand.FM_BROADCAST)
        config.notifications.append("ntfy:my-sdr-alerts")

        watch = _make_watch(tmp_path, config)

        assert topics == ["my-sdr-alerts"]
        assert len(watch.notifier.backends) == 2
        assert any(isinstance(b, NtfyBackend) for b in watch.notifier.backends)

    def test_no_ntfy_entry_means_console_only(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test a config without an ntfy entry gets no ntfy backend."""
        from adws.adw_modules.watch_config import WatchConfig

        topics = self._capture_create_notifier(monkeypatch)
        config = WatchConfig(name="fm", custom_range=(87.5e6, 108e6))

        watch = _make_watch(tmp_path, config)

        assert topics == [None]
        assert len(watch.notifier.backends) == 1


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
