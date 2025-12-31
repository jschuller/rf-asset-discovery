"""Tests for SDR device management."""

from __future__ import annotations

import pytest

from sdr_toolkit.core.device import SDRDevice
from sdr_toolkit.core.exceptions import DeviceError


class TestSDRDevice:
    """Tests for SDRDevice class."""

    def test_device_creation(self) -> None:
        """Test device creation with defaults."""
        device = SDRDevice()
        assert device.center_freq == 100.0e6
        assert device.gain == "auto"
        assert not device.is_open

    def test_device_custom_params(self) -> None:
        """Test device creation with custom parameters."""
        device = SDRDevice(
            sample_rate=2.4e6,
            center_freq=433e6,
            gain=30,
        )
        assert device.sample_rate == 2.4e6
        assert device.center_freq == 433e6
        assert device.gain == 30

    def test_read_without_open(self) -> None:
        """Test reading without opening device."""
        device = SDRDevice()

        with pytest.raises(DeviceError):
            device.read_samples(1024)

    def test_device_info_closed(self) -> None:
        """Test getting device info when closed."""
        device = SDRDevice()
        info = device.get_device_info()

        assert "sample_rate" in info
        assert "center_freq" in info
        assert "is_open" in info
        assert info["is_open"] is False

    def test_set_frequency_before_open(self) -> None:
        """Test setting frequency before opening."""
        device = SDRDevice()
        device.set_center_freq(433e6)
        assert device.center_freq == 433e6

    def test_set_gain_before_open(self) -> None:
        """Test setting gain before opening."""
        device = SDRDevice()
        device.set_gain(30)
        assert device.gain == 30

    def test_set_sample_rate_before_open(self) -> None:
        """Test setting sample rate before opening."""
        device = SDRDevice()
        device.set_sample_rate(2.4e6)
        assert device.sample_rate == 2.4e6


class TestDeviceExceptions:
    """Tests for device exception handling."""

    def test_read_without_open(self) -> None:
        """Test reading without opening device."""
        device = SDRDevice()

        with pytest.raises(DeviceError) as exc_info:
            device.read_samples(1024)

        assert "not open" in str(exc_info.value).lower()


# Note: Tests requiring actual device mocking are marked as integration tests
# and should be run with a real device or with pytest-mock properly configured.
# The core functionality is tested above without requiring device access.
