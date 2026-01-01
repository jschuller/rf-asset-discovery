"""Tests for demodulation functions."""

from __future__ import annotations

import numpy as np
import pytest

from rf_asset_discovery.dsp.demodulation import (
    am_demodulate,
    compute_signal_strength,
    fm_demodulate,
)


class TestFMDemodulate:
    """Tests for fm_demodulate function."""

    def test_fm_demod_output_shape(
        self, synthetic_fm: np.ndarray, sample_rate: float, audio_rate: int
    ) -> None:
        """Test FM demod output has correct shape."""
        audio, rate = fm_demodulate(synthetic_fm, sample_rate, audio_rate)

        assert rate == audio_rate
        # Audio should be shorter due to decimation
        expected_length = int(len(synthetic_fm) / (sample_rate / audio_rate))
        assert abs(len(audio) - expected_length) < 100

    def test_fm_demod_normalized(
        self, synthetic_fm: np.ndarray, sample_rate: float
    ) -> None:
        """Test FM demod output is normalized."""
        audio, _ = fm_demodulate(synthetic_fm, sample_rate)

        # Should be normalized to [-1, 1] range with some headroom
        assert np.max(np.abs(audio)) <= 1.0

    def test_fm_demod_no_nan(
        self, synthetic_fm: np.ndarray, sample_rate: float
    ) -> None:
        """Test FM demod doesn't produce NaN."""
        audio, _ = fm_demodulate(synthetic_fm, sample_rate)
        assert not np.any(np.isnan(audio))

    def test_fm_demod_with_dc(self, sample_rate: float) -> None:
        """Test FM demod removes DC offset."""
        # Create signal with DC offset
        num_samples = int(sample_rate * 0.1)
        samples = np.exp(1j * np.linspace(0, 100, num_samples))
        samples = (samples + 0.5).astype(np.complex64)

        audio, _ = fm_demodulate(samples, sample_rate)

        # DC should be removed
        assert abs(np.mean(audio)) < 0.1


class TestAMDemodulate:
    """Tests for am_demodulate function."""

    def test_am_demod_shape(self, sample_rate: float, audio_rate: int) -> None:
        """Test AM demod output shape."""
        # Create AM signal
        num_samples = int(sample_rate * 0.1)
        t = np.arange(num_samples) / sample_rate
        audio_freq = 1000
        carrier = np.exp(1j * 2 * np.pi * 0 * t)
        modulation = 1 + 0.5 * np.sin(2 * np.pi * audio_freq * t)
        samples = (carrier * modulation).astype(np.complex64)

        audio, rate = am_demodulate(samples, sample_rate, audio_rate)

        assert rate == audio_rate
        assert len(audio) > 0

    def test_am_demod_normalized(self, sample_rate: float) -> None:
        """Test AM demod output is normalized."""
        num_samples = int(sample_rate * 0.1)
        samples = np.random.randn(num_samples).astype(np.complex64)

        audio, _ = am_demodulate(samples, sample_rate)
        assert np.max(np.abs(audio)) <= 1.0


class TestComputeSignalStrength:
    """Tests for compute_signal_strength function."""

    def test_signal_strength_db(self) -> None:
        """Test signal strength in dB."""
        # Create signal with known power
        samples = np.ones(1000, dtype=np.complex64)
        strength = compute_signal_strength(samples)

        # Power of 1 = 0 dB
        assert strength == pytest.approx(0, abs=1)

    def test_signal_strength_weak(self) -> None:
        """Test signal strength for weak signal."""
        samples = np.ones(1000, dtype=np.complex64) * 0.01
        strength = compute_signal_strength(samples)

        # Should be around -40 dB
        assert strength < -30

    def test_signal_strength_strong(self) -> None:
        """Test signal strength for strong signal."""
        samples = np.ones(1000, dtype=np.complex64) * 10
        strength = compute_signal_strength(samples)

        # Should be around +20 dB
        assert strength > 10


class TestFMWithRealPattern:
    """Integration tests with realistic FM patterns."""

    def test_fm_silence(self, sample_rate: float) -> None:
        """Test FM demod with silence (no modulation)."""
        num_samples = int(sample_rate * 0.1)
        # Constant phase = no audio
        samples = np.ones(num_samples, dtype=np.complex64)

        audio, _ = fm_demodulate(samples, sample_rate)

        # Should be mostly silence
        assert np.std(audio) < 0.1

    def test_fm_with_noise(self, synthetic_fm: np.ndarray, sample_rate: float) -> None:
        """Test FM demod with noisy signal."""
        noise = (
            np.random.randn(len(synthetic_fm)) + 1j * np.random.randn(len(synthetic_fm))
        ) * 0.5
        noisy_signal = synthetic_fm + noise.astype(np.complex64)

        audio, _ = fm_demodulate(noisy_signal, sample_rate)

        # Should still produce valid output
        assert not np.any(np.isnan(audio))
        assert not np.any(np.isinf(audio))
