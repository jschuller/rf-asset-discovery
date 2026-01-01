"""Digital Signal Processing module for SDR operations."""

from rf_asset_discovery.dsp.demodulation import fm_demodulate
from rf_asset_discovery.dsp.filters import (
    bandpass_filter,
    dc_block,
    deemphasis_filter,
    lowpass_filter,
)
from rf_asset_discovery.dsp.spectrum import (
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
