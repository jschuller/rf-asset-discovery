"""Tests for CLI entry points."""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest


class TestCLIImports:
    """Test that CLI modules import without error."""

    def test_main_imports(self):
        """Test that main CLI module imports correctly."""
        from rf_asset_discovery.cli import main

        assert hasattr(main, "fm_radio")
        assert hasattr(main, "am_radio")
        assert hasattr(main, "scanner")
        assert hasattr(main, "recorder")

    def test_fm_radio_function_exists(self):
        """Test that fm_radio function is callable."""
        from rf_asset_discovery.cli.main import fm_radio

        assert callable(fm_radio)

    def test_am_radio_function_exists(self):
        """Test that am_radio function is callable."""
        from rf_asset_discovery.cli.main import am_radio

        assert callable(am_radio)

    def test_scanner_function_exists(self):
        """Test that scanner function is callable."""
        from rf_asset_discovery.cli.main import scanner

        assert callable(scanner)

    def test_recorder_function_exists(self):
        """Test that recorder function is callable."""
        from rf_asset_discovery.cli.main import recorder

        assert callable(recorder)


class TestCLIArguments:
    """Test CLI argument parsing."""

    def test_fm_radio_help(self):
        """Test FM radio help text."""
        from rf_asset_discovery.cli.main import fm_radio

        with patch.object(sys, "argv", ["sdr-fm", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                fm_radio()
            assert exc_info.value.code == 0

    def test_am_radio_help(self):
        """Test AM radio help text."""
        from rf_asset_discovery.cli.main import am_radio

        with patch.object(sys, "argv", ["sdr-am", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                am_radio()
            assert exc_info.value.code == 0

    def test_scanner_help(self):
        """Test scanner help text."""
        from rf_asset_discovery.cli.main import scanner

        with patch.object(sys, "argv", ["sdr-scan", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                scanner()
            assert exc_info.value.code == 0

    def test_recorder_help(self):
        """Test recorder help text with required args."""
        from rf_asset_discovery.cli.main import recorder

        with patch.object(sys, "argv", ["sdr-record", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                recorder()
            assert exc_info.value.code == 0


class TestLogging:
    """Test logging setup."""

    def test_setup_logging_function_exists(self):
        """Test that setup_logging function exists and is callable."""
        from rf_asset_discovery.cli.main import setup_logging

        assert callable(setup_logging)

    def test_setup_logging_no_errors(self):
        """Test that setup_logging runs without errors."""
        from rf_asset_discovery.cli.main import setup_logging

        # Should not raise
        setup_logging(verbose=True)
        setup_logging(verbose=False)


class TestSurveyCLI:
    """Tests for survey CLI commands."""

    def test_survey_function_exists(self):
        """Test that spectrum_survey function is callable."""
        from rf_asset_discovery.cli.main import spectrum_survey

        assert callable(spectrum_survey)

    def test_survey_help(self):
        """Test survey help text."""
        from rf_asset_discovery.cli.main import spectrum_survey

        with patch.object(sys, "argv", ["sdr-survey", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                spectrum_survey()
            assert exc_info.value.code == 0

    def test_survey_create_help(self):
        """Test survey create subcommand help."""
        from rf_asset_discovery.cli.main import spectrum_survey

        with patch.object(sys, "argv", ["sdr-survey", "create", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                spectrum_survey()
            assert exc_info.value.code == 0

    def test_survey_list_help(self):
        """Test survey list subcommand help."""
        from rf_asset_discovery.cli.main import spectrum_survey

        with patch.object(sys, "argv", ["sdr-survey", "list", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                spectrum_survey()
            assert exc_info.value.code == 0

    def test_survey_status_help(self):
        """Test survey status subcommand help."""
        from rf_asset_discovery.cli.main import spectrum_survey

        with patch.object(sys, "argv", ["sdr-survey", "status", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                spectrum_survey()
            assert exc_info.value.code == 0

    def test_survey_resume_help(self):
        """Test survey resume subcommand help."""
        from rf_asset_discovery.cli.main import spectrum_survey

        with patch.object(sys, "argv", ["sdr-survey", "resume", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                spectrum_survey()
            assert exc_info.value.code == 0

    def test_survey_next_help(self):
        """Test survey next subcommand help."""
        from rf_asset_discovery.cli.main import spectrum_survey

        with patch.object(sys, "argv", ["sdr-survey", "next", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                spectrum_survey()
            assert exc_info.value.code == 0
