"""FFT and spectrum analysis functions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import numpy as np
from scipy import signal

from rf_asset_discovery.core.config import DEFAULT_FFT_SIZE, DEFAULT_WINDOW

if TYPE_CHECKING:
    from numpy.typing import NDArray

WindowType = Literal["hamming", "hann", "blackman", "bartlett", "none"]


def get_window(window: WindowType, size: int) -> NDArray[np.float64]:
    """Get window function array.

    Args:
        window: Window function name.
        size: Window size.

    Returns:
        Window function values.
    """
    if window == "none":
        return np.ones(size)
    return signal.get_window(window, size)


def compute_fft(
    samples: NDArray[np.complex64],
    fft_size: int = DEFAULT_FFT_SIZE,
    window: WindowType = DEFAULT_WINDOW,
    shift: bool = True,
) -> NDArray[np.complex128]:
    """Compute FFT of complex samples.

    Args:
        samples: Complex IQ samples.
        fft_size: FFT size (will use last fft_size samples if longer).
        window: Window function to apply.
        shift: If True, shift zero frequency to center.

    Returns:
        Complex FFT result.
    """
    # Use last fft_size samples
    if len(samples) > fft_size:
        samples = samples[-fft_size:]
    elif len(samples) < fft_size:
        # Zero pad if needed
        padded = np.zeros(fft_size, dtype=np.complex64)
        padded[: len(samples)] = samples
        samples = padded

    # Apply window
    win = get_window(window, fft_size)
    windowed = samples * win

    # Compute FFT
    fft_result = np.fft.fft(windowed)

    if shift:
        fft_result = np.fft.fftshift(fft_result)

    return fft_result


def compute_power_spectrum(
    samples: NDArray[np.complex64],
    fft_size: int = DEFAULT_FFT_SIZE,
    window: WindowType = DEFAULT_WINDOW,
    log_scale: bool = True,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Compute power spectrum in dB.

    Args:
        samples: Complex IQ samples.
        fft_size: FFT size.
        window: Window function.
        log_scale: If True, return in dB scale.

    Returns:
        Tuple of (frequencies normalized -0.5 to 0.5, power values).
    """
    fft_result = compute_fft(samples, fft_size, window, shift=True)

    # Compute power (magnitude squared)
    power = np.abs(fft_result) ** 2

    # Normalize
    power = power / fft_size

    if log_scale:
        # Convert to dB, avoid log(0)
        power = 10 * np.log10(np.maximum(power, 1e-20))

    # Frequency axis (normalized)
    freqs = np.linspace(-0.5, 0.5, fft_size)

    return freqs, power


def compute_power_spectrum_hz(
    samples: NDArray[np.complex64],
    sample_rate: float,
    center_freq: float,
    fft_size: int = DEFAULT_FFT_SIZE,
    window: WindowType = DEFAULT_WINDOW,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Compute power spectrum with frequency in Hz.

    Args:
        samples: Complex IQ samples.
        sample_rate: Sample rate in Hz.
        center_freq: Center frequency in Hz.
        fft_size: FFT size.
        window: Window function.

    Returns:
        Tuple of (frequencies in Hz, power in dB).
    """
    freqs_norm, power = compute_power_spectrum(samples, fft_size, window, log_scale=True)

    # Convert normalized frequencies to Hz
    freqs_hz = freqs_norm * sample_rate + center_freq

    return freqs_hz, power


def compute_spectrogram(
    samples: NDArray[np.complex64],
    fft_size: int = DEFAULT_FFT_SIZE,
    overlap: float = 0.5,
    window: WindowType = DEFAULT_WINDOW,
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Compute spectrogram (time-frequency representation).

    Args:
        samples: Complex IQ samples.
        fft_size: FFT size per segment.
        overlap: Overlap fraction (0 to 1).
        window: Window function.

    Returns:
        Tuple of (times, frequencies, power_dB).
    """
    hop_size = int(fft_size * (1 - overlap))
    num_segments = (len(samples) - fft_size) // hop_size + 1

    if num_segments < 1:
        num_segments = 1

    # Pre-allocate output
    spectrogram = np.zeros((num_segments, fft_size))

    for i in range(num_segments):
        start = i * hop_size
        end = start + fft_size
        if end > len(samples):
            break

        segment = samples[start:end]
        _, power = compute_power_spectrum(segment, fft_size, window, log_scale=True)
        spectrogram[i, :] = power

    # Create time and frequency axes (normalized)
    times = np.arange(num_segments) * hop_size
    freqs = np.linspace(-0.5, 0.5, fft_size)

    return times.astype(np.float64), freqs, spectrogram


def find_peaks(
    power_spectrum: NDArray[np.float64],
    threshold_db: float = -30.0,
    min_distance: int = 10,
) -> list[tuple[int, float]]:
    """Find peaks in power spectrum.

    Args:
        power_spectrum: Power spectrum in dB.
        threshold_db: Minimum peak height in dB.
        min_distance: Minimum distance between peaks in bins.

    Returns:
        List of (bin_index, power_dB) tuples for each peak.
    """
    peaks, properties = signal.find_peaks(
        power_spectrum,
        height=threshold_db,
        distance=min_distance,
    )

    heights = properties.get("peak_heights", power_spectrum[peaks])

    return [(int(idx), float(height)) for idx, height in zip(peaks, heights, strict=False)]


def estimate_noise_floor(
    power_spectrum: NDArray[np.float64],
    percentile: float = 25.0,
) -> float:
    """Estimate noise floor from power spectrum.

    Args:
        power_spectrum: Power spectrum in dB.
        percentile: Percentile to use for estimation.

    Returns:
        Estimated noise floor in dB.
    """
    return float(np.percentile(power_spectrum, percentile))


def signal_to_noise(
    power_spectrum: NDArray[np.float64],
    signal_bins: tuple[int, int] | None = None,
) -> float:
    """Estimate signal-to-noise ratio.

    Args:
        power_spectrum: Power spectrum in dB.
        signal_bins: Optional (start, end) bins for signal region.

    Returns:
        SNR in dB.
    """
    if signal_bins is None:
        # Use center as signal, edges as noise
        center = len(power_spectrum) // 2
        width = len(power_spectrum) // 8
        signal_bins = (center - width, center + width)

    noise_floor = estimate_noise_floor(power_spectrum)
    signal_power = np.max(power_spectrum[signal_bins[0] : signal_bins[1]])

    return float(signal_power - noise_floor)
