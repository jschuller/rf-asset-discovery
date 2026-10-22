"""Autonomous Spectrum Watch - Claude-orchestrated continuous monitoring.

Provides continuous spectrum monitoring with:
- Natural language watch configuration
- Automatic baseline establishment
- Multi-condition alerting (new signals, threshold breaches, etc.)
- Multiple notification backends (ntfy.sh, console)
- State persistence for restart resilience
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import signal
from datetime import datetime
from pathlib import Path
from typing import Any

from rf_asset_discovery.apps.scanner import ScanResult, SpectrumScanner

from .adw_modules.baseline import RangeBaselines
from .adw_modules.notifier import (
    MultiBackend,
    Notification,
    NotificationPriority,
    create_notifier,
)
from .adw_modules.observability import AuditLogger
from .adw_modules.watch_config import (
    Alert,
    AlertCondition,
    FrequencyBand,
    WatchConfig,
    WatchState,
    create_watch_for_band,
    create_watch_for_frequency,
    is_emergency_frequency,
    lookup_notable,
    parse_natural_language,
)

logger = logging.getLogger(__name__)


class SpectrumWatch:
    """Autonomous spectrum monitoring with alerting.

    Continuously scans configured frequency ranges, establishes a baseline
    of normal activity, and sends alerts when anomalies are detected.

    Example:
        >>> config = parse_natural_language("Watch aircraft band, alert on 121.5 MHz")
        >>> watch = SpectrumWatch(config)
        >>> await watch.start()
        >>> # ... monitoring runs until stopped
        >>> await watch.stop()

    State Machine:
        IDLE -> BASELINE -> WATCHING -> ALERTING -> WATCHING
                    |          |
                    v          v
                 PAUSED     PAUSED
                    |          |
                    v          v
                 STOPPED   STOPPED
    """

    def __init__(
        self,
        config: WatchConfig,
        notifier: MultiBackend | None = None,
        audit_logger: AuditLogger | None = None,
        state_dir: Path | None = None,
    ) -> None:
        """Initialize spectrum watch.

        Args:
            config: Watch configuration.
            notifier: Notification backend (created from config if None).
            audit_logger: Audit logger instance.
            state_dir: Directory for state persistence.
        """
        self.config = config
        self.state = WatchState(config=config)
        # One baseline per scanned range, so bands do not share scan counts,
        # signals or power history
        self.baseline = RangeBaselines(
            ranges=config.get_frequency_ranges(),
            min_scans_required=config.baseline_scans,
        )

        # Create scanner
        self.scanner = SpectrumScanner(
            threshold_db=config.threshold_db,
        )

        # Setup notifier
        if notifier is not None:
            self.notifier = notifier
        else:
            # The watch helpers add the topic as an "ntfy:<topic>" entry
            ntfy_topic = next(
                (
                    n.split(":", 1)[1]
                    for n in config.notifications
                    if n.startswith("ntfy:")
                ),
                None,
            )
            self.notifier = create_notifier(
                ntfy_topic=ntfy_topic,
                console="console" in config.notifications,
            )

        # Setup audit logger
        self.audit_logger = audit_logger or AuditLogger(
            log_path=Path("watch_audit.jsonl"),
        )

        # State persistence
        self.state_dir = state_dir or Path.home() / ".rf-asset-discovery" / "watches"
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Runtime state
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._alert_cooldowns: dict[str, datetime] = {}
        self._alert_history: list[Alert] = []

    async def start(self) -> None:
        """Start the spectrum watch.

        Begins the baseline establishment phase, then transitions to
        active watching once baseline is complete.
        """
        if self._running:
            logger.warning("Watch already running")
            return

        self._running = True
        self.state.status = "baseline"
        self.state.started_at = datetime.now()

        # Log start
        self.audit_logger.log_operation(
            adw_id=f"watch_{self.config.watch_id}",
            operation="watch_started",
            params={
                "name": self.config.name,
                "bands": [b.value for b in self.config.bands],
                "conditions": [c.condition_type for c in self.config.alert_conditions],
            },
        )

        logger.info("Starting watch: %s", self.config.name)

        # Send startup notification
        await self.notifier.send(
            Notification(
                title=f"Watch Started: {self.config.name}",
                message=f"Establishing baseline ({self.config.baseline_scans} scans)...",
                priority=NotificationPriority.LOW,
                tags=["sdr", "watch", "start"],
            )
        )

        # Start scan loop
        self._task = asyncio.create_task(self._scan_loop())

    async def stop(self) -> None:
        """Stop the spectrum watch gracefully."""
        if not self._running:
            return

        self._running = False
        self.state.status = "stopped"

        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

        # Save state
        await self._save_state()

        # Log stop
        self.audit_logger.log_operation(
            adw_id=f"watch_{self.config.watch_id}",
            operation="watch_stopped",
            params={
                "scans_completed": self.state.scans_completed,
                "alerts_sent": self.state.alerts_sent,
            },
        )

        # Send summary notification
        await self.notifier.send(
            Notification(
                title=f"Watch Stopped: {self.config.name}",
                message=(
                    f"Scans: {self.state.scans_completed}, "
                    f"Alerts: {self.state.alerts_sent}"
                ),
                priority=NotificationPriority.LOW,
                tags=["sdr", "watch", "stop"],
            )
        )

        # Close notifier
        await self.notifier.close()

        logger.info(
            "Watch stopped: %d scans, %d alerts",
            self.state.scans_completed,
            self.state.alerts_sent,
        )

    async def pause(self) -> None:
        """Pause the watch (can be resumed)."""
        if self.state.status in ("watching", "baseline"):
            self.state.status = "paused"
            logger.info("Watch paused")

    async def resume(self) -> None:
        """Resume a paused watch."""
        if self.state.status == "paused":
            if self.baseline.established:
                self.state.status = "watching"
            else:
                self.state.status = "baseline"
            logger.info("Watch resumed")

    async def _scan_loop(self) -> None:
        """Main scan loop - runs continuously until stopped."""
        try:
            while self._running:
                if self.state.status == "paused":
                    await asyncio.sleep(1)
                    continue

                # Get frequency ranges to scan
                ranges = self.config.get_frequency_ranges()
                if not ranges:
                    logger.error("No frequency ranges configured")
                    await asyncio.sleep(self.config.scan_interval_seconds)
                    continue

                # Scan each range; each one baselines, then watches, on its own
                for start_hz, end_hz in ranges:
                    if not self._running:
                        break
                    if self.baseline.is_failed(start_hz, end_hz):
                        continue

                    try:
                        result = await self._execute_scan(start_hz, end_hz)
                    except Exception as e:
                        logger.error("Scan error: %s", e)
                        self.state.error = str(e)
                        if self.baseline.record_scan_error(start_hz, end_hz):
                            await self._range_failed(start_hz, end_hz, e)
                        continue

                    self.baseline.record_scan_success(start_hz, end_hz)
                    try:
                        for alert in await self._process_scan(result):
                            await self._send_alert(alert)
                    except Exception as e:
                        logger.error("Scan processing error: %s", e)
                        self.state.error = str(e)

                # Wait for next scan interval
                await asyncio.sleep(self.config.scan_interval_seconds)

        except asyncio.CancelledError:
            logger.debug("Scan loop cancelled")
        except Exception as e:
            logger.error("Fatal scan loop error: %s", e)
            self.state.status = "stopped"
            self.state.error = str(e)

    async def _execute_scan(
        self, start_hz: float, end_hz: float
    ) -> ScanResult:
        """Execute a single scan.

        Args:
            start_hz: Start frequency in Hz.
            end_hz: End frequency in Hz.

        Returns:
            Scan result with detected peaks.
        """
        # Run scan in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self.scanner.scan(
                start_hz,
                end_hz,
                dwell_time_ms=self.config.dwell_time_ms,
            ),
        )

        self.state.scans_completed += 1
        self.state.last_scan_time = datetime.now()

        return result

    async def _process_scan(self, result: ScanResult) -> list[Alert]:
        """Route a scan by its range's phase.

        A range still building its baseline adds the scan to it; a range whose
        baseline is complete checks alert conditions, whatever the other
        ranges are doing.

        Args:
            result: Scan result of one range.

        Returns:
            Alerts to send (none while the range is baselining).
        """
        if self.baseline.is_range_established(result.start_freq_hz, result.end_freq_hz):
            return await self._check_alerts(result)
        await self._process_baseline_scan(result)
        return []

    async def _range_failed(self, start_hz: float, end_hz: float, error: Exception) -> None:
        """Report, once, a range given up on after repeated scan errors."""
        message = (
            f"{start_hz / 1e6:.3f}-{end_hz / 1e6:.3f} MHz failed "
            f"{self.baseline.max_consecutive_errors} scans in a row ({error}); "
            "no longer scanning it"
        )
        logger.error("Range failed: %s", message)
        self.audit_logger.log_operation(
            adw_id=f"watch_{self.config.watch_id}",
            operation="range_failed",
            params={"start_hz": start_hz, "end_hz": end_hz, "error": str(error)},
        )
        await self.notifier.send(
            Notification(
                title="Watch Range Failed",
                message=message,
                priority=NotificationPriority.HIGH,
                tags=["sdr", "watch", "error"],
            )
        )
        if not self.baseline.active_ranges:
            self.state.error = "Every frequency range failed; nothing left to watch"
            logger.error(self.state.error)
            return
        # The failed range may have been the last one holding back the baseline
        await self._update_phase()

    async def _process_baseline_scan(self, result: ScanResult) -> None:
        """Process a scan during baseline establishment.

        Args:
            result: Scan result to add to baseline.
        """
        range_baseline = self.baseline.for_result(result)
        was_established = range_baseline.established
        self.baseline.add_scan(result)
        self.state.baseline_scans_completed = self.baseline.scan_count

        # Log progress
        logger.info(
            "Baseline scan %d/%d of %.3f-%.3f MHz: %d signals",
            range_baseline.scan_count,
            self.config.baseline_scans,
            result.start_freq_hz / 1e6,
            result.end_freq_hz / 1e6,
            len(result.peaks),
        )

        if range_baseline.established and not was_established:
            logger.info(
                "Baseline of %.3f-%.3f MHz established; watching that range",
                result.start_freq_hz / 1e6,
                result.end_freq_hz / 1e6,
            )
        await self._update_phase()

    async def _update_phase(self) -> None:
        """Move the watch to "watching" once every active range has its baseline.

        A paused or stopped watch keeps its status; resume() picks the phase.
        """
        if self.state.status in ("idle", "baseline") and self.baseline.established:
            self.state.status = "watching"
            self.state.baseline_established = True

            stable = len(self.baseline.get_baseline_signals())

            self.audit_logger.log_operation(
                adw_id=f"watch_{self.config.watch_id}",
                operation="baseline_established",
                params={
                    "scans": self.baseline.scan_count,
                    "stable_signals": stable,
                },
            )

            await self.notifier.send(
                Notification(
                    title="Baseline Established",
                    message=f"Tracking {stable} signals. Now watching...",
                    priority=NotificationPriority.DEFAULT,
                    tags=["sdr", "baseline"],
                )
            )

            logger.info("Baseline established: %d stable signals", stable)

    async def _check_alerts(self, result: ScanResult) -> list[Alert]:
        """Check alert conditions against scan result.

        Args:
            result: Current scan result.

        Returns:
            List of triggered alerts.
        """
        alerts: list[Alert] = []

        # Track signal presence once per scan, whatever the cooldowns
        self.baseline.for_result(result).update_presence(result)

        for condition in self.config.alert_conditions:
            # Check cooldown
            cooldown_key = f"{condition.condition_type}_{condition.frequency_hz}"
            if cooldown_key in self._alert_cooldowns:
                last_alert = self._alert_cooldowns[cooldown_key]
                if (datetime.now() - last_alert).seconds < condition.cooldown_seconds:
                    continue

            triggered_alerts = self._evaluate_condition(condition, result)
            alerts.extend(triggered_alerts)

            # Update cooldown for triggered conditions
            if triggered_alerts:
                self._alert_cooldowns[cooldown_key] = datetime.now()

        return alerts

    def _evaluate_condition(
        self, condition: AlertCondition, result: ScanResult
    ) -> list[Alert]:
        """Evaluate a single alert condition.

        Args:
            condition: The condition to evaluate.
            result: Current scan result.

        Returns:
            List of alerts if condition triggered.
        """
        alerts: list[Alert] = []

        if condition.condition_type == "new_signal":
            alerts.extend(self._check_new_signals(condition, result))

        elif condition.condition_type == "threshold_breach":
            alerts.extend(self._check_threshold_breach(condition, result))

        elif condition.condition_type == "band_activity":
            alert = self._check_band_activity(condition, result)
            if alert:
                alerts.append(alert)

        elif condition.condition_type == "signal_loss":
            alerts.extend(self._check_signal_loss(condition, result))

        return alerts

    def _check_new_signals(
        self, condition: AlertCondition, result: ScanResult
    ) -> list[Alert]:
        """Check for new signals not in the scanned range's baseline."""
        alerts = []
        baseline = self.baseline.for_result(result)

        for peak in result.peaks:
            # Skip if below threshold
            if condition.threshold_db and peak.power_db < condition.threshold_db:
                continue

            # Check if monitoring specific frequency
            if (
                condition.frequency_hz is not None
                and abs(peak.frequency_hz - condition.frequency_hz)
                > condition.frequency_tolerance_hz
            ):
                continue

            # Check if new
            if baseline.is_new_signal(peak):
                freq_mhz = peak.frequency_hz / 1e6
                notable = lookup_notable(peak.frequency_hz)

                message = f"New signal at {freq_mhz:.3f} MHz ({peak.power_db:.1f} dB)"
                if notable:
                    message += f" - {notable}"

                alerts.append(
                    Alert(
                        watch_id=self.config.watch_id,
                        condition=condition,
                        frequency_hz=peak.frequency_hz,
                        power_db=peak.power_db,
                        message=message,
                    )
                )

        return alerts

    def _check_threshold_breach(
        self, condition: AlertCondition, result: ScanResult
    ) -> list[Alert]:
        """Check for signals exceeding threshold."""
        alerts = []

        if condition.threshold_db is None:
            return alerts

        for peak in result.peaks:
            if peak.power_db > condition.threshold_db:
                freq_mhz = peak.frequency_hz / 1e6

                alerts.append(
                    Alert(
                        watch_id=self.config.watch_id,
                        condition=condition,
                        frequency_hz=peak.frequency_hz,
                        power_db=peak.power_db,
                        message=(
                            f"Threshold breach at {freq_mhz:.3f} MHz: "
                            f"{peak.power_db:.1f} dB > {condition.threshold_db} dB"
                        ),
                    )
                )

        return alerts

    def _check_band_activity(
        self, condition: AlertCondition, result: ScanResult
    ) -> Alert | None:
        """Check for significant band activity changes."""
        if condition.activity_change_percent is None:
            return None

        # Compared with this range's own power history, not other bands'
        change = self.baseline.for_result(result).get_activity_change(result)

        if abs(change) > condition.activity_change_percent:
            direction = "increased" if change > 0 else "decreased"

            return Alert(
                watch_id=self.config.watch_id,
                condition=condition,
                frequency_hz=result.start_freq_hz,
                power_db=result.noise_floor_db,
                message=(
                    f"Band activity {direction} by {abs(change):.1f}% "
                    f"(threshold: {condition.activity_change_percent}%)"
                ),
            )

        return None

    def _check_signal_loss(
        self, condition: AlertCondition, result: ScanResult
    ) -> list[Alert]:
        """Check for missing baseline signals."""
        alerts = []
        baseline = self.baseline.for_result(result)

        missing = baseline.get_missing_signals(result)

        for freq_hz, last_power in missing:
            # Check if monitoring specific frequency
            if (
                condition.frequency_hz is not None
                and abs(freq_hz - condition.frequency_hz)
                > condition.frequency_tolerance_hz
            ):
                continue

            freq_mhz = freq_hz / 1e6
            notable = lookup_notable(freq_hz)

            message = f"Signal lost at {freq_mhz:.3f} MHz (was {last_power:.1f} dB)"
            if notable:
                message += f" - {notable}"

            alerts.append(
                Alert(
                    watch_id=self.config.watch_id,
                    condition=condition,
                    frequency_hz=freq_hz,
                    power_db=last_power,
                    message=message,
                )
            )
            # One alert per loss: quiet until the signal returns and is lost again
            baseline.mark_loss_reported(freq_hz)

        return alerts

    async def _send_alert(self, alert: Alert) -> None:
        """Send an alert through notification backends.

        Args:
            alert: The alert to send.
        """
        previous_status = self.state.status
        self.state.status = "alerting"

        # Determine priority based on condition and frequency
        priority = NotificationPriority.HIGH
        # Emergency frequencies get urgent priority; a measured peak is never
        # exactly on the channel, so match within a tolerance
        if is_emergency_frequency(alert.frequency_hz):
            priority = NotificationPriority.URGENT

        # Build notification
        freq_mhz = alert.frequency_hz / 1e6
        notification = Notification(
            title=f"SDR Alert: {alert.condition.condition_type.replace('_', ' ').title()}",
            message=alert.message,
            priority=priority,
            tags=["sdr", "alert", alert.condition.condition_type],
            data=alert.to_dict(),
        )

        # Send notification
        results = await self.notifier.send(notification)
        alert.notified = any(results)

        # Log to audit
        self.audit_logger.log_operation(
            adw_id=f"watch_{self.config.watch_id}",
            operation="alert_triggered",
            params={
                "alert_id": alert.alert_id,
                "condition_type": alert.condition.condition_type,
                "frequency_mhz": freq_mhz,
                "power_db": alert.power_db,
            },
        )

        # Update state
        self.state.alerts_sent += 1
        self._alert_history.append(alert)

        # Back to the phase the watch was in (other ranges may still be baselining)
        self.state.status = previous_status

        logger.warning("ALERT: %s", alert.message)

    async def _save_state(self) -> None:
        """Save watch state to disk for persistence."""
        state_file = self.state_dir / f"{self.config.watch_id}.json"

        state_data = {
            "config": self.config.model_dump(mode="json"),
            "state": {
                "status": self.state.status,
                "baseline_established": self.state.baseline_established,
                "scans_completed": self.state.scans_completed,
                "alerts_sent": self.state.alerts_sent,
                "started_at": (
                    self.state.started_at.isoformat()
                    if self.state.started_at
                    else None
                ),
            },
            "baseline": self.baseline.to_dict(),
            "alert_history": [a.to_dict() for a in self._alert_history[-100:]],
        }

        state_file.write_text(json.dumps(state_data, indent=2))
        logger.debug("State saved to %s", state_file)

    @classmethod
    async def load_state(cls, watch_id: str, state_dir: Path | None = None) -> SpectrumWatch | None:
        """Load a watch from saved state.

        Args:
            watch_id: The watch ID to load.
            state_dir: State directory (default: ~/.rf-asset-discovery/watches).

        Returns:
            Restored SpectrumWatch or None if not found.
        """
        state_dir = state_dir or Path.home() / ".rf-asset-discovery" / "watches"
        state_file = state_dir / f"{watch_id}.json"

        if not state_file.exists():
            return None

        try:
            data = json.loads(state_file.read_text())

            config = WatchConfig(**data["config"])
            watch = cls(config, state_dir=state_dir)

            # Restore baseline
            watch.baseline = RangeBaselines.from_dict(
                data["baseline"],
                ranges=config.get_frequency_ranges(),
                min_scans_required=config.baseline_scans,
            )

            # Restore state
            state_data = data["state"]
            # From the restored baseline, which may have been rebuilt or trimmed
            watch.state.baseline_established = watch.baseline.established
            watch.state.baseline_scans_completed = watch.baseline.scan_count
            watch.state.scans_completed = state_data.get("scans_completed", 0)
            watch.state.alerts_sent = state_data.get("alerts_sent", 0)

            logger.info("Loaded watch state: %s", watch_id)
            return watch

        except Exception as e:
            logger.error("Failed to load watch state: %s", e)
            return None

    def get_status(self) -> dict[str, Any]:
        """Get current watch status.

        Returns:
            Dictionary with status information.
        """
        return {
            "watch_id": self.config.watch_id,
            "name": self.config.name,
            "status": self.state.status,
            "baseline_established": self.baseline.established,
            "baseline_progress": (
                f"{self.baseline.scan_count}/{self.config.baseline_scans}"
            ),
            "scans_completed": self.state.scans_completed,
            "alerts_sent": self.state.alerts_sent,
            "stable_signals": len(self.baseline.get_baseline_signals()),
            "uptime_seconds": (
                (datetime.now() - self.state.started_at).total_seconds()
                if self.state.started_at
                else 0
            ),
        }


# =============================================================================
# Convenience Functions
# =============================================================================


async def watch_band(
    band: FrequencyBand,
    ntfy_topic: str | None = None,
    threshold_db: float = -30.0,
    **kwargs: Any,
) -> SpectrumWatch:
    """Create and start a watch for a predefined band.

    Args:
        band: The frequency band to watch.
        ntfy_topic: Optional ntfy.sh topic for notifications.
        threshold_db: Detection threshold in dB.
        **kwargs: Additional WatchConfig parameters.

    Returns:
        Running SpectrumWatch instance.
    """
    config = create_watch_for_band(band, threshold_db=threshold_db)

    if ntfy_topic:
        config.notifications.append(f"ntfy:{ntfy_topic}")

    watch = SpectrumWatch(config)
    await watch.start()
    return watch


async def watch_frequency(
    freq_hz: float,
    tolerance_hz: float = 50000,
    ntfy_topic: str | None = None,
    threshold_db: float = -30.0,
    **kwargs: Any,
) -> SpectrumWatch:
    """Create and start a watch for a specific frequency.

    Args:
        freq_hz: The frequency to watch in Hz.
        tolerance_hz: Frequency tolerance for matching.
        ntfy_topic: Optional ntfy.sh topic for notifications.
        threshold_db: Detection threshold in dB.
        **kwargs: Additional parameters.

    Returns:
        Running SpectrumWatch instance.
    """
    config = create_watch_for_frequency(
        freq_hz,
        tolerance_hz=tolerance_hz,
        threshold_db=threshold_db,
    )

    if ntfy_topic:
        config.notifications.append(f"ntfy:{ntfy_topic}")

    watch = SpectrumWatch(config)
    await watch.start()
    return watch


async def watch_from_intent(
    intent: str,
    ntfy_topic: str | None = None,
    **kwargs: Any,
) -> SpectrumWatch:
    """Create and start a watch from natural language intent.

    Args:
        intent: Natural language description of what to watch.
        ntfy_topic: Optional ntfy.sh topic for notifications.
        **kwargs: Additional parameters.

    Returns:
        Running SpectrumWatch instance.

    Example:
        >>> watch = await watch_from_intent(
        ...     "Watch aircraft band, alert on 121.5 MHz emergency",
        ...     ntfy_topic="my-sdr-alerts",
        ... )
    """
    config = parse_natural_language(intent)

    if ntfy_topic:
        config.notifications.append(f"ntfy:{ntfy_topic}")

    watch = SpectrumWatch(config)
    await watch.start()
    return watch


async def run_watch_cli(
    config: WatchConfig,
    ntfy_topic: str | None = None,
) -> None:
    """Run a watch interactively with signal handling.

    Sets up SIGINT/SIGTERM handlers for graceful shutdown.

    Args:
        config: Watch configuration.
        ntfy_topic: Optional ntfy.sh topic.
    """
    # Setup notifier
    notifier = create_notifier(
        ntfy_topic=ntfy_topic,
        console=True,
        use_rich=True,
    )

    watch = SpectrumWatch(config, notifier=notifier)

    # Signal handlers
    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()

    def handle_signal() -> None:
        logger.info("Received shutdown signal")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_signal)

    # Start watch
    await watch.start()

    # Print status header
    print(f"\nSpectrum Watch: {config.name}")
    print("=" * 40)
    ranges = config.get_frequency_ranges()
    for start, end in ranges:
        print(f"Range: {start/1e6:.3f} - {end/1e6:.3f} MHz")
    print(f"Alerts: {', '.join(c.condition_type for c in config.alert_conditions)}")
    print(f"Notifications: {', '.join(config.notifications)}")
    print("=" * 40)
    print("\nPress Ctrl+C to stop\n")

    # Wait for shutdown
    await stop_event.wait()

    # Stop gracefully
    await watch.stop()

    # Print summary
    status = watch.get_status()
    print("\nWatch Summary:")
    print(f"  Scans: {status['scans_completed']}")
    print(f"  Alerts: {status['alerts_sent']}")
    print(f"  Uptime: {status['uptime_seconds']:.0f} seconds")
