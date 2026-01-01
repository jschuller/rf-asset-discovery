"""Audio and RF filter implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from scipy import signal

from rf_asset_discovery.core.config import FM_AUDIO_RATE

if TYPE_CHECKING:
    from numpy.typing import NDArray


def lowpass_filter(
    samples: NDArray[np.float64],
    cutoff_hz: float,
    sample_rate: float,
    order: int = 5,
) -> NDArray[np.float64]:
    """Apply low-pass filter.

    Args:
        samples: Input samples (real or complex).
        cutoff_hz: Cutoff frequency in Hz.
        sample_rate: Sample rate in Hz.
        order: Filter order.

    Returns:
        Filtered samples.
    """
    nyquist = sample_rate / 2
    normalized_cutoff = cutoff_hz / nyquist

    # Clamp to valid range
    normalized_cutoff = np.clip(normalized_cutoff, 0.001, 0.999)

    b, a = signal.butter(order, normalized_cutoff, btype="low")
    return signal.lfilter(b, a, samples)


def bandpass_filter(
    samples: NDArray[np.float64],
    low_hz: float,
    high_hz: float,
    sample_rate: float,
    order: int = 5,
) -> NDArray[np.float64]:
    """Apply band-pass filter.

    Args:
        samples: Input samples.
        low_hz: Lower cutoff frequency in Hz.
        high_hz: Upper cutoff frequency in Hz.
        sample_rate: Sample rate in Hz.
        order: Filter order.

    Returns:
        Filtered samples.
    """
    nyquist = sample_rate / 2
    low = np.clip(low_hz / nyquist, 0.001, 0.999)
    high = np.clip(high_hz / nyquist, 0.001, 0.999)

    if low >= high:
        return samples

    b, a = signal.butter(order, [low, high], btype="band")
    return signal.lfilter(b, a, samples)


def highpass_filter(
    samples: NDArray[np.float64],
    cutoff_hz: float,
    sample_rate: float,
    order: int = 5,
) -> NDArray[np.float64]:
    """Apply high-pass filter.

    Args:
        samples: Input samples.
        cutoff_hz: Cutoff frequency in Hz.
        sample_rate: Sample rate in Hz.
        order: Filter order.

    Returns:
        Filtered samples.
    """
    nyquist = sample_rate / 2
    normalized_cutoff = np.clip(cutoff_hz / nyquist, 0.001, 0.999)

    b, a = signal.butter(order, normalized_cutoff, btype="high")
    return signal.lfilter(b, a, samples)


def dc_block(
    samples: NDArray[np.float64],
    alpha: float = 0.995,
) -> NDArray[np.float64]:
    """Remove DC offset using a single-pole high-pass filter.

    Args:
        samples: Input samples.
        alpha: Filter coefficient (higher = lower cutoff).

    Returns:
        DC-blocked samples.
    """
    output = np.zeros_like(samples)
    prev_in = 0.0
    prev_out = 0.0

    for i, x in enumerate(samples):
        output[i] = x - prev_in + alpha * prev_out
        prev_in = x
        prev_out = output[i]

    return output


def dc_block_fast(samples: NDArray[np.float64]) -> NDArray[np.float64]:
    """Fast DC offset removal by subtracting mean.

    Args:
        samples: Input samples.

    Returns:
        DC-blocked samples.
    """
    return samples - np.mean(samples)


def deemphasis_filter(
    samples: NDArray[np.float64],
    sample_rate: float = FM_AUDIO_RATE,
    tau_us: float = 75.0,
) -> NDArray[np.float64]:
    """Apply FM de-emphasis filter.

    FM broadcast uses pre-emphasis to boost high frequencies.
    This filter reverses that effect for proper audio playback.

    Args:
        samples: Input audio samples.
        sample_rate: Audio sample rate in Hz.
        tau_us: Time constant in microseconds (75us for US/Korea, 50us for Europe).

    Returns:
        De-emphasized audio samples.
    """
    # Convert time constant to seconds
    tau = tau_us * 1e-6

    # Design single-pole IIR filter
    # Transfer function: H(s) = 1 / (1 + s*tau)
    # Bilinear transform to get digital filter

    # Pre-warped frequency
    w0 = 1.0 / tau
    fs = sample_rate

    # Bilinear transform
    alpha = w0 / (2.0 * fs)
    b = np.array([alpha, alpha])
    a = np.array([1.0 + alpha, alpha - 1.0])

    return signal.lfilter(b, a, samples)


def resample(
    samples: NDArray[np.float64],
    input_rate: float,
    output_rate: float,
) -> NDArray[np.float64]:
    """Resample signal to new sample rate.

    Args:
        samples: Input samples.
        input_rate: Input sample rate in Hz.
        output_rate: Desired output sample rate in Hz.

    Returns:
        Resampled signal.
    """
    if input_rate == output_rate:
        return samples

    # Calculate resampling ratio
    ratio = output_rate / input_rate
    new_length = int(len(samples) * ratio)

    return signal.resample(samples, new_length)


def decimate(
    samples: NDArray[np.float64],
    factor: int,
) -> NDArray[np.float64]:
    """Decimate signal by integer factor.

    Applies anti-aliasing filter before downsampling.

    Args:
        samples: Input samples.
        factor: Decimation factor (must be > 1).

    Returns:
        Decimated signal.
    """
    if factor <= 1:
        return samples

    return signal.decimate(samples, factor)


def moving_average(
    samples: NDArray[np.float64],
    window_size: int,
) -> NDArray[np.float64]:
    """Apply moving average filter.

    Args:
        samples: Input samples.
        window_size: Averaging window size.

    Returns:
        Smoothed samples.
    """
    if window_size <= 1:
        return samples

    kernel = np.ones(window_size) / window_size
    return np.convolve(samples, kernel, mode="same")
