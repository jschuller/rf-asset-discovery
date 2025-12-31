"""Tests for survey app modules (band_catalog, executor, manager)."""

from __future__ import annotations

import pytest

from sdr_toolkit.apps.survey.band_catalog import (
    PRIORITY_BANDS,
    RTL_SDR_MAX_HZ,
    RTL_SDR_MIN_HZ,
    estimate_survey_duration,
    format_duration,
    generate_full_survey_segments,
    generate_gap_segments,
    generate_priority_only_segments,
    get_priority_bands,
)
from sdr_toolkit.storage.survey_models import (
    BandDefinition,
    SegmentPriority,
    SurveySegment,
)


# ============================================================================
# Band Catalog Tests
# ============================================================================


class TestBandCatalogConstants:
    """Tests for band catalog constants."""

    def test_rtl_sdr_frequency_range(self) -> None:
        """RTL-SDR frequency limits should be correct."""
        assert RTL_SDR_MIN_HZ == 24e6  # 24 MHz
        assert RTL_SDR_MAX_HZ == 1766e6  # 1766 MHz

    def test_priority_bands_exist(self) -> None:
        """Priority bands dictionary should be populated."""
        assert len(PRIORITY_BANDS) > 0
        assert "fm_broadcast" in PRIORITY_BANDS
        assert "aircraft_vhf" in PRIORITY_BANDS
        assert "ism_433" in PRIORITY_BANDS

    def test_priority_bands_have_required_fields(self) -> None:
        """Each priority band should have required fields."""
        for name, band in PRIORITY_BANDS.items():
            assert isinstance(band, BandDefinition), f"{name} is not BandDefinition"
            assert band.name, f"{name} missing name"
            assert band.start_hz > 0, f"{name} invalid start_hz"
            assert band.end_hz > band.start_hz, f"{name} end_hz <= start_hz"
            assert band.step_hz > 0, f"{name} invalid step_hz"


class TestGetPriorityBands:
    """Tests for get_priority_bands function."""

    def test_returns_sorted_list(self) -> None:
        """get_priority_bands should return bands sorted by frequency."""
        bands = get_priority_bands()
        assert len(bands) > 0

        # Check sorted order
        for i in range(len(bands) - 1):
            assert bands[i].start_hz <= bands[i + 1].start_hz

    def test_returns_all_priority_bands(self) -> None:
        """get_priority_bands should return all defined bands."""
        bands = get_priority_bands()
        assert len(bands) == len(PRIORITY_BANDS)


class TestGenerateGapSegments:
    """Tests for generate_gap_segments function."""

    def test_generates_gaps_with_defaults(self) -> None:
        """Should generate gap segments using default parameters."""
        gaps = generate_gap_segments()
        assert len(gaps) > 0

        # All gaps should be COARSE priority
        for gap in gaps:
            assert gap.priority == SegmentPriority.COARSE

    def test_generates_gaps_in_custom_range(self) -> None:
        """Should generate gaps in custom frequency range."""
        # Simple range with no priority bands
        gaps = generate_gap_segments(
            start_hz=50e6,
            end_hz=70e6,
            coarse_step_hz=2e6,
            priority_bands=[],  # No priority bands
        )

        # Should create one gap covering the whole range
        assert len(gaps) == 1
        assert gaps[0].start_hz == 50e6
        assert gaps[0].end_hz == 70e6

    def test_gaps_around_priority_bands(self) -> None:
        """Should create gaps around priority bands."""
        # Create a simple priority band
        test_band = BandDefinition(
            name="Test Band",
            start_hz=100e6,
            end_hz=110e6,
            step_hz=1e6,
        )

        gaps = generate_gap_segments(
            start_hz=50e6,
            end_hz=150e6,
            coarse_step_hz=2e6,
            priority_bands=[test_band],
        )

        # Should have gap before and after the priority band
        assert len(gaps) == 2
        assert gaps[0].end_hz == 100e6  # Before band
        assert gaps[1].start_hz == 110e6  # After band

    def test_no_gaps_when_covered(self) -> None:
        """Should return no gaps when range is covered by priority bands."""
        # Priority band covers entire range
        covering_band = BandDefinition(
            name="Full Coverage",
            start_hz=50e6,
            end_hz=150e6,
            step_hz=1e6,
        )

        gaps = generate_gap_segments(
            start_hz=60e6,
            end_hz=140e6,
            priority_bands=[covering_band],
        )

        assert len(gaps) == 0


class TestGenerateFullSurveySegments:
    """Tests for generate_full_survey_segments function."""

    def test_generates_segments_with_survey_id(self) -> None:
        """Should generate segments linked to survey ID."""
        segments = generate_full_survey_segments(survey_id="test-survey-123")

        assert len(segments) > 0
        for segment in segments:
            assert segment.survey_id == "test-survey-123"

    def test_segments_sorted_by_priority_then_frequency(self) -> None:
        """Segments should be sorted by priority, then frequency."""
        segments = generate_full_survey_segments(survey_id="test")

        # Check priority ordering (FINE=1 before MEDIUM=2 before COARSE=3)
        prev_priority = 0
        prev_freq = 0.0
        for segment in segments:
            if segment.priority.value > prev_priority:
                prev_freq = 0.0  # Reset when priority changes
            assert segment.priority.value >= prev_priority
            if segment.priority.value == prev_priority:
                assert segment.start_freq_hz >= prev_freq
            prev_priority = segment.priority.value
            prev_freq = segment.start_freq_hz

    def test_clips_segments_to_range(self) -> None:
        """Segments should be clipped to survey range."""
        segments = generate_full_survey_segments(
            survey_id="test",
            start_hz=100e6,
            end_hz=200e6,
        )

        for segment in segments:
            assert segment.start_freq_hz >= 100e6
            assert segment.end_freq_hz <= 200e6

    def test_include_gaps_flag(self) -> None:
        """include_gaps=False should skip gap segments."""
        with_gaps = generate_full_survey_segments(
            survey_id="test",
            include_gaps=True,
        )
        without_gaps = generate_full_survey_segments(
            survey_id="test",
            include_gaps=False,
        )

        # More segments when gaps included
        assert len(with_gaps) > len(without_gaps)

        # Without gaps should only have FINE/MEDIUM priority
        for segment in without_gaps:
            assert segment.priority != SegmentPriority.COARSE


class TestGeneratePriorityOnlySegments:
    """Tests for generate_priority_only_segments function."""

    def test_generates_priority_only(self) -> None:
        """Should only generate segments for priority bands."""
        segments = generate_priority_only_segments(survey_id="test")

        # Should not have any COARSE (gap) segments
        for segment in segments:
            assert segment.priority != SegmentPriority.COARSE

    def test_matches_full_survey_without_gaps(self) -> None:
        """Should match generate_full_survey_segments with include_gaps=False."""
        priority_only = generate_priority_only_segments(survey_id="test")
        full_no_gaps = generate_full_survey_segments(
            survey_id="test",
            include_gaps=False,
        )

        assert len(priority_only) == len(full_no_gaps)


# ============================================================================
# Duration Estimation Tests
# ============================================================================


class TestEstimateSurveyDuration:
    """Tests for estimate_survey_duration function."""

    def test_estimates_duration_for_segments(self) -> None:
        """Should estimate total duration for segments."""
        segments = [
            SurveySegment(
                survey_id="test",
                start_freq_hz=100e6,
                end_freq_hz=110e6,
                step_hz=1e6,
            ),
            SurveySegment(
                survey_id="test",
                start_freq_hz=200e6,
                end_freq_hz=220e6,
                step_hz=1e6,
            ),
        ]

        duration = estimate_survey_duration(segments)

        # 11 steps + 21 steps = 32 steps * 0.15s = 4.8s
        assert duration == pytest.approx(4.8, rel=0.01)

    def test_empty_segments_zero_duration(self) -> None:
        """Empty segment list should have zero duration."""
        duration = estimate_survey_duration([])
        assert duration == 0.0


class TestFormatDuration:
    """Tests for format_duration function."""

    def test_format_seconds(self) -> None:
        """Should format seconds correctly."""
        assert format_duration(30) == "30s"
        assert format_duration(59) == "59s"

    def test_format_minutes(self) -> None:
        """Should format minutes correctly."""
        assert format_duration(60) == "1m 0s"
        assert format_duration(90) == "1m 30s"
        assert format_duration(330) == "5m 30s"

    def test_format_hours(self) -> None:
        """Should format hours correctly."""
        assert format_duration(3600) == "1h 0m"
        assert format_duration(4500) == "1h 15m"
        assert format_duration(7200) == "2h 0m"


# ============================================================================
# Integration Tests
# ============================================================================


class TestSurveySegmentGeneration:
    """Integration tests for survey segment generation."""

    def test_full_survey_coverage(self) -> None:
        """Full survey should cover RTL-SDR frequency range."""
        segments = generate_full_survey_segments(
            survey_id="coverage-test",
            include_gaps=True,
        )

        # Collect all covered frequencies
        covered_ranges: list[tuple[float, float]] = []
        for seg in segments:
            covered_ranges.append((seg.start_freq_hz, seg.end_freq_hz))

        # Sort by start frequency
        covered_ranges.sort()

        # Check coverage starts at RTL-SDR minimum
        assert covered_ranges[0][0] == RTL_SDR_MIN_HZ

        # Check coverage ends at RTL-SDR maximum (allowing for step size)
        assert covered_ranges[-1][1] >= RTL_SDR_MAX_HZ - 5e6  # Within 5 MHz

    def test_priority_bands_have_fine_step_sizes(self) -> None:
        """Priority bands should have appropriate step sizes for their purpose."""
        bands = get_priority_bands()

        for band in bands:
            if band.priority == SegmentPriority.FINE:
                # Fine bands should have step <= 1 MHz
                assert band.step_hz <= 1e6, f"{band.name} step too large"

    def test_known_bands_present(self) -> None:
        """Known important bands should be in the catalog."""
        band_names = {b.name for b in get_priority_bands()}

        expected_bands = [
            "FM Broadcast",
            "Aircraft VHF",
            "ISM 433 MHz",
            "ADS-B 1090",
        ]

        for expected in expected_bands:
            assert expected in band_names, f"Missing band: {expected}"
