"""ADS-B message decoder using pyModeS.

ADS-B (Automatic Dependent Surveillance-Broadcast) is a surveillance
technology where aircraft broadcast their position and identification.

Requires: pip install pyModeS

Note: This module provides basic message decoding only.
For live ADS-B reception, you need:
- RTL-SDR tuned to 1090 MHz
- dump1090 or similar demodulator
- This module to decode the hex messages
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

try:
    import pyModeS as pms

    PYMODES_AVAILABLE = True
except ImportError:
    PYMODES_AVAILABLE = False
    pms = None


@dataclass
class ADSBMessage:
    """Decoded ADS-B message."""

    raw: str
    icao: str
    typecode: int
    downlink_format: int

    # Optional fields depending on message type
    callsign: str | None = None
    altitude: int | None = None
    velocity: dict[str, Any] | None = None
    position: dict[str, float] | None = None
    squawk: str | None = None
    category: str | None = None

    # Metadata
    message_type: str = "unknown"
    valid: bool = True
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "raw": self.raw,
            "icao": self.icao,
            "typecode": self.typecode,
            "downlink_format": self.downlink_format,
            "callsign": self.callsign,
            "altitude": self.altitude,
            "velocity": self.velocity,
            "position": self.position,
            "squawk": self.squawk,
            "category": self.category,
            "message_type": self.message_type,
            "valid": self.valid,
        }


def is_valid_adsb(msg: str) -> bool:
    """Check if a message is a valid ADS-B message.

    Args:
        msg: Hex string of the raw message.

    Returns:
        True if valid ADS-B message.
    """
    if not PYMODES_AVAILABLE:
        raise ImportError("pyModeS not installed. Install with: pip install pyModeS")

    # Clean message
    msg = msg.strip().upper()

    # Check length (112 bits = 28 hex chars for extended squitter)
    if len(msg) != 28:
        return False

    # Check CRC
    try:
        return pms.crc(msg) == 0
    except Exception:
        return False


def decode_adsb_message(msg: str) -> ADSBMessage | None:
    """Decode a single ADS-B message.

    Args:
        msg: Hex string of the raw message (28 characters for ADS-B).

    Returns:
        Decoded message or None if invalid.
    """
    if not PYMODES_AVAILABLE:
        raise ImportError("pyModeS not installed. Install with: pip install pyModeS")

    # Clean message
    msg = msg.strip().upper()

    # Validate
    if len(msg) != 28:
        return None

    # Check CRC
    try:
        if pms.crc(msg) != 0:
            return None
    except Exception:
        return None

    # Get basic info
    try:
        df = pms.df(msg)
        icao = pms.adsb.icao(msg)
        tc = pms.adsb.typecode(msg)
    except Exception as e:
        logger.debug("Failed to decode basic info: %s", e)
        return None

    # Create message object
    result = ADSBMessage(
        raw=msg,
        icao=icao,
        typecode=tc,
        downlink_format=df,
    )

    # Decode based on typecode
    try:
        if 1 <= tc <= 4:
            # Aircraft identification
            result.callsign = pms.adsb.callsign(msg)
            result.category = pms.adsb.category(msg)
            result.message_type = "identification"

        elif 5 <= tc <= 8:
            # Surface position
            result.message_type = "surface_position"
            # Note: CPR decoding requires even/odd message pairs

        elif 9 <= tc <= 18:
            # Airborne position (barometric altitude)
            result.altitude = pms.adsb.altitude(msg)
            result.message_type = "airborne_position"
            # Note: CPR decoding requires even/odd message pairs

        elif tc == 19:
            # Airborne velocity
            velocity = pms.adsb.velocity(msg)
            if velocity:
                result.velocity = {
                    "speed_kts": velocity[0],
                    "heading_deg": velocity[1],
                    "vertical_rate_fpm": velocity[2],
                    "speed_type": velocity[3],  # "GS" or "TAS"
                }
            result.message_type = "velocity"

        elif 20 <= tc <= 22:
            # Airborne position (GNSS altitude)
            result.altitude = pms.adsb.altitude(msg)
            result.message_type = "airborne_position_gnss"

        elif tc == 28:
            # Aircraft status
            result.message_type = "aircraft_status"

        elif tc == 29:
            # Target state and status
            result.message_type = "target_state"

        elif tc == 31:
            # Aircraft operational status
            result.message_type = "operational_status"

        else:
            result.message_type = f"typecode_{tc}"

    except Exception as e:
        result.errors.append(str(e))
        logger.debug("Error decoding message: %s", e)

    return result


def decode_adsb_messages(messages: list[str]) -> list[ADSBMessage]:
    """Decode multiple ADS-B messages.

    Args:
        messages: List of hex strings.

    Returns:
        List of successfully decoded messages.
    """
    if not PYMODES_AVAILABLE:
        raise ImportError("pyModeS not installed. Install with: pip install pyModeS")

    results = []
    for msg in messages:
        decoded = decode_adsb_message(msg)
        if decoded is not None:
            results.append(decoded)

    return results


def decode_callsign(msg: str) -> str | None:
    """Extract callsign from an identification message.

    Args:
        msg: Hex string of the raw message.

    Returns:
        Callsign string or None.
    """
    if not PYMODES_AVAILABLE:
        raise ImportError("pyModeS not installed. Install with: pip install pyModeS")

    try:
        tc = pms.adsb.typecode(msg)
        if 1 <= tc <= 4:
            return pms.adsb.callsign(msg)
    except Exception:
        pass
    return None


def decode_altitude(msg: str) -> int | None:
    """Extract altitude from a position message.

    Args:
        msg: Hex string of the raw message.

    Returns:
        Altitude in feet or None.
    """
    if not PYMODES_AVAILABLE:
        raise ImportError("pyModeS not installed. Install with: pip install pyModeS")

    try:
        tc = pms.adsb.typecode(msg)
        if 9 <= tc <= 18 or 20 <= tc <= 22:
            return pms.adsb.altitude(msg)
    except Exception:
        pass
    return None


def decode_velocity(msg: str) -> dict[str, Any] | None:
    """Extract velocity from a velocity message.

    Args:
        msg: Hex string of the raw message.

    Returns:
        Dictionary with speed, heading, vertical rate, or None.
    """
    if not PYMODES_AVAILABLE:
        raise ImportError("pyModeS not installed. Install with: pip install pyModeS")

    try:
        tc = pms.adsb.typecode(msg)
        if tc == 19:
            velocity = pms.adsb.velocity(msg)
            if velocity:
                return {
                    "speed_kts": velocity[0],
                    "heading_deg": velocity[1],
                    "vertical_rate_fpm": velocity[2],
                    "speed_type": velocity[3],
                }
    except Exception:
        pass
    return None


def get_icao_info(icao: str) -> dict[str, str]:
    """Get basic info about an ICAO address.

    Args:
        icao: 6-character ICAO hex address.

    Returns:
        Dictionary with country registration info.
    """
    # ICAO address ranges for major countries
    # This is a simplified lookup - real lookups would use a database
    icao = icao.upper()
    prefix = icao[:2]

    country_map = {
        "A0": "United States",
        "A1": "United States",
        "A2": "United States",
        "A3": "United States",
        "A4": "United States",
        "A5": "United States",
        "A6": "United States",
        "A7": "United States",
        "A8": "United States",
        "A9": "United States",
        "AA": "United States",
        "AB": "United States",
        "AC": "United States",
        "AD": "United States",
        "AE": "United States",
        "AF": "United States",
        "40": "United Kingdom",
        "41": "United Kingdom",
        "42": "United Kingdom",
        "43": "United Kingdom",
        "38": "France",
        "39": "France",
        "3A": "France",
        "3B": "France",
        "3C": "Germany",
        "3D": "Germany",
        "3E": "Germany",
        "3F": "Germany",
        "C0": "Canada",
        "C1": "Canada",
        "C2": "Canada",
        "C3": "Canada",
        "78": "China",
        "79": "China",
        "7A": "China",
        "7B": "China",
        "7C": "Australia",
        "7D": "Australia",
        "84": "Japan",
        "85": "Japan",
    }

    country = country_map.get(prefix, "Unknown")
    return {
        "icao": icao,
        "country": country,
    }
