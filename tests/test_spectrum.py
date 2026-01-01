"""Tests for spectrum analysis functions."""

from __future__ import annotations

import numpy as np
import pytest

from rf_asset_discovery.dsp.spectrum import (
    compute_fft,
    compute_power_spectrum,
    compute_power_spectrum_hz,
    estimate_noise_floor,
    find_peaks,
    get_window,
)


class TestGetWindow:
    """Tests for get_window function."""

    def test_hamming_window(self) -> None:
        """Test Hamming window generation."""
        window = get_window("hamming", 256)
        assert len(window) == 256
        assert window[0] < window[128]  # Should be tapered

    def test_none_window(self) -> None:
        """Test no window (rectangular)."""
        window = get_window("none", 256)
        assert len(window) == 256
        assert np.allclose(window, 1.0)

    def test_hann_window(self) -> None:
        """Test Hann window."""
        window = get_window("hann", 512)
        assert len(window) == 512
        assert window[0] < 0.01  # Should be near zero at edges


class TestComputeFFT:
    """Tests for compute_fft function."""

    def test_fft_shape(self, synthetic_iq: np.ndarray) -> None:
        """Test FFT output shape."""
        fft_size = 1024
        result = compute_fft(synthetic_iq, fft_size=fft_size)
        assert len(result) == fft_size

    def test_fft_peak_detection(self, sample_rate: float) -> None:
        """Test that FFT detects a known frequency."""
        # Create a pure tone at 50 kHz offset
        num_samples = 2048
        t = np.arange(num_samples) / sample_rate
        freq_offset = 50e3
        samples = np.exp(2j * np.pi * freq_offset * t).astype(np.complex64)

        fft_result = compute_fft(samples, fft_size=num_samples, shift=True)
        power = np.abs(fft_result) ** 2

        # Find peak
        peak_bin = np.argmax(power)
        expected_bin = num_samples // 2 + int(freq_offset / sample_rate * num_samples)

        assert abs(peak_bin - expected_bin) < 3  # Within 3 bins

    def test_fft_zero_padding(self) -> None:
        """Test FFT with zero padding."""
        samples = np.random.randn(100).astype(np.complex64)
        fft_size = 256
        result = compute_fft(samples, fft_size=fft_size)
        assert len(result) == fft_size


class TestComputePowerSpectrum:
    """Tests for compute_power_spectrum function."""

    def test_power_spectrum_shape(self, synthetic_iq: np.ndarray) -> None:
        """Test power spectrum output shape."""
        fft_size = 1024
        freqs, power = compute_power_spectrum(synthetic_iq, fft_size=fft_size)
        assert len(freqs) == fft_size
        assert len(power) == fft_size

    def test_power_spectrum_frequency_range(self, synthetic_iq: np.ndarray) -> None:
        """Test frequency axis range."""
        freqs, _ = compute_power_spectrum(synthetic_iq)
        assert freqs[0] == pytest.approx(-0.5, rel=0.01)
        assert freqs[-1] == pytest.approx(0.5, rel=0.01)

    def test_power_spectrum_db_scale(self, synthetic_iq: np.ndarray) -> None:
        """Test dB scale output."""
        _, power = compute_power_spectrum(synthetic_iq, log_scale=True)
        # Power in dB should be reasonable (not NaN or Inf)
        assert np.all(np.isfinite(power))
        assert np.max(power) < 100  # Reasonable dB range
        assert np.min(power) > -200


class TestComputePowerSpectrumHz:
    """Tests for compute_power_spectrum_hz function."""

    def test_frequency_in_hz(
        self, synthetic_iq: np.ndarray, sample_rate: float, center_freq: float
    ) -> None:
        """Test frequency axis in Hz."""
        freqs, power = compute_power_spectrum_hz(
            synthetic_iq, sample_rate, center_freq
        )

        # Check frequency range
        expected_start = center_freq - sample_rate / 2
        expected_end = center_freq + sample_rate / 2

        assert freqs[0] == pytest.approx(expected_start, rel=0.01)
        assert freqs[-1] == pytest.approx(expected_end, rel=0.01)


class TestFindPeaks:
    """Tests for find_peaks function."""

    def test_find_single_peak(self) -> None:
        """Test finding a single peak."""
        # Create spectrum with one peak
        power = np.ones(256) * -60
        power[128] = -20  # Strong peak in center

        peaks = find_peaks(power, threshold_db=-30)
        assert len(peaks) == 1
        assert peaks[0][0] == 128
        assert peaks[0][1] == pytest.approx(-20)

    def test_find_multiple_peaks(self) -> None:
        """Test finding multiple peaks."""
        power = np.ones(256) * -60
        power[64] = -25
        power[128] = -20
        power[192] = -28

        peaks = find_peaks(power, threshold_db=-30, min_distance=20)
        assert len(peaks) == 3

    def test_threshold_filtering(self) -> None:
        """Test that threshold filters out weak signals."""
        power = np.ones(256) * -60
        power[128] = -35  # Below threshold

        peaks = find_peaks(power, threshold_db=-30)
        assert len(peaks) == 0


class TestEstimateNoiseFloor:
    """Tests for estimate_noise_floor function."""

    def test_noise_floor_estimation(self) -> None:
        """Test noise floor estimation."""
        # Create spectrum with noise at -50 dB
        power = np.random.randn(1024) * 2 - 50

        noise_floor = estimate_noise_floor(power)
        assert -60 < noise_floor < -40

    def test_noise_floor_with_signal(self) -> None:
        """Test noise floor with strong signal present."""
        power = np.random.randn(1024) * 2 - 50
        power[512] = -10  # Strong signal

        noise_floor = estimate_noise_floor(power)
        # Should still estimate the noise, not the signal
        assert noise_floor < -30
