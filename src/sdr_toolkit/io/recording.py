"""Signal recording utilities."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from scipy.io import wavfile

from sdr_toolkit.core.config import FM_AUDIO_RATE
from sdr_toolkit.io.sigmf import SigMFRecording

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)


@dataclass
class IQRecording:
    """Simple IQ recording with numpy format.

    For quick recordings without full SigMF metadata.
    Use SigMFRecording for production recordings.
    """

    samples: NDArray[np.complex64]
    sample_rate: float
    center_freq: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, object] = field(default_factory=dict)

    @classmethod
    def from_file(cls, path: Path | str) -> IQRecording:
        """Load recording from numpy file.

        Args:
            path: Path to .npy file or directory with recording.

        Returns:
            IQRecording instance.
        """
        path = Path(path)

        if path.is_dir():
            data_file = path / "samples.npy"
            meta_file = path / "metadata.npy"
        else:
            data_file = path
            meta_file = path.with_suffix(".meta.npy")

        samples = np.load(data_file)

        if meta_file.exists():
            meta = np.load(meta_file, allow_pickle=True).item()
            sample_rate = meta.get("sample_rate", 0.0)
            center_freq = meta.get("center_freq", 0.0)
            timestamp_str = meta.get("timestamp", "")
            if timestamp_str:
                timestamp = datetime.fromisoformat(timestamp_str)
            else:
                timestamp = datetime.now(timezone.utc)
            metadata = meta.get("metadata", {})
        else:
            sample_rate = 0.0
            center_freq = 0.0
            timestamp = datetime.now(timezone.utc)
            metadata = {}

        return cls(
            samples=samples,
            sample_rate=sample_rate,
            center_freq=center_freq,
            timestamp=timestamp,
            metadata=metadata,
        )

    def save(self, path: Path | str) -> None:
        """Save recording to numpy file.

        Args:
            path: Output path (.npy file or directory).
        """
        path = Path(path)

        if path.suffix == ".npy":
            data_file = path
            meta_file = path.with_suffix(".meta.npy")
        else:
            path.mkdir(parents=True, exist_ok=True)
            data_file = path / "samples.npy"
            meta_file = path / "metadata.npy"

        np.save(data_file, self.samples)

        meta = {
            "sample_rate": self.sample_rate,
            "center_freq": self.center_freq,
            "timestamp": self.timestamp.isoformat(),
            "num_samples": len(self.samples),
            "metadata": self.metadata,
        }
        np.save(meta_file, meta)

        logger.info("Saved recording to %s", data_file)

    def to_sigmf(
        self,
        output_dir: Path | str,
        basename: str | None = None,
        description: str = "",
    ) -> SigMFRecording:
        """Convert to SigMF format.

        Args:
            output_dir: Output directory.
            basename: Base filename.
            description: Recording description.

        Returns:
            SigMFRecording instance.
        """
        return SigMFRecording.create(
            samples=self.samples,
            sample_rate=self.sample_rate,
            center_freq=self.center_freq,
            output_dir=output_dir,
            basename=basename,
            description=description,
        )

    @property
    def duration_seconds(self) -> float:
        """Get recording duration in seconds."""
        if self.sample_rate <= 0:
            return 0.0
        return len(self.samples) / self.sample_rate


def save_audio_wav(
    audio: NDArray[np.float64],
    path: Path | str,
    sample_rate: int = FM_AUDIO_RATE,
    normalize: bool = True,
) -> None:
    """Save audio samples to WAV file.

    Args:
        audio: Audio samples (float64).
        path: Output WAV file path.
        sample_rate: Audio sample rate.
        normalize: Normalize audio level.
    """
    path = Path(path)

    if normalize:
        max_val = np.max(np.abs(audio))
        if max_val > 0:
            audio = audio / max_val * 0.95

    # Convert to int16 for WAV
    audio_int = (audio * 32767).astype(np.int16)

    wavfile.write(path, sample_rate, audio_int)
    logger.info("Saved audio to %s", path)


def save_audio_stereo_wav(
    left: NDArray[np.float64],
    right: NDArray[np.float64],
    path: Path | str,
    sample_rate: int = FM_AUDIO_RATE,
    normalize: bool = True,
) -> None:
    """Save stereo audio to WAV file.

    Args:
        left: Left channel samples.
        right: Right channel samples.
        path: Output WAV file path.
        sample_rate: Audio sample rate.
        normalize: Normalize audio level.
    """
    path = Path(path)

    # Ensure same length
    min_len = min(len(left), len(right))
    left = left[:min_len]
    right = right[:min_len]

    if normalize:
        max_val = max(np.max(np.abs(left)), np.max(np.abs(right)))
        if max_val > 0:
            left = left / max_val * 0.95
            right = right / max_val * 0.95

    # Interleave channels
    stereo = np.column_stack((left, right))
    stereo_int = (stereo * 32767).astype(np.int16)

    wavfile.write(path, sample_rate, stereo_int)
    logger.info("Saved stereo audio to %s", path)


def load_audio_wav(path: Path | str) -> tuple[NDArray[np.float64], int]:
    """Load audio from WAV file.

    Args:
        path: WAV file path.

    Returns:
        Tuple of (samples, sample_rate).
    """
    sample_rate, data = wavfile.read(path)

    # Convert to float64
    if data.dtype == np.int16:
        samples = data.astype(np.float64) / 32767.0
    elif data.dtype == np.int32:
        samples = data.astype(np.float64) / 2147483647.0
    else:
        samples = data.astype(np.float64)

    return samples, sample_rate


class StreamRecorder:
    """Record streaming samples to file."""

    def __init__(
        self,
        output_path: Path | str,
        sample_rate: float,
        center_freq: float,
        max_samples: int | None = None,
    ) -> None:
        """Initialize stream recorder.

        Args:
            output_path: Output file path.
            sample_rate: Sample rate in Hz.
            center_freq: Center frequency in Hz.
            max_samples: Maximum samples to record (None = unlimited).
        """
        self.output_path = Path(output_path)
        self.sample_rate = sample_rate
        self.center_freq = center_freq
        self.max_samples = max_samples

        self._samples: list[NDArray[np.complex64]] = []
        self._total_samples = 0
        self._start_time: datetime | None = None

    def write(self, samples: NDArray[np.complex64]) -> bool:
        """Write samples to buffer.

        Args:
            samples: Samples to record.

        Returns:
            True if more samples can be recorded, False if limit reached.
        """
        if self._start_time is None:
            self._start_time = datetime.now(timezone.utc)

        if self.max_samples is not None:
            remaining = self.max_samples - self._total_samples
            if remaining <= 0:
                return False
            if len(samples) > remaining:
                samples = samples[:remaining]

        self._samples.append(samples.copy())
        self._total_samples += len(samples)

        if self.max_samples is not None and self._total_samples >= self.max_samples:
            return False

        return True

    def save(self) -> SigMFRecording:
        """Save recorded samples to file.

        Returns:
            SigMFRecording of saved data.
        """
        all_samples = np.concatenate(self._samples)

        return SigMFRecording.create(
            samples=all_samples,
            sample_rate=self.sample_rate,
            center_freq=self.center_freq,
            output_dir=self.output_path.parent,
            basename=self.output_path.stem,
        )

    @property
    def duration_seconds(self) -> float:
        """Get current recording duration."""
        if self.sample_rate <= 0:
            return 0.0
        return self._total_samples / self.sample_rate

    @property
    def total_samples(self) -> int:
        """Get total samples recorded."""
        return self._total_samples
