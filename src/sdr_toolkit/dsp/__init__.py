"""Digital Signal Processing module for SDR operations."""

from sdr_toolkit.dsp.demodulation import fm_demodulate
from sdr_toolkit.dsp.filters import (
    bandpass_filter,
    dc_block,
    deemphasis_filter,
    lowpass_filter,
)
from sdr_toolkit.dsp.spectrum import (
    compute_fft,
    compute_power_spectrum,
    compute_spectrogram,
    find_peaks,
)

__all__ = [
    # Spectrum
    "compute_fft",
    "compute_power_spectrum",
    "compute_spectrogram",
    "find_peaks",
    # Demodulation
    "fm_demodulate",
    # Filters
    "lowpass_filter",
    "bandpass_filter",
    "dc_block",
    "deemphasis_filter",
]
