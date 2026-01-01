"""Tests for SigMF format support."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest

from rf_asset_discovery.io.sigmf import SigMFAnnotation, SigMFCapture, SigMFRecording


class TestSigMFRecording:
    """Tests for SigMFRecording class."""

    def test_create_recording(self) -> None:
        """Test creating a SigMF recording."""
        with tempfile.TemporaryDirectory() as tmpdir:
            samples = np.random.randn(1024).astype(np.complex64)

            recording = SigMFRecording.create(
                samples=samples,
                sample_rate=1.024e6,
                center_freq=100e6,
                output_dir=tmpdir,
                description="Test recording",
            )

            assert recording.data_path.exists()
            assert recording.meta_path.exists()
            assert recording.sample_rate == 1.024e6

    def test_load_recording(self) -> None:
        """Test loading a SigMF recording."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create recording
            samples = np.exp(1j * np.linspace(0, 100, 1024)).astype(np.complex64)

            original = SigMFRecording.create(
                samples=samples,
                sample_rate=2.048e6,
                center_freq=433e6,
                output_dir=tmpdir,
            )

            # Load it back
            loaded = SigMFRecording.load(original.meta_path)

            assert loaded.sample_rate == 2.048e6
            assert loaded.center_frequency == 433e6

    def test_to_numpy(self) -> None:
        """Test loading samples as numpy array."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_samples = np.random.randn(512).astype(np.complex64) + 1j * np.random.randn(512).astype(np.float32)
            original_samples = original_samples.astype(np.complex64)

            recording = SigMFRecording.create(
                samples=original_samples,
                sample_rate=1e6,
                center_freq=100e6,
                output_dir=tmpdir,
            )

            loaded_samples = recording.to_numpy()

            assert len(loaded_samples) == len(original_samples)
            np.testing.assert_array_almost_equal(
                loaded_samples, original_samples, decimal=5
            )

    def test_metadata_structure(self) -> None:
        """Test metadata file structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            samples = np.zeros(100, dtype=np.complex64)

            recording = SigMFRecording.create(
                samples=samples,
                sample_rate=1e6,
                center_freq=100e6,
                output_dir=tmpdir,
                description="Metadata test",
            )

            with open(recording.meta_path) as f:
                metadata = json.load(f)

            assert "global" in metadata
            assert "captures" in metadata
            assert "annotations" in metadata
            assert metadata["global"]["core:datatype"] == "cf32_le"
            assert metadata["global"]["core:sample_rate"] == 1e6

    def test_add_annotation(self) -> None:
        """Test adding annotations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            samples = np.zeros(1000, dtype=np.complex64)

            recording = SigMFRecording.create(
                samples=samples,
                sample_rate=1e6,
                center_freq=100e6,
                output_dir=tmpdir,
            )

            recording.add_annotation(
                sample_start=100,
                sample_count=500,
                label="FM Broadcast",
                freq_lower=99.5e6,
                freq_upper=100.5e6,
            )
            recording.save_metadata()

            # Reload and verify
            loaded = SigMFRecording.load(recording.meta_path)
            assert len(loaded.annotations) == 1
            assert loaded.annotations[0].label == "FM Broadcast"

    def test_duration_seconds(self) -> None:
        """Test duration calculation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sample_rate = 1e6
            duration = 2.0
            num_samples = int(sample_rate * duration)
            samples = np.zeros(num_samples, dtype=np.complex64)

            recording = SigMFRecording.create(
                samples=samples,
                sample_rate=sample_rate,
                center_freq=100e6,
                output_dir=tmpdir,
            )

            assert recording.duration_seconds == pytest.approx(duration, rel=0.01)


class TestSigMFCapture:
    """Tests for SigMFCapture dataclass."""

    def test_capture_creation(self) -> None:
        """Test capture creation."""
        capture = SigMFCapture(
            sample_start=0,
            frequency=100e6,
            datetime="2024-01-01T00:00:00Z",
        )

        assert capture.sample_start == 0
        assert capture.frequency == 100e6


class TestSigMFAnnotation:
    """Tests for SigMFAnnotation dataclass."""

    def test_annotation_creation(self) -> None:
        """Test annotation creation."""
        annotation = SigMFAnnotation(
            sample_start=1000,
            sample_count=5000,
            label="Signal",
            comment="Test signal",
        )

        assert annotation.sample_start == 1000
        assert annotation.sample_count == 5000
        assert annotation.label == "Signal"
