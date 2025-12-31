"""Tests for UI display functions."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest


class TestUIImports:
    """Test UI module imports."""

    def test_ui_module_imports(self):
        """Test that UI module imports correctly."""
        try:
            from sdr_toolkit.ui import display_scan_results, print_banner

            assert callable(display_scan_results)
            assert callable(print_banner)
        except ImportError:
            # Rich is optional
            pytest.skip("Rich not installed")


class TestPrintBanner:
    """Tests for print_banner function."""

    def test_print_banner_with_title(self):
        """Test banner with just title."""
        try:
            from sdr_toolkit.ui import print_banner

            # Should not raise
            print_banner("Test Title")
        except ImportError:
            pytest.skip("Rich not installed")

    def test_print_banner_with_subtitle(self):
        """Test banner with title and subtitle."""
        try:
            from sdr_toolkit.ui import print_banner

            # Should not raise
            print_banner("Test Title", "Test Subtitle")
        except ImportError:
            pytest.skip("Rich not installed")


class TestDisplayScanResults:
    """Tests for display_scan_results function."""

    def test_display_scan_results_empty(self):
        """Test display with no peaks."""
        try:
            from sdr_toolkit.ui import display_scan_results

            # Create mock scan result
            mock_result = MagicMock()
            mock_result.peaks = []
            mock_result.scan_time_seconds = 1.5
            mock_result.noise_floor_db = -60.0

            # Should not raise
            display_scan_results(mock_result)
        except ImportError:
            pytest.skip("Rich not installed")

    def test_display_scan_results_with_peaks(self):
        """Test display with some peaks."""
        try:
            from sdr_toolkit.ui import display_scan_results

            # Create mock peak
            mock_peak = MagicMock()
            mock_peak.frequency_hz = 100.1e6
            mock_peak.power_db = -25.0

            # Create mock scan result
            mock_result = MagicMock()
            mock_result.peaks = [mock_peak]
            mock_result.scan_time_seconds = 2.5
            mock_result.noise_floor_db = -55.0

            # Should not raise
            display_scan_results(mock_result)
        except ImportError:
            pytest.skip("Rich not installed")

    def test_display_scan_results_show_all(self):
        """Test display with show_all flag."""
        try:
            from sdr_toolkit.ui import display_scan_results

            mock_result = MagicMock()
            mock_result.peaks = []
            mock_result.scan_time_seconds = 1.0
            mock_result.noise_floor_db = -50.0

            # Should not raise with show_all=True
            display_scan_results(mock_result, show_all=True)
        except ImportError:
            pytest.skip("Rich not installed")
