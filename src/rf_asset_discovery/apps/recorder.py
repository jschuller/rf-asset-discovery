"""Signal recorder application."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from rf_asset_discovery.core.config import get_platform_config
from rf_asset_discovery.core.device import SDRDevice
from rf_asset_discovery.dsp.demodulation import compute_signal_strength, fm_demodulate
from rf_asset_discovery.io.recording import StreamRecorder, save_audio_wav
from rf_asset_discovery.io.sigmf import SigMFRecording

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)


@dataclass
class RecordingResult:
    """Result of a signal recording."""

    path: Path
    duration_seconds: float
    num_samples: int
    sample_rate: float
    center_freq: float
    format: str

    def __repr__(self) -> str:
        return (
            f"Recording({self.path.name}, "
            f"{self.duration_seconds:.1f}s, "
            f"{self.center_freq/1e6:.3f}MHz)"
        )


@dataclass
class SignalRecorder:
    """Signal recorder for capturing IQ samples.

    Example:
        >>> recorder = SignalRecorder(center_freq_mhz=100.1)
        >>> result = recorder.record_iq(duration=10, output_dir="./recordings")
    """

    center_freq_mhz: float = 100.0
    sample_rate: float = field(default_factory=lambda: get_platform_config().sample_rate)
    gain: float | str = "auto"
    device_index: int = 0

    def record_iq(
        self,
        duration: float,
        output_dir: Path | str,
        basename: str | None = None,
        description: str = "",
    ) -> RecordingResult:
        """Record IQ samples to SigMF file.

        Args:
            duration: Recording duration in seconds.
            output_dir: Output directory.
            basename: Base filename (auto-generated if None).
            description: Recording description.

        Returns:
            RecordingResult with file info.
        """
        output_dir = Path(output_dir)
        center_freq = self.center_freq_mhz * 1e6
        total_samples = int(self.sample_rate * duration)
        block_size = int(self.sample_rate * 0.1)

        logger.info(
            "Recording %.1f seconds at %.3f MHz...",
            duration,
            self.center_freq_mhz,
        )

        samples_list: list[NDArray[np.complex64]] = []
        start_time = time.time()

        with SDRDevice(
            sample_rate=self.sample_rate,
            center_freq=center_freq,
            gain=self.gain,
            device_index=self.device_index,
        ) as device:
            samples_recorded = 0

            while samples_recorded < total_samples:
                remaining = total_samples - samples_recorded
                read_size = min(block_size, remaining)

                samples = device.read_samples(read_size)
                samples_list.append(samples)
                samples_recorded += len(samples)

                # Progress logging
                progress = samples_recorded / total_samples * 100
                if int(progress) % 20 == 0:
                    logger.debug("Recording progress: %.0f%%", progress)

        actual_duration = time.time() - start_time
        all_samples = np.concatenate(samples_list)

        # Save as SigMF
        recording = SigMFRecording.create(
            samples=all_samples,
            sample_rate=self.sample_rate,
            center_freq=center_freq,
            output_dir=output_dir,
            basename=basename,
            description=description,
        )

        logger.info(
            "Saved recording to %s (%.1f seconds)",
            recording.data_path,
            actual_duration,
        )

        return RecordingResult(
            path=recording.data_path,
            duration_seconds=actual_duration,
            num_samples=len(all_samples),
            sample_rate=self.sample_rate,
            center_freq=center_freq,
            format="sigmf",
        )

    def record_fm_audio(
        self,
        duration: float,
        output_path: Path | str,
        audio_rate: int = 48000,
    ) -> RecordingResult:
        """Record demodulated FM audio to WAV file.

        Args:
            duration: Recording duration in seconds.
            output_path: Output WAV file path.
            audio_rate: Audio sample rate.

        Returns:
            RecordingResult with file info.
        """
        output_path = Path(output_path)
        center_freq = self.center_freq_mhz * 1e6
        block_size = int(self.sample_rate * 0.1)

        logger.info(
            "Recording FM audio for %.1f seconds at %.1f MHz...",
            duration,
            self.center_freq_mhz,
        )

        audio_list: list[NDArray[np.float64]] = []
        start_time = time.time()

        with SDRDevice(
            sample_rate=self.sample_rate,
            center_freq=center_freq,
            gain=self.gain,
            device_index=self.device_index,
        ) as device:
            while time.time() - start_time < duration:
                samples = device.read_samples(block_size)
                audio, _ = fm_demodulate(samples, self.sample_rate, audio_rate)
                audio_list.append(audio)

        actual_duration = time.time() - start_time
        all_audio = np.concatenate(audio_list)

        # Save as WAV
        save_audio_wav(all_audio, output_path, sample_rate=audio_rate)

        logger.info("Saved FM audio to %s", output_path)

        return RecordingResult(
            path=output_path,
            duration_seconds=actual_duration,
            num_samples=len(all_audio),
            sample_rate=audio_rate,
            center_freq=center_freq,
            format="wav",
        )

    def stream_record(
        self,
        output_path: Path | str,
        max_duration: float | None = None,
        max_samples: int | None = None,
        trigger_threshold_db: float | None = None,
    ) -> RecordingResult:
        """Stream-record with optional triggering.

        Records continuously until stopped or limits reached.
        With trigger_threshold_db, only records when signal exceeds threshold.

        Args:
            output_path: Output file path.
            max_duration: Maximum duration in seconds.
            max_samples: Maximum number of samples.
            trigger_threshold_db: Signal threshold for triggered recording.

        Returns:
            RecordingResult with file info.
        """
        output_path = Path(output_path)
        center_freq = self.center_freq_mhz * 1e6
        block_size = int(self.sample_rate * 0.1)

        if max_duration is not None:
            max_samples = int(self.sample_rate * max_duration)

        recorder = StreamRecorder(
            output_path=output_path,
            sample_rate=self.sample_rate,
            center_freq=center_freq,
            max_samples=max_samples,
        )

        logger.info("Starting stream recording at %.3f MHz...", self.center_freq_mhz)

        with SDRDevice(
            sample_rate=self.sample_rate,
            center_freq=center_freq,
            gain=self.gain,
            device_index=self.device_index,
        ) as device:
            try:
                while True:
                    samples = device.read_samples(block_size)

                    # Check trigger if enabled
                    if trigger_threshold_db is not None:
                        strength = compute_signal_strength(samples)
                        if strength < trigger_threshold_db:
                            continue

                    # Write samples
                    if not recorder.write(samples):
                        break

            except KeyboardInterrupt:
                logger.info("Recording stopped by user")

        # Save recording
        sigmf_recording = recorder.save()

        return RecordingResult(
            path=sigmf_recording.data_path,
            duration_seconds=recorder.duration_seconds,
            num_samples=recorder.total_samples,
            sample_rate=self.sample_rate,
            center_freq=center_freq,
            format="sigmf",
        )


def record_signal(
    freq_mhz: float,
    duration: float,
    output_dir: str = ".",
) -> RecordingResult:
    """Record signal at specified frequency.

    Convenience function for quick recording.

    Args:
        freq_mhz: Center frequency in MHz.
        duration: Duration in seconds.
        output_dir: Output directory.

    Returns:
        RecordingResult with file info.
    """
    recorder = SignalRecorder(center_freq_mhz=freq_mhz)
    return recorder.record_iq(duration=duration, output_dir=output_dir)
