"""Frequency band catalog for spectrum surveys.

Defines priority bands with optimal scan parameters and
provides gap-filling segment generation for comprehensive
coverage across the RTL-SDR frequency range.

RTL-SDR (R820T tuner) coverage: ~24 MHz to ~1766 MHz
"""

from __future__ import annotations

from sdr_toolkit.storage.survey_models import (
    BandDefinition,
    SegmentPriority,
    SurveySegment,
)

# ============================================================================
# RTL-SDR Frequency Limits
# ============================================================================

RTL_SDR_MIN_HZ = 24e6  # 24 MHz minimum
RTL_SDR_MAX_HZ = 1766e6  # 1766 MHz maximum

# ============================================================================
# Priority Bands - Known Active Frequencies
# ============================================================================

PRIORITY_BANDS: dict[str, BandDefinition] = {
    # Broadcast
    "fm_broadcast": BandDefinition(
        name="FM Broadcast",
        start_hz=87.5e6,
        end_hz=108e6,
        step_hz=200e3,  # 200 kHz for FM stations
        priority=SegmentPriority.FINE,
        description="Commercial FM radio stations",
        modulation="wfm",
    ),
    # Aviation
    "aircraft_vhf": BandDefinition(
        name="Aircraft VHF",
        start_hz=118e6,
        end_hz=137e6,
        step_hz=25e3,  # 25 kHz channel spacing
        priority=SegmentPriority.FINE,
        description="Aviation communications (AM)",
        modulation="am",
    ),
    # Amateur Radio
    "amateur_2m": BandDefinition(
        name="Amateur 2m",
        start_hz=144e6,
        end_hz=148e6,
        step_hz=12.5e3,  # 12.5 kHz for repeaters
        priority=SegmentPriority.FINE,
        description="Ham radio VHF band",
        modulation="nfm",
    ),
    # Marine
    "marine_vhf": BandDefinition(
        name="Marine VHF",
        start_hz=156e6,
        end_hz=162.025e6,
        step_hz=25e3,  # 25 kHz channels
        priority=SegmentPriority.FINE,
        description="Marine radio communications",
        modulation="nfm",
    ),
    # Weather
    "noaa_weather": BandDefinition(
        name="NOAA Weather",
        start_hz=162.4e6,
        end_hz=162.55e6,
        step_hz=25e3,
        priority=SegmentPriority.FINE,
        description="NOAA Weather Radio",
        modulation="nfm",
    ),
    # ISM Bands (IoT/Consumer)
    "ism_315": BandDefinition(
        name="ISM 315 MHz",
        start_hz=314e6,
        end_hz=316e6,
        step_hz=25e3,
        priority=SegmentPriority.FINE,
        description="TPMS, garage doors, remotes (US)",
        modulation="digital",
    ),
    # Amateur 70cm
    "amateur_70cm": BandDefinition(
        name="Amateur 70cm",
        start_hz=420e6,
        end_hz=450e6,
        step_hz=25e3,
        priority=SegmentPriority.FINE,
        description="Ham radio UHF band",
        modulation="nfm",
    ),
    # ISM 433 MHz
    "ism_433": BandDefinition(
        name="ISM 433 MHz",
        start_hz=433e6,
        end_hz=434.79e6,
        step_hz=25e3,
        priority=SegmentPriority.FINE,
        description="Weather stations, IoT devices, remotes",
        modulation="digital",
    ),
    # FRS/GMRS
    "frs_gmrs": BandDefinition(
        name="FRS/GMRS",
        start_hz=462e6,
        end_hz=467.7125e6,
        step_hz=12.5e3,  # 12.5 kHz channel spacing
        priority=SegmentPriority.FINE,
        description="Family Radio Service",
        modulation="nfm",
    ),
    # Cellular - observation only
    "cellular_700": BandDefinition(
        name="Cellular 700 MHz",
        start_hz=698e6,
        end_hz=806e6,
        step_hz=1e6,  # Coarse - just presence detection
        priority=SegmentPriority.MEDIUM,
        description="LTE Band 12/13/17",
        modulation="digital",
    ),
    # ISM 868 MHz (EU)
    "ism_868": BandDefinition(
        name="ISM 868 MHz",
        start_hz=863e6,
        end_hz=870e6,
        step_hz=100e3,
        priority=SegmentPriority.FINE,
        description="LoRa, SigFox (EU)",
        modulation="digital",
    ),
    # ISM 915 MHz (US)
    "ism_915": BandDefinition(
        name="ISM 915 MHz",
        start_hz=902e6,
        end_hz=928e6,
        step_hz=100e3,
        priority=SegmentPriority.FINE,
        description="LoRa, smart meters (US)",
        modulation="digital",
    ),
    # GSM 900
    "gsm_900": BandDefinition(
        name="GSM 900",
        start_hz=935e6,
        end_hz=960e6,
        step_hz=200e3,  # 200 kHz GSM channels
        priority=SegmentPriority.MEDIUM,
        description="GSM downlink",
        modulation="digital",
    ),
    # ADS-B
    "adsb_1090": BandDefinition(
        name="ADS-B 1090",
        start_hz=1088e6,
        end_hz=1092e6,
        step_hz=1e6,  # Single frequency band
        priority=SegmentPriority.FINE,
        description="Aircraft transponders",
        modulation="digital",
    ),
    # GPS L1
    "gps_l1": BandDefinition(
        name="GPS L1",
        start_hz=1574e6,
        end_hz=1578e6,
        step_hz=1e6,
        priority=SegmentPriority.MEDIUM,
        description="GPS L1 frequency",
        modulation="digital",
    ),
}


def get_priority_bands() -> list[BandDefinition]:
    """Return all priority bands sorted by frequency.

    Returns:
        List of BandDefinition objects.
    """
    return sorted(PRIORITY_BANDS.values(), key=lambda b: b.start_hz)


def generate_gap_segments(
    start_hz: float = RTL_SDR_MIN_HZ,
    end_hz: float = RTL_SDR_MAX_HZ,
    coarse_step_hz: float = 2e6,
    priority_bands: list[BandDefinition] | None = None,
) -> list[BandDefinition]:
    """Generate coarse-sweep segments for gaps between priority bands.

    Creates segments to cover frequency ranges not covered by priority
    bands, ensuring comprehensive spectrum coverage.

    Args:
        start_hz: Survey start frequency (default: RTL-SDR minimum).
        end_hz: Survey end frequency (default: RTL-SDR maximum).
        coarse_step_hz: Step size for gap segments (default: 2 MHz).
        priority_bands: Priority bands to work around (default: all).

    Returns:
        List of BandDefinition objects for gap coverage.
    """
    if priority_bands is None:
        priority_bands = get_priority_bands()

    # Sort bands by start frequency
    sorted_bands = sorted(priority_bands, key=lambda b: b.start_hz)

    gaps: list[BandDefinition] = []
    current_pos = start_hz

    for band in sorted_bands:
        # Skip bands outside our range
        if band.end_hz < start_hz:
            continue
        if band.start_hz > end_hz:
            break

        # Check for gap before this band
        gap_start = current_pos
        gap_end = min(band.start_hz, end_hz)

        if gap_end > gap_start + coarse_step_hz:
            # Significant gap - create coarse segment
            gaps.append(
                BandDefinition(
                    name=f"Gap {gap_start/1e6:.0f}-{gap_end/1e6:.0f} MHz",
                    start_hz=gap_start,
                    end_hz=gap_end,
                    step_hz=coarse_step_hz,
                    priority=SegmentPriority.COARSE,
                    description="Gap-filling sweep",
                )
            )

        # Move past this band
        current_pos = max(current_pos, band.end_hz)

    # Check for gap after last band
    if current_pos < end_hz - coarse_step_hz:
        gaps.append(
            BandDefinition(
                name=f"Gap {current_pos/1e6:.0f}-{end_hz/1e6:.0f} MHz",
                start_hz=current_pos,
                end_hz=end_hz,
                step_hz=coarse_step_hz,
                priority=SegmentPriority.COARSE,
                description="Gap-filling sweep",
            )
        )

    return gaps


def generate_full_survey_segments(
    survey_id: str,
    start_hz: float = RTL_SDR_MIN_HZ,
    end_hz: float = RTL_SDR_MAX_HZ,
    include_gaps: bool = True,
    coarse_step_hz: float = 2e6,
) -> list[SurveySegment]:
    """Generate all segments for a comprehensive survey.

    Creates segments for priority bands and (optionally) gap-filling
    sweeps to ensure no frequency is missed.

    Args:
        survey_id: Parent survey ID.
        start_hz: Survey start frequency.
        end_hz: Survey end frequency.
        include_gaps: Whether to include gap-filling segments.
        coarse_step_hz: Step size for gap segments.

    Returns:
        List of SurveySegment objects ordered by priority then frequency.
    """
    segments: list[SurveySegment] = []

    # Add priority bands within range
    for band in get_priority_bands():
        if band.end_hz < start_hz:
            continue
        if band.start_hz > end_hz:
            continue

        # Clip band to survey range
        clipped_start = max(band.start_hz, start_hz)
        clipped_end = min(band.end_hz, end_hz)

        segment = SurveySegment(
            survey_id=survey_id,
            name=band.name,
            start_freq_hz=clipped_start,
            end_freq_hz=clipped_end,
            priority=band.priority,
            step_hz=band.step_hz,
        )
        segments.append(segment)

    # Add gap-filling segments
    if include_gaps:
        gaps = generate_gap_segments(
            start_hz=start_hz,
            end_hz=end_hz,
            coarse_step_hz=coarse_step_hz,
        )
        for gap in gaps:
            segment = gap.to_segment(survey_id)
            segments.append(segment)

    # Sort by priority (lower = higher priority) then frequency
    segments.sort(key=lambda s: (s.priority.value, s.start_freq_hz))

    return segments


def generate_priority_only_segments(survey_id: str) -> list[SurveySegment]:
    """Generate segments for priority bands only (no gap filling).

    Faster survey covering only known active frequency ranges.

    Args:
        survey_id: Parent survey ID.

    Returns:
        List of SurveySegment objects for priority bands.
    """
    return generate_full_survey_segments(
        survey_id=survey_id,
        include_gaps=False,
    )


def estimate_survey_duration(segments: list[SurveySegment]) -> float:
    """Estimate total survey duration in seconds.

    Based on empirical timing of ~150ms per frequency step.

    Args:
        segments: List of survey segments.

    Returns:
        Estimated duration in seconds.
    """
    total_seconds = 0.0
    for segment in segments:
        total_seconds += segment.estimated_duration_seconds
    return total_seconds


def format_duration(seconds: float) -> str:
    """Format duration in human-readable form.

    Args:
        seconds: Duration in seconds.

    Returns:
        Formatted string (e.g., "5m 30s" or "1h 15m").
    """
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"
