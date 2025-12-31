"""Watch configuration models for spectrum monitoring.

Defines Pydantic models for watch configuration and natural language parsing
for converting user intents into structured watch configurations.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class FrequencyBand(str, Enum):
    """Predefined frequency bands for monitoring.

    Based on US legal receive bands from observability.py.
    """

    FM_BROADCAST = "fm_broadcast"
    AM_BROADCAST = "am_broadcast"
    AIRCRAFT_VHF = "aircraft_vhf"
    MARINE_VHF = "marine_vhf"
    AMATEUR_2M = "amateur_2m"
    AMATEUR_70CM = "amateur_70cm"
    NOAA_WEATHER = "noaa_weather"
    NOAA_SATELLITE = "noaa_satellite"
    FRS_GMRS = "frs_gmrs"
    ADSB = "adsb"
    CUSTOM = "custom"


# Band frequency ranges in Hz
BAND_RANGES: dict[FrequencyBand, tuple[float, float]] = {
    FrequencyBand.FM_BROADCAST: (87.5e6, 108.0e6),
    FrequencyBand.AM_BROADCAST: (0.5e6, 1.7e6),
    FrequencyBand.AIRCRAFT_VHF: (118.0e6, 137.0e6),
    FrequencyBand.MARINE_VHF: (156.0e6, 162.025e6),
    FrequencyBand.AMATEUR_2M: (144.0e6, 148.0e6),
    FrequencyBand.AMATEUR_70CM: (420.0e6, 450.0e6),
    FrequencyBand.NOAA_WEATHER: (162.4e6, 162.55e6),
    FrequencyBand.NOAA_SATELLITE: (137.0e6, 138.0e6),
    FrequencyBand.FRS_GMRS: (462.5625e6, 467.7125e6),
    FrequencyBand.ADSB: (1090.0e6, 1090.0e6),
}

# Common frequencies of interest
NOTABLE_FREQUENCIES: dict[float, str] = {
    121.5e6: "Aircraft Emergency",
    156.8e6: "Marine Channel 16 (Distress)",
    162.55e6: "NOAA Weather",
    146.52e6: "2m FM Calling",
    446.0e6: "70cm FM Calling",
}


class AlertCondition(BaseModel):
    """A single alert condition to monitor.

    Defines when an alert should be triggered based on spectrum activity.
    """

    condition_type: Literal[
        "new_signal", "threshold_breach", "band_activity", "signal_loss"
    ]
    threshold_db: float | None = None
    frequency_hz: float | None = None
    frequency_tolerance_hz: float = 50000
    activity_change_percent: float | None = None
    cooldown_seconds: int = 60

    def describe(self) -> str:
        """Return human-readable description of the condition."""
        if self.condition_type == "new_signal":
            if self.frequency_hz:
                freq_mhz = self.frequency_hz / 1e6
                return f"New signal near {freq_mhz:.3f} MHz"
            return "Any new signal detected"
        elif self.condition_type == "threshold_breach":
            return f"Signal exceeds {self.threshold_db} dB"
        elif self.condition_type == "band_activity":
            return f"Band activity changes by {self.activity_change_percent}%"
        elif self.condition_type == "signal_loss":
            if self.frequency_hz:
                freq_mhz = self.frequency_hz / 1e6
                return f"Signal lost at {freq_mhz:.3f} MHz"
            return "Any baseline signal lost"
        return str(self.condition_type)


class WatchConfig(BaseModel):
    """Configuration for a spectrum watch.

    Defines what to monitor, when to alert, and how to notify.
    """

    watch_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    description: str | None = None
    bands: list[FrequencyBand] = Field(default_factory=list)
    custom_range: tuple[float, float] | None = None
    alert_conditions: list[AlertCondition] = Field(default_factory=list)
    scan_interval_seconds: float = 5.0
    dwell_time_ms: float = 100
    threshold_db: float = -30.0
    baseline_duration_seconds: float = 60.0
    baseline_scans: int = 12
    notifications: list[str] = Field(default_factory=lambda: ["console"])
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def get_frequency_ranges(self) -> list[tuple[float, float]]:
        """Get all frequency ranges to monitor.

        Returns:
            List of (start_hz, end_hz) tuples.
        """
        ranges: list[tuple[float, float]] = []

        for band in self.bands:
            if band in BAND_RANGES:
                ranges.append(BAND_RANGES[band])

        if self.custom_range:
            ranges.append(self.custom_range)

        return ranges

    def get_alert_frequencies(self) -> list[float]:
        """Get specific frequencies to monitor for alerts.

        Returns:
            List of frequencies in Hz.
        """
        return [
            cond.frequency_hz
            for cond in self.alert_conditions
            if cond.frequency_hz is not None
        ]


class WatchState(BaseModel):
    """Runtime state of a spectrum watch."""

    config: WatchConfig
    status: Literal["idle", "baseline", "watching", "alerting", "paused", "stopped"] = (
        "idle"
    )
    baseline_established: bool = False
    baseline_scans_completed: int = 0
    last_scan_time: datetime | None = None
    started_at: datetime | None = None
    scans_completed: int = 0
    alerts_sent: int = 0
    error: str | None = None


class Alert(BaseModel):
    """A triggered alert from spectrum monitoring."""

    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    watch_id: str
    condition: AlertCondition
    triggered_at: datetime = Field(default_factory=datetime.now)
    frequency_hz: float
    power_db: float
    message: str
    notified: bool = False
    acknowledged: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "alert_id": self.alert_id,
            "watch_id": self.watch_id,
            "condition_type": self.condition.condition_type,
            "triggered_at": self.triggered_at.isoformat(),
            "frequency_hz": self.frequency_hz,
            "frequency_mhz": self.frequency_hz / 1e6,
            "power_db": self.power_db,
            "message": self.message,
            "notified": self.notified,
            "acknowledged": self.acknowledged,
        }


# =============================================================================
# Natural Language Parsing
# =============================================================================

# Keyword mappings for band detection
BAND_KEYWORDS: dict[str, FrequencyBand] = {
    "fm": FrequencyBand.FM_BROADCAST,
    "fm broadcast": FrequencyBand.FM_BROADCAST,
    "radio": FrequencyBand.FM_BROADCAST,
    "am": FrequencyBand.AM_BROADCAST,
    "am broadcast": FrequencyBand.AM_BROADCAST,
    "aircraft": FrequencyBand.AIRCRAFT_VHF,
    "aviation": FrequencyBand.AIRCRAFT_VHF,
    "air": FrequencyBand.AIRCRAFT_VHF,
    "plane": FrequencyBand.AIRCRAFT_VHF,
    "airplane": FrequencyBand.AIRCRAFT_VHF,
    "marine": FrequencyBand.MARINE_VHF,
    "boat": FrequencyBand.MARINE_VHF,
    "ship": FrequencyBand.MARINE_VHF,
    "amateur": FrequencyBand.AMATEUR_2M,
    "ham": FrequencyBand.AMATEUR_2M,
    "2m": FrequencyBand.AMATEUR_2M,
    "2 meter": FrequencyBand.AMATEUR_2M,
    "70cm": FrequencyBand.AMATEUR_70CM,
    "70 cm": FrequencyBand.AMATEUR_70CM,
    "weather": FrequencyBand.NOAA_WEATHER,
    "noaa": FrequencyBand.NOAA_WEATHER,
    "satellite": FrequencyBand.NOAA_SATELLITE,
    "frs": FrequencyBand.FRS_GMRS,
    "gmrs": FrequencyBand.FRS_GMRS,
    "walkie": FrequencyBand.FRS_GMRS,
    "adsb": FrequencyBand.ADSB,
    "ads-b": FrequencyBand.ADSB,
    "transponder": FrequencyBand.ADSB,
}

# Regex patterns for parsing
FREQ_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:mhz|MHz|Mhz|M)",
    re.IGNORECASE,
)
THRESHOLD_PATTERN = re.compile(
    r"(?:exceeds?|above|over|greater than|>)\s*(-?\d+(?:\.\d+)?)\s*(?:db|dB)?",
    re.IGNORECASE,
)
RANGE_PATTERN = re.compile(
    r"(?:between|from)\s*(\d+(?:\.\d+)?)\s*(?:to|-|and)\s*(\d+(?:\.\d+)?)\s*(?:mhz|MHz)?",
    re.IGNORECASE,
)
PERCENT_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:%|percent)",
    re.IGNORECASE,
)


def parse_natural_language(intent: str) -> WatchConfig:
    """Parse natural language intent into a WatchConfig.

    Supports patterns like:
    - "Watch the aircraft band and alert me if anything appears on 121.5 MHz"
    - "Monitor FM band, alert if any signal exceeds -10 dB"
    - "Alert me to any new signals between 400-410 MHz"

    Args:
        intent: Natural language description of what to watch.

    Returns:
        WatchConfig with parsed parameters.
    """
    intent_lower = intent.lower()

    # Detect bands
    bands: list[FrequencyBand] = []
    for keyword, band in BAND_KEYWORDS.items():
        if keyword in intent_lower and band not in bands:
            bands.append(band)

    # Extract specific frequencies (in MHz)
    freq_matches = FREQ_PATTERN.findall(intent)
    alert_frequencies = [float(f) * 1e6 for f in freq_matches]

    # Extract threshold
    threshold_db = -30.0  # default
    threshold_match = THRESHOLD_PATTERN.search(intent)
    if threshold_match:
        threshold_db = float(threshold_match.group(1))

    # Extract custom range
    custom_range: tuple[float, float] | None = None
    range_match = RANGE_PATTERN.search(intent)
    if range_match:
        start = float(range_match.group(1)) * 1e6
        end = float(range_match.group(2)) * 1e6
        custom_range = (start, end)
        bands.append(FrequencyBand.CUSTOM)

    # Extract percentage for activity monitoring
    activity_percent: float | None = None
    percent_match = PERCENT_PATTERN.search(intent)
    if percent_match:
        activity_percent = float(percent_match.group(1))

    # Build alert conditions
    conditions: list[AlertCondition] = []

    # Check for "new" signals keyword
    detect_new = any(
        word in intent_lower for word in ["new", "appear", "emerges", "detect"]
    )

    # Check for threshold-based alerting
    detect_threshold = any(
        word in intent_lower for word in ["exceed", "above", "over", "greater"]
    )

    # Check for activity-based alerting
    detect_activity = any(
        word in intent_lower for word in ["activity", "change", "busy"]
    )

    # Check for loss detection
    detect_loss = any(
        word in intent_lower for word in ["loss", "lost", "disappear", "gone"]
    )

    # Add conditions for specific frequencies
    for freq in alert_frequencies:
        conditions.append(
            AlertCondition(
                condition_type="new_signal",
                frequency_hz=freq,
                threshold_db=threshold_db,
            )
        )

    # Add generic new signal detection if requested but no specific freq
    if detect_new and not alert_frequencies:
        conditions.append(
            AlertCondition(
                condition_type="new_signal",
                threshold_db=threshold_db,
            )
        )

    # Add threshold breach condition
    if detect_threshold:
        conditions.append(
            AlertCondition(
                condition_type="threshold_breach",
                threshold_db=threshold_db,
            )
        )

    # Add activity change condition
    if detect_activity:
        conditions.append(
            AlertCondition(
                condition_type="band_activity",
                activity_change_percent=activity_percent or 50.0,
            )
        )

    # Add signal loss condition
    if detect_loss:
        conditions.append(
            AlertCondition(
                condition_type="signal_loss",
            )
        )

    # Default condition if none specified
    if not conditions:
        conditions.append(
            AlertCondition(
                condition_type="new_signal",
                threshold_db=threshold_db,
            )
        )

    # Generate name from bands and frequencies
    name_parts: list[str] = []
    if bands:
        name_parts.append("_".join(b.value for b in bands[:2]))
    if alert_frequencies:
        freq_str = "_".join(f"{f/1e6:.1f}MHz" for f in alert_frequencies[:2])
        name_parts.append(freq_str)
    name = "_".join(name_parts) or "spectrum_watch"

    return WatchConfig(
        name=name,
        description=intent,
        bands=bands or [FrequencyBand.FM_BROADCAST],  # default to FM
        custom_range=custom_range,
        alert_conditions=conditions,
        threshold_db=threshold_db,
    )


def create_watch_for_band(
    band: FrequencyBand,
    threshold_db: float = -30.0,
    detect_new: bool = True,
) -> WatchConfig:
    """Create a simple watch config for a predefined band.

    Args:
        band: The frequency band to monitor.
        threshold_db: Detection threshold in dB.
        detect_new: Whether to alert on new signals.

    Returns:
        WatchConfig for the specified band.
    """
    conditions = []
    if detect_new:
        conditions.append(
            AlertCondition(
                condition_type="new_signal",
                threshold_db=threshold_db,
            )
        )

    return WatchConfig(
        name=f"{band.value}_watch",
        bands=[band],
        alert_conditions=conditions,
        threshold_db=threshold_db,
    )


def create_watch_for_frequency(
    frequency_hz: float,
    tolerance_hz: float = 50000,
    threshold_db: float = -30.0,
) -> WatchConfig:
    """Create a watch config for a specific frequency.

    Args:
        frequency_hz: The frequency to monitor in Hz.
        tolerance_hz: Tolerance for frequency matching.
        threshold_db: Detection threshold in dB.

    Returns:
        WatchConfig for the specified frequency.
    """
    freq_mhz = frequency_hz / 1e6

    # Find notable name if available
    name = NOTABLE_FREQUENCIES.get(frequency_hz, f"{freq_mhz:.3f}MHz")

    # Determine band
    bands = []
    for band, (start, end) in BAND_RANGES.items():
        if start <= frequency_hz <= end:
            bands.append(band)
            break

    if not bands:
        bands = [FrequencyBand.CUSTOM]

    return WatchConfig(
        name=f"watch_{name.replace(' ', '_').lower()}",
        description=f"Monitor {freq_mhz:.3f} MHz ({name})",
        bands=bands,
        alert_conditions=[
            AlertCondition(
                condition_type="new_signal",
                frequency_hz=frequency_hz,
                frequency_tolerance_hz=tolerance_hz,
                threshold_db=threshold_db,
            )
        ],
        threshold_db=threshold_db,
    )
