"""Signal demodulation functions."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from scipy import signal

from rf_asset_discovery.core.config import FM_AUDIO_RATE, FM_DEVIATION_HZ
from rf_asset_discovery.dsp.filters import dc_block_fast, deemphasis_filter, lowpass_filter

if TYPE_CHECKING:
    from numpy.typing import NDArray


def fm_demodulate(
    samples: NDArray[np.complex64],
    sample_rate: float,
    audio_rate: int = FM_AUDIO_RATE,
    deviation: float = FM_DEVIATION_HZ,
    apply_deemphasis: bool = True,
) -> tuple[NDArray[np.float64], int]:
    """Demodulate FM signal to audio.

    Uses the differentiate-and-divide method for FM demodulation:
    1. Compute instantaneous phase
    2. Differentiate to get frequency
    3. Decimate to audio rate
    4. Apply de-emphasis filter

    Args:
        samples: Complex IQ samples.
        sample_rate: Input sample rate in Hz.
        audio_rate: Desired audio output rate in Hz.
        deviation: FM deviation in Hz.
        apply_deemphasis: Whether to apply de-emphasis filter.

    Returns:
        Tuple of (audio samples, audio sample rate).
    """
    # Compute instantaneous phase
    phase = np.angle(samples)

    # Unwrap phase to avoid discontinuities
    phase = np.unwrap(phase)

    # Differentiate to get instantaneous frequency
    # d(phase)/dt = 2*pi*f, so f = d(phase)/dt / (2*pi)
    freq = np.diff(phase)

    # Normalize by expected deviation
    # For FM, the frequency deviation represents the amplitude
    audio = freq / (2 * np.pi * deviation) * sample_rate

    # Low-pass filter before decimation (anti-aliasing)
    audio = lowpass_filter(audio, audio_rate / 2, sample_rate, order=5)

    # Decimate to audio rate
    decimation = int(sample_rate / audio_rate)
    if decimation > 1:
        audio = signal.decimate(audio, decimation)

    # Remove DC offset
    audio = dc_block_fast(audio)

    # Apply de-emphasis filter
    if apply_deemphasis:
        audio = deemphasis_filter(audio, audio_rate)

    # Normalize audio level
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = audio / max_val * 0.9  # Leave some headroom

    return audio.astype(np.float64), audio_rate


def fm_demodulate_stereo(
    samples: NDArray[np.complex64],
    sample_rate: float,
    audio_rate: int = FM_AUDIO_RATE,
) -> tuple[NDArray[np.float64], NDArray[np.float64], int]:
    """Demodulate FM stereo signal.

    FM stereo uses:
    - L+R (mono) at baseband
    - 19 kHz pilot tone
    - L-R on 23-53 kHz (double sideband suppressed carrier at 38 kHz)

    Args:
        samples: Complex IQ samples.
        sample_rate: Input sample rate in Hz.
        audio_rate: Desired audio output rate in Hz.

    Returns:
        Tuple of (left channel, right channel, audio sample rate).
    """
    # First, get the baseband FM signal
    phase = np.unwrap(np.angle(samples))
    baseband = np.diff(phase)

    # Decimate to a workable rate for stereo processing
    # Need at least 76 kHz for stereo (38 kHz * 2)
    intermediate_rate = 152000
    decim1 = int(sample_rate / intermediate_rate)
    if decim1 > 1:
        baseband = signal.decimate(baseband, decim1)
        current_rate = sample_rate / decim1
    else:
        current_rate = sample_rate

    # Extract mono (L+R) - lowpass at 15 kHz
    mono = lowpass_filter(baseband, 15000, current_rate)

    # Look for pilot tone at 19 kHz
    # Create a bandpass filter around 19 kHz
    from rf_asset_discovery.dsp.filters import bandpass_filter

    pilot = bandpass_filter(baseband, 18500, 19500, current_rate)

    # Double the pilot to get 38 kHz carrier
    carrier = pilot * pilot  # This gives us 38 kHz component

    # Extract L-R using the recovered carrier
    # The L-R signal is at 23-53 kHz (centered at 38 kHz)
    stereo_band = bandpass_filter(baseband, 23000, 53000, current_rate)
    stereo_demod = stereo_band * np.sign(carrier[: len(stereo_band)])

    # Lowpass the stereo difference
    stereo_diff = lowpass_filter(stereo_demod, 15000, current_rate)

    # Combine to get L and R
    # Ensure same length
    min_len = min(len(mono), len(stereo_diff))
    mono = mono[:min_len]
    stereo_diff = stereo_diff[:min_len]

    left = mono + stereo_diff
    right = mono - stereo_diff

    # Decimate to audio rate
    decim2 = int(current_rate / audio_rate)
    if decim2 > 1:
        left = signal.decimate(left, decim2)
        right = signal.decimate(right, decim2)

    # Apply de-emphasis
    left = deemphasis_filter(left, audio_rate)
    right = deemphasis_filter(right, audio_rate)

    # Normalize
    max_val = max(np.max(np.abs(left)), np.max(np.abs(right)))
    if max_val > 0:
        left = left / max_val * 0.9
        right = right / max_val * 0.9

    return left.astype(np.float64), right.astype(np.float64), audio_rate


def am_demodulate(
    samples: NDArray[np.complex64],
    sample_rate: float,
    audio_rate: int = FM_AUDIO_RATE,
) -> tuple[NDArray[np.float64], int]:
    """Demodulate AM signal to audio.

    Uses envelope detection (magnitude of complex signal).

    Args:
        samples: Complex IQ samples.
        sample_rate: Input sample rate in Hz.
        audio_rate: Desired audio output rate in Hz.

    Returns:
        Tuple of (audio samples, audio sample rate).
    """
    # Envelope detection - just take magnitude
    envelope = np.abs(samples)

    # Remove DC (carrier component)
    audio = envelope - np.mean(envelope)

    # Low-pass filter
    audio = lowpass_filter(audio, audio_rate / 2, sample_rate)

    # Decimate
    decimation = int(sample_rate / audio_rate)
    if decimation > 1:
        audio = signal.decimate(audio, decimation)

    # Normalize
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = audio / max_val * 0.9

    return audio.astype(np.float64), audio_rate


def ssb_demodulate(
    samples: NDArray[np.complex64],
    sample_rate: float,
    audio_rate: int = FM_AUDIO_RATE,
    upper_sideband: bool = True,
) -> tuple[NDArray[np.float64], int]:
    """Demodulate SSB (Single Sideband) signal.

    Args:
        samples: Complex IQ samples.
        sample_rate: Input sample rate in Hz.
        audio_rate: Desired audio output rate in Hz.
        upper_sideband: True for USB, False for LSB.

    Returns:
        Tuple of (audio samples, audio sample rate).
    """
    # For SSB, we take real or imaginary part depending on sideband
    if upper_sideband:
        audio = np.real(samples)
    else:
        audio = np.imag(samples)

    # Bandpass filter for voice (300 Hz - 3000 Hz is typical)
    from rf_asset_discovery.dsp.filters import bandpass_filter

    audio = bandpass_filter(audio, 300, 3000, sample_rate)

    # Decimate
    decimation = int(sample_rate / audio_rate)
    if decimation > 1:
        audio = signal.decimate(audio, decimation)

    # Normalize
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = audio / max_val * 0.9

    return audio.astype(np.float64), audio_rate


def compute_signal_strength(samples: NDArray[np.complex64]) -> float:
    """Compute signal strength in dB.

    Args:
        samples: Complex IQ samples.

    Returns:
        Signal strength in dB.
    """
    power = np.mean(np.abs(samples) ** 2)
    return float(10 * np.log10(power + 1e-20))
