"""Tests for survey models."""

from __future__ import annotations

from datetime import datetime

import pytest

from sdr_toolkit.storage.survey_models import (
    BandDefinition,
    SegmentPriority,
    SegmentStatus,
    SignalState,
    SpectrumSurvey,
    SurveyLocation,
    SurveySegment,
    SurveySignal,
    SurveyStatus,
)


# ============================================================================
# Enum Tests
# ============================================================================


class TestSurveyEnums:
    """Tests for survey enum values."""

    def test_survey_status_values(self) -> None:
        """SurveyStatus should have expected values."""
        assert SurveyStatus.PENDING.value == "pending"
        assert SurveyStatus.IN_PROGRESS.value == "in_progress"
        assert SurveyStatus.PAUSED.value == "paused"
        assert SurveyStatus.COMPLETED.value == "completed"
        assert SurveyStatus.FAILED.value == "failed"

    def test_segment_status_values(self) -> None:
        """SegmentStatus should have expected values."""
        assert SegmentStatus.PENDING.value == "pending"
        assert SegmentStatus.IN_PROGRESS.value == "in_progress"
        assert SegmentStatus.COMPLETED.value == "completed"
        assert SegmentStatus.FAILED.value == "failed"
        assert SegmentStatus.SKIPPED.value == "skipped"

    def test_segment_priority_values(self) -> None:
        """SegmentPriority should have correct numeric values."""
        assert SegmentPriority.FINE.value == 1
        assert SegmentPriority.MEDIUM.value == 2
        assert SegmentPriority.COARSE.value == 3

    def test_signal_state_values(self) -> None:
        """SignalState should have ServiceNow-style states."""
        assert SignalState.DISCOVERED.value == "discovered"
        assert SignalState.CONFIRMED.value == "confirmed"
        assert SignalState.DISMISSED.value == "dismissed"
        assert SignalState.PROMOTED.value == "promoted"


# ============================================================================
# SurveySegment Tests
# ============================================================================


class TestSurveySegment:
    """Tests for SurveySegment model."""

    def test_segment_creation_with_required_fields(self) -> None:
        """Segment should be created with required fields."""
        segment = SurveySegment(
            survey_id="survey-123",
            start_freq_hz=87.5e6,
            end_freq_hz=108e6,
            step_hz=100e3,
        )
        assert segment.segment_id is not None
        assert segment.survey_id == "survey-123"
        assert segment.start_freq_hz == 87.5e6
        assert segment.end_freq_hz == 108e6
        assert segment.status == SegmentStatus.PENDING

    def test_segment_defaults(self) -> None:
        """Segment should have sensible defaults."""
        segment = SurveySegment(
            survey_id="test",
            start_freq_hz=100e6,
            end_freq_hz=200e6,
            step_hz=1e6,
        )
        assert segment.priority == SegmentPriority.COARSE
        assert segment.dwell_time_ms == 100.0
        assert segment.signals_found == 0
        assert segment.scan_id is None

    def test_bandwidth_mhz_property(self) -> None:
        """bandwidth_mhz should return correct value."""
        segment = SurveySegment(
            survey_id="test",
            start_freq_hz=100e6,
            end_freq_hz=120e6,
            step_hz=1e6,
        )
        assert segment.bandwidth_mhz == 20.0

    def test_estimated_steps_property(self) -> None:
        """estimated_steps should calculate correctly."""
        segment = SurveySegment(
            survey_id="test",
            start_freq_hz=100e6,
            end_freq_hz=110e6,
            step_hz=1e6,
        )
        assert segment.estimated_steps == 11  # 10 MHz / 1 MHz + 1

    def test_estimated_duration_seconds(self) -> None:
        """estimated_duration_seconds should estimate scan time."""
        segment = SurveySegment(
            survey_id="test",
            start_freq_hz=100e6,
            end_freq_hz=110e6,
            step_hz=1e6,
        )
        # 11 steps * 0.15 seconds
        assert segment.estimated_duration_seconds == pytest.approx(1.65, rel=0.01)


# ============================================================================
# SurveySignal Tests
# ============================================================================


class TestSurveySignal:
    """Tests for SurveySignal model."""

    def test_signal_creation(self) -> None:
        """Signal should be created with required fields."""
        signal = SurveySignal(
            survey_id="survey-123",
            frequency_hz=101.9e6,
            power_db=-25.0,
        )
        assert signal.signal_id is not None
        assert signal.frequency_hz == 101.9e6
        assert signal.power_db == -25.0
        assert signal.state == SignalState.DISCOVERED

    def test_signal_defaults(self) -> None:
        """Signal should have sensible defaults."""
        signal = SurveySignal(
            survey_id="test",
            frequency_hz=100e6,
            power_db=-30.0,
        )
        assert signal.detection_count == 1
        assert signal.state == SignalState.DISCOVERED
        assert signal.promoted_asset_id is None
        assert signal.first_seen is not None
        assert signal.last_seen is not None

    def test_frequency_mhz_property(self) -> None:
        """frequency_mhz should convert Hz to MHz."""
        signal = SurveySignal(
            survey_id="test",
            frequency_hz=101.9e6,
            power_db=-25.0,
        )
        assert signal.frequency_mhz == 101.9

    def test_should_auto_promote_default(self) -> None:
        """Signal with 3+ detections should qualify for auto-promote."""
        signal = SurveySignal(
            survey_id="test",
            frequency_hz=100e6,
            power_db=-30.0,
        )
        # 1 detection - not enough
        assert signal.should_auto_promote() is False

        # Update to 3 detections
        signal.detection_count = 3
        assert signal.should_auto_promote() is True

    def test_should_auto_promote_custom_threshold(self) -> None:
        """should_auto_promote should respect custom threshold."""
        signal = SurveySignal(
            survey_id="test",
            frequency_hz=100e6,
            power_db=-30.0,
        )
        signal.detection_count = 5
        assert signal.should_auto_promote(min_detections=5) is True
        assert signal.should_auto_promote(min_detections=6) is False

    def test_should_auto_promote_wrong_state(self) -> None:
        """Non-discovered signals should not auto-promote."""
        signal = SurveySignal(
            survey_id="test",
            frequency_hz=100e6,
            power_db=-30.0,
        )
        signal.detection_count = 10
        signal.state = SignalState.CONFIRMED
        assert signal.should_auto_promote() is False

    def test_update_detection(self) -> None:
        """update_detection should increment count and update timestamp."""
        signal = SurveySignal(
            survey_id="test",
            frequency_hz=100e6,
            power_db=-30.0,
        )
        old_last_seen = signal.last_seen

        signal.update_detection(power_db=-25.0)

        assert signal.detection_count == 2
        assert signal.last_seen >= old_last_seen
        assert signal.power_db == -25.0  # Updated to stronger

    def test_update_detection_weaker_power(self) -> None:
        """update_detection should not update power if weaker."""
        signal = SurveySignal(
            survey_id="test",
            frequency_hz=100e6,
            power_db=-25.0,
        )
        signal.update_detection(power_db=-35.0)  # Weaker signal
        assert signal.power_db == -25.0  # Kept original


# ============================================================================
# SpectrumSurvey Tests
# ============================================================================


class TestSpectrumSurvey:
    """Tests for SpectrumSurvey model."""

    def test_survey_creation(self) -> None:
        """Survey should be created with required name."""
        survey = SpectrumSurvey(name="Full Spectrum Scan")
        assert survey.survey_id is not None
        assert survey.name == "Full Spectrum Scan"
        assert survey.status == SurveyStatus.PENDING

    def test_survey_defaults(self) -> None:
        """Survey should have sensible defaults."""
        survey = SpectrumSurvey(name="Test")
        assert survey.start_freq_hz == 24e6
        assert survey.end_freq_hz == 1766e6
        assert survey.total_segments == 0
        assert survey.completed_segments == 0
        assert survey.completion_pct == 0.0
        assert survey.created_at is not None

    def test_coverage_mhz_property(self) -> None:
        """coverage_mhz should calculate total coverage."""
        survey = SpectrumSurvey(
            name="Test",
            start_freq_hz=100e6,
            end_freq_hz=200e6,
        )
        assert survey.coverage_mhz == 100.0

    def test_update_progress(self) -> None:
        """update_progress should update counters."""
        survey = SpectrumSurvey(name="Test")
        survey.total_segments = 10

        survey.update_progress(completed=5, signals=25)

        assert survey.completed_segments == 5
        assert survey.total_signals_found == 25
        assert survey.completion_pct == 50.0
        assert survey.last_activity_at is not None

    def test_is_complete_false(self) -> None:
        """is_complete should return False when not done."""
        survey = SpectrumSurvey(name="Test")
        survey.total_segments = 10
        survey.completed_segments = 5
        assert survey.is_complete() is False

    def test_is_complete_true(self) -> None:
        """is_complete should return True when all done."""
        survey = SpectrumSurvey(name="Test")
        survey.total_segments = 10
        survey.completed_segments = 10
        assert survey.is_complete() is True

    def test_location_context_fields(self) -> None:
        """Survey should support location context."""
        survey = SpectrumSurvey(
            name="NYC Office Survey",
            location_name="NYC Office",
            location_gps_lat=40.7128,
            location_gps_lon=-74.0060,
            environment="indoor",
            antenna_type="discone",
            run_number=3,
        )
        assert survey.location_name == "NYC Office"
        assert survey.location_gps_lat == 40.7128
        assert survey.run_number == 3


# ============================================================================
# BandDefinition Tests
# ============================================================================


class TestBandDefinition:
    """Tests for BandDefinition model."""

    def test_band_creation(self) -> None:
        """Band should be created with required fields."""
        band = BandDefinition(
            name="FM Broadcast",
            start_hz=87.5e6,
            end_hz=108e6,
            step_hz=100e3,
        )
        assert band.name == "FM Broadcast"
        assert band.start_hz == 87.5e6
        assert band.end_hz == 108e6

    def test_bandwidth_mhz_property(self) -> None:
        """bandwidth_mhz should calculate correctly."""
        band = BandDefinition(
            name="Test",
            start_hz=100e6,
            end_hz=120e6,
            step_hz=1e6,
        )
        assert band.bandwidth_mhz == 20.0

    def test_to_segment(self) -> None:
        """to_segment should convert band to survey segment."""
        band = BandDefinition(
            name="FM Broadcast",
            start_hz=87.5e6,
            end_hz=108e6,
            step_hz=100e3,
            priority=SegmentPriority.FINE,
        )

        segment = band.to_segment(survey_id="survey-123")

        assert segment.survey_id == "survey-123"
        assert segment.name == "FM Broadcast"
        assert segment.start_freq_hz == 87.5e6
        assert segment.end_freq_hz == 108e6
        assert segment.step_hz == 100e3
        assert segment.priority == SegmentPriority.FINE


# ============================================================================
# SurveyLocation Tests
# ============================================================================


class TestSurveyLocation:
    """Tests for SurveyLocation model."""

    def test_location_creation(self) -> None:
        """Location should be created with required name."""
        location = SurveyLocation(name="NYC Office")
        assert location.location_id is not None
        assert location.name == "NYC Office"
        assert location.created_at is not None

    def test_location_with_gps(self) -> None:
        """Location should support GPS coordinates."""
        location = SurveyLocation(
            name="Rooftop",
            gps_lat=40.7128,
            gps_lon=-74.0060,
            environment="rooftop",
        )
        assert location.gps_lat == 40.7128
        assert location.gps_lon == -74.0060
        assert location.environment == "rooftop"

    def test_location_defaults(self) -> None:
        """Location should have sensible defaults."""
        location = SurveyLocation(name="Test")
        assert location.total_surveys == 0
        assert location.last_survey_at is None
        assert location.default_antenna is None
