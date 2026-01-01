"""Tests for ADS-B decoder."""

from __future__ import annotations

import pytest


class TestADSBImports:
    """Test ADS-B decoder imports."""

    def test_decoder_imports(self):
        """Test that decoder module imports correctly."""
        try:
            from rf_asset_discovery.decoders import (
                ADSBMessage,
                decode_adsb_message,
                decode_adsb_messages,
                is_valid_adsb,
            )

            assert ADSBMessage is not None
            assert callable(decode_adsb_message)
            assert callable(decode_adsb_messages)
            assert callable(is_valid_adsb)
        except ImportError:
            pytest.skip("pyModeS not installed")


class TestIsValidADSB:
    """Tests for is_valid_adsb function."""

    def test_valid_message(self):
        """Test with valid ADS-B message."""
        try:
            from rf_asset_discovery.decoders import is_valid_adsb

            # Known valid ADS-B message (aircraft identification)
            msg = "8D4840D6202CC371C32CE0576098"
            assert is_valid_adsb(msg) is True
        except ImportError:
            pytest.skip("pyModeS not installed")

    def test_invalid_length(self):
        """Test with wrong length message."""
        try:
            from rf_asset_discovery.decoders import is_valid_adsb

            # Too short
            assert is_valid_adsb("8D4840D6") is False

            # Too long
            assert is_valid_adsb("8D4840D6202CC371C32CE0576098FFFF") is False
        except ImportError:
            pytest.skip("pyModeS not installed")

    def test_invalid_crc(self):
        """Test with invalid CRC."""
        try:
            from rf_asset_discovery.decoders import is_valid_adsb

            # Valid length but corrupted (bad CRC)
            msg = "8D4840D6202CC371C32CE0576099"  # Changed last byte
            assert is_valid_adsb(msg) is False
        except ImportError:
            pytest.skip("pyModeS not installed")


class TestDecodeADSBMessage:
    """Tests for decode_adsb_message function."""

    def test_decode_identification(self):
        """Test decoding aircraft identification message."""
        try:
            from rf_asset_discovery.decoders import decode_adsb_message

            # Aircraft identification message (typecode 1-4)
            msg = "8D4840D6202CC371C32CE0576098"
            result = decode_adsb_message(msg)

            assert result is not None
            assert result.icao == "4840D6"
            assert 1 <= result.typecode <= 4
            assert result.callsign is not None
        except ImportError:
            pytest.skip("pyModeS not installed")

    def test_decode_invalid_message(self):
        """Test decoding returns None for invalid message."""
        try:
            from rf_asset_discovery.decoders import decode_adsb_message

            # Invalid message
            result = decode_adsb_message("invalid")
            assert result is None
        except ImportError:
            pytest.skip("pyModeS not installed")


class TestDecodeADSBMessages:
    """Tests for decode_adsb_messages function."""

    def test_decode_multiple(self):
        """Test decoding multiple messages."""
        try:
            from rf_asset_discovery.decoders import decode_adsb_messages

            messages = [
                "8D4840D6202CC371C32CE0576098",  # Valid
                "invalid",  # Invalid
                "8D4840D6202CC371C32CE0576098",  # Valid duplicate
            ]

            results = decode_adsb_messages(messages)

            # Should only get 2 valid results
            assert len(results) == 2
        except ImportError:
            pytest.skip("pyModeS not installed")

    def test_decode_empty_list(self):
        """Test decoding empty list."""
        try:
            from rf_asset_discovery.decoders import decode_adsb_messages

            results = decode_adsb_messages([])
            assert len(results) == 0
        except ImportError:
            pytest.skip("pyModeS not installed")


class TestADSBMessage:
    """Tests for ADSBMessage dataclass."""

    def test_message_to_dict(self):
        """Test converting message to dictionary."""
        try:
            from rf_asset_discovery.decoders import ADSBMessage

            msg = ADSBMessage(
                raw="8D4840D6202CC371C32CE0576098",
                icao="4840D6",
                typecode=4,
                downlink_format=17,
                callsign="TEST123",
                message_type="identification",
            )

            d = msg.to_dict()
            assert d["icao"] == "4840D6"
            assert d["callsign"] == "TEST123"
            assert d["message_type"] == "identification"
        except ImportError:
            pytest.skip("pyModeS not installed")
