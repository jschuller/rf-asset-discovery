"""Tests for application layer."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest


class TestFMRadio:
    """Tests for FMRadio application."""

    def test_fm_radio_import(self):
        """Test that FMRadio imports correctly."""
        from sdr_toolkit.apps.fm_radio import FMRadio

        assert FMRadio is not None

    def test_fm_radio_init(self):
        """Test FMRadio initialization with valid parameters."""
        from sdr_toolkit.apps.fm_radio import FMRadio

        # Mock the device to avoid hardware dependency
        with patch("sdr_toolkit.apps.fm_radio.SDRDevice"):
            radio = FMRadio(freq_mhz=100.1, gain="auto", device_index=0)
            assert radio.freq_mhz == 100.1
            assert radio.gain == "auto"

    def test_fm_radio_frequency_range(self):
        """Test FMRadio accepts valid FM frequencies."""
        from sdr_toolkit.apps.fm_radio import FMRadio

        with patch("sdr_toolkit.apps.fm_radio.SDRDevice"):
            # Valid FM frequencies
            radio = FMRadio(freq_mhz=87.5)  # Low end
            assert radio.freq_mhz == 87.5

            radio = FMRadio(freq_mhz=108.0)  # High end
            assert radio.freq_mhz == 108.0


class TestAMRadio:
    """Tests for AMRadio application."""

    def test_am_radio_import(self):
        """Test that AMRadio imports correctly."""
        from sdr_toolkit.apps.am_radio import AMRadio

        assert AMRadio is not None

    def test_am_radio_init(self):
        """Test AMRadio initialization with valid parameters."""
        from sdr_toolkit.apps.am_radio import AMRadio

        with patch("sdr_toolkit.apps.am_radio.SDRDevice"):
            radio = AMRadio(freq_mhz=119.1, gain="auto", device_index=0)
            assert radio.freq_mhz == 119.1
            assert radio.gain == "auto"

    def test_am_radio_aircraft_band(self):
        """Test AMRadio with aircraft band frequencies."""
        from sdr_toolkit.apps.am_radio import AMRadio

        with patch("sdr_toolkit.apps.am_radio.SDRDevice"):
            # Aircraft band frequencies
            radio = AMRadio(freq_mhz=118.0)  # Low end
            assert radio.freq_mhz == 118.0

            radio = AMRadio(freq_mhz=137.0)  # High end
            assert radio.freq_mhz == 137.0


class TestSpectrumScanner:
    """Tests for SpectrumScanner application."""

    def test_scanner_import(self):
        """Test that SpectrumScanner imports correctly."""
        from sdr_toolkit.apps.scanner import SpectrumScanner

        assert SpectrumScanner is not None

    def test_scanner_init(self):
        """Test SpectrumScanner initialization."""
        from sdr_toolkit.apps.scanner import SpectrumScanner

        with patch("sdr_toolkit.apps.scanner.SDRDevice"):
            scanner = SpectrumScanner(gain="auto", threshold_db=-30)
            assert scanner.threshold_db == -30


class TestSignalRecorder:
    """Tests for SignalRecorder application."""

    def test_recorder_import(self):
        """Test that SignalRecorder imports correctly."""
        from sdr_toolkit.apps.recorder import SignalRecorder

        assert SignalRecorder is not None

    def test_recorder_init(self):
        """Test SignalRecorder initialization."""
        from sdr_toolkit.apps.recorder import SignalRecorder

        with patch("sdr_toolkit.apps.recorder.SDRDevice"):
            recorder = SignalRecorder(center_freq_mhz=100.1, gain="auto")
            assert recorder.center_freq_mhz == 100.1
