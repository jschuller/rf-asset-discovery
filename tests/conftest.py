"""Pytest configuration and fixtures."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import numpy as np
import pytest

if TYPE_CHECKING:
    from numpy.typing import NDArray


class MockSDRDevice:
    """Mock SDR device for testing without hardware."""

    def __init__(
        self,
        sample_rate: float = 1.024e6,
        center_freq: float = 100.0e6,
        gain: float | str = "auto",
    ):
        self.sample_rate = sample_rate
        self.center_freq = center_freq
        self.gain = gain
        self._is_open = False

    def __enter__(self) -> "MockSDRDevice":
        self._is_open = True
        return self

    def __exit__(self, *args) -> None:
        self._is_open = False

    def read_samples(self, num_samples: int) -> np.ndarray:
        """Generate synthetic IQ samples with a known tone."""
        if not self._is_open:
            raise RuntimeError("Device not open")
        t = np.arange(num_samples) / self.sample_rate
        freq_offset = 10e3
        samples = np.exp(2j * np.pi * freq_offset * t)
        noise = (np.random.randn(num_samples) + 1j * np.random.randn(num_samples)) * 0.1
        return (samples + noise).astype(np.complex64)


@pytest.fixture
def mock_sdr_device() -> MockSDRDevice:
    """Provide a mock SDR device for testing."""
    return MockSDRDevice()


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for tests."""
    return tmp_path


@pytest.fixture
def sample_rate() -> float:
    """Default sample rate for tests."""
    return 1.024e6


@pytest.fixture
def audio_rate() -> int:
    """Default audio rate for tests."""
    return 48000


@pytest.fixture
def center_freq() -> float:
    """Default center frequency for tests."""
    return 100.0e6


@pytest.fixture
def synthetic_iq(sample_rate: float) -> NDArray[np.complex64]:
    """Generate synthetic IQ samples with a known tone.

    Creates a complex signal with a 10 kHz tone.
    """
    duration = 0.1  # 100ms
    num_samples = int(sample_rate * duration)
    t = np.arange(num_samples) / sample_rate

    # Create 10 kHz tone
    freq_offset = 10e3
    samples = np.exp(2j * np.pi * freq_offset * t)

    # Add some noise
    noise = (np.random.randn(num_samples) + 1j * np.random.randn(num_samples)) * 0.1
    samples = samples + noise

    return samples.astype(np.complex64)


@pytest.fixture
def synthetic_fm(sample_rate: float) -> NDArray[np.complex64]:
    """Generate synthetic FM modulated signal.

    Creates an FM signal with a 1 kHz audio tone.
    """
    duration = 0.1  # 100ms
    num_samples = int(sample_rate * duration)
    t = np.arange(num_samples) / sample_rate

    # Audio signal (1 kHz tone)
    audio_freq = 1000
    audio = np.sin(2 * np.pi * audio_freq * t)

    # FM modulation
    deviation = 75e3  # FM broadcast deviation
    phase = 2 * np.pi * deviation * np.cumsum(audio) / sample_rate
    samples = np.exp(1j * phase)

    return samples.astype(np.complex64)
