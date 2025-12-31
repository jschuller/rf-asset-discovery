"""Spectrum scanner application."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

from sdr_toolkit.core.config import DEFAULT_FFT_SIZE, get_platform_config
from sdr_toolkit.core.device import SDRDevice
from sdr_toolkit.dsp.spectrum import (
    compute_power_spectrum,
    estimate_noise_floor,
    find_peaks,
)

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)


@dataclass
class SignalPeak:
    """Detected signal peak."""

    frequency_hz: float
    power_db: float
    bandwidth_hz: float | None = None

    def __repr__(self) -> str:
        return f"Signal({self.frequency_hz/1e6:.3f} MHz, {self.power_db:.1f} dB)"


@dataclass
class ScanResult:
    """Result of a spectrum scan."""

    start_freq_hz: float
    end_freq_hz: float
    step_hz: float
    peaks: list[SignalPeak]
    noise_floor_db: float
    scan_time_seconds: float

    def __repr__(self) -> str:
        return (
            f"ScanResult({self.start_freq_hz/1e6:.1f}-{self.end_freq_hz/1e6:.1f} MHz, "
            f"{len(self.peaks)} signals)"
        )


@dataclass
class SpectrumScanner:
    """Spectrum scanner for finding signals.

    Example:
        >>> scanner = SpectrumScanner()
        >>> result = scanner.scan(88e6, 108e6)  # Scan FM band
        >>> for peak in result.peaks:
        ...     print(f"{peak.frequency_hz/1e6:.1f} MHz: {peak.power_db:.1f} dB")
    """

    sample_rate: float = field(default_factory=lambda: get_platform_config().sample_rate)
    fft_size: int = DEFAULT_FFT_SIZE
    gain: float | str = "auto"
    threshold_db: float = -30.0
    device_index: int = 0

    def scan(
        self,
        start_freq_hz: float,
        end_freq_hz: float,
        step_hz: float | None = None,
        dwell_time_ms: float = 100,
    ) -> ScanResult:
        """Scan frequency range for signals.

        Args:
            start_freq_hz: Start frequency in Hz.
            end_freq_hz: End frequency in Hz.
            step_hz: Frequency step (default = sample_rate * 0.8).
            dwell_time_ms: Time to spend at each frequency in ms.

        Returns:
            ScanResult with detected signals.
        """
        import time

        if step_hz is None:
            step_hz = self.sample_rate * 0.8

        scan_start = time.time()
        all_peaks: list[SignalPeak] = []
        noise_floors: list[float] = []

        num_steps = int((end_freq_hz - start_freq_hz) / step_hz) + 1
        samples_per_step = int(self.sample_rate * dwell_time_ms / 1000)

        logger.info(
            "Scanning %.1f - %.1f MHz (%d steps)",
            start_freq_hz / 1e6,
            end_freq_hz / 1e6,
            num_steps,
        )

        with SDRDevice(
            sample_rate=self.sample_rate,
            center_freq=start_freq_hz,
            gain=self.gain,
            device_index=self.device_index,
        ) as device:
            for i in range(num_steps):
                center_freq = start_freq_hz + i * step_hz

                # Tune to frequency
                device.set_center_freq(center_freq)
                time.sleep(0.01)  # Allow PLL to settle

                # Read samples
                samples = device.read_samples(samples_per_step)

                # Compute power spectrum
                freqs_norm, power = compute_power_spectrum(
                    samples, self.fft_size, log_scale=True
                )

                # Find peaks
                peaks = find_peaks(power, threshold_db=self.threshold_db)

                # Convert to absolute frequencies
                for bin_idx, peak_power in peaks:
                    freq_offset = freqs_norm[bin_idx] * self.sample_rate
                    abs_freq = center_freq + freq_offset

                    # Only include peaks within scan range
                    if start_freq_hz <= abs_freq <= end_freq_hz:
                        all_peaks.append(
                            SignalPeak(
                                frequency_hz=abs_freq,
                                power_db=peak_power,
                            )
                        )

                # Track noise floor
                noise_floors.append(estimate_noise_floor(power))

                # Progress logging
                if (i + 1) % 10 == 0 or i == num_steps - 1:
                    logger.debug(
                        "Progress: %d/%d (%.0f%%)",
                        i + 1,
                        num_steps,
                        100 * (i + 1) / num_steps,
                    )

        scan_time = time.time() - scan_start

        # Merge nearby peaks
        merged_peaks = self._merge_peaks(all_peaks, merge_threshold_hz=50000)

        # Sort by power
        merged_peaks.sort(key=lambda p: p.power_db, reverse=True)

        avg_noise = np.mean(noise_floors) if noise_floors else -60.0

        return ScanResult(
            start_freq_hz=start_freq_hz,
            end_freq_hz=end_freq_hz,
            step_hz=step_hz,
            peaks=merged_peaks,
            noise_floor_db=float(avg_noise),
            scan_time_seconds=scan_time,
        )

    def _merge_peaks(
        self,
        peaks: list[SignalPeak],
        merge_threshold_hz: float,
    ) -> list[SignalPeak]:
        """Merge nearby peaks into single signals."""
        if not peaks:
            return []

        # Sort by frequency
        sorted_peaks = sorted(peaks, key=lambda p: p.frequency_hz)

        merged: list[SignalPeak] = []
        current = sorted_peaks[0]

        for peak in sorted_peaks[1:]:
            if peak.frequency_hz - current.frequency_hz < merge_threshold_hz:
                # Merge: keep highest power, average frequency
                if peak.power_db > current.power_db:
                    current = SignalPeak(
                        frequency_hz=(current.frequency_hz + peak.frequency_hz) / 2,
                        power_db=peak.power_db,
                    )
            else:
                merged.append(current)
                current = peak

        merged.append(current)
        return merged

    def scan_fm_band(self) -> ScanResult:
        """Scan FM broadcast band (87.5 - 108 MHz).

        Returns:
            ScanResult for FM band.
        """
        return self.scan(87.5e6, 108e6, step_hz=200e3)

    def quick_scan(
        self,
        center_freq_hz: float,
        bandwidth_hz: float = 2e6,
    ) -> list[SignalPeak]:
        """Quick single-frequency scan.

        Args:
            center_freq_hz: Center frequency in Hz.
            bandwidth_hz: Bandwidth to scan.

        Returns:
            List of detected peaks.
        """
        with SDRDevice(
            sample_rate=self.sample_rate,
            center_freq=center_freq_hz,
            gain=self.gain,
            device_index=self.device_index,
        ) as device:
            samples = device.read_samples(self.fft_size * 4)

            freqs_norm, power = compute_power_spectrum(
                samples, self.fft_size, log_scale=True
            )

            peaks = find_peaks(power, threshold_db=self.threshold_db)

            return [
                SignalPeak(
                    frequency_hz=center_freq_hz + freqs_norm[idx] * self.sample_rate,
                    power_db=pwr,
                )
                for idx, pwr in peaks
            ]


def scan_frequency_range(
    start_mhz: float,
    end_mhz: float,
    step_khz: float = 200,
) -> ScanResult:
    """Scan frequency range for signals.

    Convenience function for quick scanning.

    Args:
        start_mhz: Start frequency in MHz.
        end_mhz: End frequency in MHz.
        step_khz: Step size in kHz.

    Returns:
        ScanResult with detected signals.
    """
    scanner = SpectrumScanner()
    return scanner.scan(start_mhz * 1e6, end_mhz * 1e6, step_khz * 1e3)
