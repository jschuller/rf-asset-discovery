"""Spectrum baseline management for anomaly detection.

Tracks known signals in a frequency range to detect:
- New signals that weren't present during baseline
- Power deviations from normal levels
- Missing signals that were previously stable
- Overall activity changes
"""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field
from typing import Any

from rf_asset_discovery.apps.scanner import ScanResult, SignalPeak

logger = logging.getLogger(__name__)

# Power samples a signal needs before it counts as part of the baseline
MIN_SIGNAL_SAMPLES = 3


def _in_range(result: ScanResult, freq_hz: float) -> bool:
    """Whether a frequency lies inside the range a scan covered."""
    return result.start_freq_hz <= freq_hz <= result.end_freq_hz


@dataclass
class SignalHistory:
    """History of power readings for a single signal."""

    frequency_hz: float
    power_samples: list[float] = field(default_factory=list)
    last_seen_scan: int = 0
    consecutive_misses: int = 0
    # Absent and already alerted on; cleared when the signal is seen again
    known_missing: bool = False

    @property
    def average_power(self) -> float:
        """Average power in dB."""
        if not self.power_samples:
            return -60.0
        return statistics.mean(self.power_samples)

    @property
    def power_std(self) -> float:
        """Standard deviation of power readings."""
        if len(self.power_samples) < 2:
            return 0.0
        return statistics.stdev(self.power_samples)

    @property
    def is_established(self) -> bool:
        """Whether the signal was seen often enough to be tracked for loss."""
        return len(self.power_samples) >= MIN_SIGNAL_SAMPLES

    @property
    def is_stable(self) -> bool:
        """Whether the signal has been consistently present."""
        return self.is_established and self.consecutive_misses == 0


@dataclass
class SpectrumBaseline:
    """Baseline manager for spectrum anomaly detection.

    Collects power readings over multiple scans to establish
    a baseline of normal activity, then detects deviations.

    Example:
        >>> baseline = SpectrumBaseline(tolerance_hz=50000)
        >>> for _ in range(12):
        ...     result = scanner.scan(...)
        ...     baseline.add_scan(result)
        >>> if baseline.established:
        ...     for peak in current_result.peaks:
        ...         if baseline.is_new_signal(peak):
        ...             print(f"New signal at {peak.frequency_hz} Hz!")
    """

    tolerance_hz: float = 50000
    min_scans_required: int = 12
    power_deviation_threshold_db: float = 6.0
    miss_threshold: int = 3

    # Internal state
    signals: dict[int, SignalHistory] = field(default_factory=dict)
    scan_count: int = 0
    established: bool = False
    total_power_history: list[float] = field(default_factory=list)

    def _freq_key(self, freq_hz: float) -> int:
        """Convert frequency to bucket key for grouping nearby signals."""
        return int(freq_hz / self.tolerance_hz)

    def _find_matching_signal(self, freq_hz: float) -> SignalHistory | None:
        """Find an existing signal within tolerance."""
        key = self._freq_key(freq_hz)
        # Check this bucket and neighbors
        for k in [key - 1, key, key + 1]:
            if k in self.signals:
                sig = self.signals[k]
                if abs(sig.frequency_hz - freq_hz) <= self.tolerance_hz:
                    return sig
        return None

    def add_scan(self, result: ScanResult) -> None:
        """Add a scan result to the baseline.

        Args:
            result: Scan result with detected peaks.
        """
        self.scan_count += 1
        seen_keys: set[int] = set()

        # Process each peak
        for peak in result.peaks:
            key = self._freq_key(peak.frequency_hz)
            seen_keys.add(key)

            existing = self._find_matching_signal(peak.frequency_hz)

            if existing:
                # Update existing signal
                existing.power_samples.append(peak.power_db)
                existing.last_seen_scan = self.scan_count
                existing.consecutive_misses = 0
                # Update frequency with running average
                existing.frequency_hz = (
                    existing.frequency_hz * 0.9 + peak.frequency_hz * 0.1
                )
            else:
                # New signal
                self.signals[key] = SignalHistory(
                    frequency_hz=peak.frequency_hz,
                    power_samples=[peak.power_db],
                    last_seen_scan=self.scan_count,
                )

        # Track misses for signals in this scan's range that were not seen
        for key, sig in self.signals.items():
            if (
                key not in seen_keys
                and self.scan_count > sig.last_seen_scan
                and _in_range(result, sig.frequency_hz)
            ):
                sig.consecutive_misses += 1

        # Track total band power
        if result.peaks:
            total_power = sum(10 ** (p.power_db / 10) for p in result.peaks)
            self.total_power_history.append(total_power)

        # Check if baseline is established
        if self.scan_count >= self.min_scans_required and not self.established:
            self.established = True
            stable_count = sum(1 for s in self.signals.values() if s.is_stable)
            logger.info(
                "Baseline established: %d signals tracked, %d stable",
                len(self.signals),
                stable_count,
            )

    def _is_present(self, sig: SignalHistory, result: ScanResult) -> bool:
        """Whether any peak in the scan lies within tolerance of the signal."""
        return any(
            abs(p.frequency_hz - sig.frequency_hz) <= self.tolerance_hz
            for p in result.peaks
        )

    def update_presence(self, result: ScanResult) -> None:
        """Update miss counts from a watching-phase scan.

        Unlike add_scan, this learns no new signals and adds no power samples.
        Only signals inside the scanned range are touched: a peak within
        tolerance resets the signal's misses (and known_missing), otherwise
        they increase by one.

        Args:
            result: Current scan result.
        """
        for sig in self.signals.values():
            if not _in_range(result, sig.frequency_hz):
                continue
            if self._is_present(sig, result):
                sig.consecutive_misses = 0
                sig.known_missing = False
            else:
                sig.consecutive_misses += 1

    def is_new_signal(self, peak: SignalPeak) -> bool:
        """Check if a peak represents a new signal not in baseline.

        Args:
            peak: Signal peak to check.

        Returns:
            True if signal is not in the baseline.
        """
        if not self.established:
            return False

        existing = self._find_matching_signal(peak.frequency_hz)
        return existing is None

    def get_power_deviation(self, peak: SignalPeak) -> float | None:
        """Get power deviation from baseline for a signal.

        Args:
            peak: Signal peak to check.

        Returns:
            Power deviation in dB, or None if not in baseline.
        """
        existing = self._find_matching_signal(peak.frequency_hz)
        if existing is None or not existing.power_samples:
            return None

        return peak.power_db - existing.average_power

    def is_power_anomaly(self, peak: SignalPeak) -> bool:
        """Check if signal power is anomalous.

        Args:
            peak: Signal peak to check.

        Returns:
            True if power deviates significantly from baseline.
        """
        deviation = self.get_power_deviation(peak)
        if deviation is None:
            return False

        return abs(deviation) > self.power_deviation_threshold_db

    def get_missing_signals(
        self, result: ScanResult
    ) -> list[tuple[float, float]]:
        """Find baseline signals not present in current scan.

        A signal counts as missing once it has been absent from at least
        miss_threshold consecutive scans of its range (see update_presence).
        Signals already marked known_missing are left out, so each loss is
        reported once; call mark_loss_reported after alerting.

        Args:
            result: Current scan result.

        Returns:
            List of (frequency_hz, last_power_db) for missing signals.
        """
        if not self.established:
            return []

        missing: list[tuple[float, float]] = []

        for sig in self.signals.values():
            if (
                not sig.is_established
                or sig.known_missing
                or not _in_range(result, sig.frequency_hz)
            ):
                continue

            if (
                not self._is_present(sig, result)
                and sig.consecutive_misses >= self.miss_threshold
            ):
                missing.append((sig.frequency_hz, sig.average_power))

        return missing

    def mark_loss_reported(self, freq_hz: float) -> None:
        """Stop reporting a missing signal until it is seen again.

        Args:
            freq_hz: Frequency of the signal, as returned by get_missing_signals.
        """
        sig = self._find_matching_signal(freq_hz)
        if sig is not None:
            sig.known_missing = True

    def get_activity_change(
        self,
        result: ScanResult,
        band_start: float | None = None,
        band_end: float | None = None,
    ) -> float:
        """Calculate activity change from baseline.

        Args:
            result: Current scan result.
            band_start: Optional band start frequency (Hz).
            band_end: Optional band end frequency (Hz).

        Returns:
            Percentage change in total band power (-100 to +inf).
        """
        if not self.established or not self.total_power_history:
            return 0.0

        # Filter peaks to band if specified
        peaks = result.peaks
        if band_start is not None and band_end is not None:
            peaks = [
                p
                for p in peaks
                if band_start <= p.frequency_hz <= band_end
            ]

        if not peaks:
            return -100.0  # Complete silence

        # Calculate current total power
        current_power = sum(10 ** (p.power_db / 10) for p in peaks)

        # Compare to baseline average
        baseline_avg = statistics.mean(self.total_power_history)
        if baseline_avg == 0:
            return 0.0

        return ((current_power - baseline_avg) / baseline_avg) * 100

    def get_baseline_signals(self) -> list[tuple[float, float]]:
        """Get all signals in the baseline.

        Returns:
            List of (frequency_hz, average_power_db) tuples.
        """
        return [
            (sig.frequency_hz, sig.average_power)
            for sig in self.signals.values()
            if sig.is_stable
        ]

    def get_stats(self) -> dict[str, Any]:
        """Get baseline statistics.

        Returns:
            Dictionary with baseline statistics.
        """
        stable_signals = [s for s in self.signals.values() if s.is_stable]

        return {
            "established": self.established,
            "scan_count": self.scan_count,
            "total_signals": len(self.signals),
            "stable_signals": len(stable_signals),
            "tolerance_hz": self.tolerance_hz,
            "min_scans_required": self.min_scans_required,
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize baseline to dictionary.

        Returns:
            Dictionary representation for persistence.
        """
        return {
            "tolerance_hz": self.tolerance_hz,
            "min_scans_required": self.min_scans_required,
            "power_deviation_threshold_db": self.power_deviation_threshold_db,
            "miss_threshold": self.miss_threshold,
            "scan_count": self.scan_count,
            "established": self.established,
            "total_power_history": self.total_power_history,
            "signals": {
                str(k): {
                    "frequency_hz": v.frequency_hz,
                    "power_samples": v.power_samples,
                    "last_seen_scan": v.last_seen_scan,
                    "consecutive_misses": v.consecutive_misses,
                    "known_missing": v.known_missing,
                }
                for k, v in self.signals.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SpectrumBaseline:
        """Deserialize baseline from dictionary.

        Args:
            data: Dictionary representation.

        Returns:
            Reconstructed SpectrumBaseline.
        """
        baseline = cls(
            tolerance_hz=data.get("tolerance_hz", 50000),
            min_scans_required=data.get("min_scans_required", 12),
            power_deviation_threshold_db=data.get(
                "power_deviation_threshold_db", 6.0
            ),
            miss_threshold=data.get("miss_threshold", 3),
        )

        baseline.scan_count = data.get("scan_count", 0)
        baseline.established = data.get("established", False)
        baseline.total_power_history = data.get("total_power_history", [])

        for key_str, sig_data in data.get("signals", {}).items():
            key = int(key_str)
            baseline.signals[key] = SignalHistory(
                frequency_hz=sig_data["frequency_hz"],
                power_samples=sig_data["power_samples"],
                last_seen_scan=sig_data["last_seen_scan"],
                consecutive_misses=sig_data.get("consecutive_misses", 0),
                known_missing=sig_data.get("known_missing", False),
            )

        return baseline

    def clear(self) -> None:
        """Reset the baseline."""
        self.signals.clear()
        self.total_power_history.clear()
        self.scan_count = 0
        self.established = False
