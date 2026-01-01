"""SigMF format support for signal recordings."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import numpy as np

from rf_asset_discovery.core.exceptions import SigMFError

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)

# SigMF data types
SigMFDataType = Literal[
    "cf64_le",  # Complex float64, little-endian
    "cf32_le",  # Complex float32, little-endian
    "ci32_le",  # Complex int32, little-endian
    "ci16_le",  # Complex int16, little-endian
    "ci8",  # Complex int8
    "rf64_le",  # Real float64, little-endian
    "rf32_le",  # Real float32, little-endian
    "ri32_le",  # Real int32, little-endian
    "ri16_le",  # Real int16, little-endian
    "ri8",  # Real int8
]


DTYPE_MAP: dict[SigMFDataType, type[np.generic]] = {
    "cf64_le": np.complex128,
    "cf32_le": np.complex64,
    "ci32_le": np.int32,
    "ci16_le": np.int16,
    "ci8": np.int8,
    "rf64_le": np.float64,
    "rf32_le": np.float32,
    "ri32_le": np.int32,
    "ri16_le": np.int16,
    "ri8": np.int8,
}


@dataclass
class SigMFCapture:
    """SigMF capture segment."""

    sample_start: int = 0
    frequency: float | None = None
    datetime: str | None = None
    global_index: int | None = None
    header_bytes: int | None = None


@dataclass
class SigMFAnnotation:
    """SigMF annotation."""

    sample_start: int
    sample_count: int
    frequency_lower_edge: float | None = None
    frequency_upper_edge: float | None = None
    label: str | None = None
    comment: str | None = None
    generator: str | None = None


@dataclass
class SigMFRecording:
    """SigMF recording with metadata.

    Implements the SigMF 1.0 specification for RF signal recordings.
    """

    data_path: Path
    meta_path: Path

    # Global metadata
    datatype: SigMFDataType = "cf32_le"
    sample_rate: float = 0.0
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    recorder: str = "rf-asset-discovery"
    license: str = ""
    hw: str = ""

    # Captures and annotations
    captures: list[SigMFCapture] = field(default_factory=list)
    annotations: list[SigMFAnnotation] = field(default_factory=list)

    # Extensions
    extensions: dict[str, object] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        samples: NDArray[np.complex64],
        sample_rate: float,
        center_freq: float,
        output_dir: Path | str,
        basename: str | None = None,
        description: str = "",
        datatype: SigMFDataType = "cf32_le",
    ) -> SigMFRecording:
        """Create a new SigMF recording.

        Args:
            samples: Complex IQ samples to save.
            sample_rate: Sample rate in Hz.
            center_freq: Center frequency in Hz.
            output_dir: Directory to save files.
            basename: Base filename (without extension).
            description: Recording description.
            datatype: SigMF data type.

        Returns:
            SigMFRecording instance.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if basename is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            basename = f"recording_{timestamp}"

        data_path = output_dir / f"{basename}.sigmf-data"
        meta_path = output_dir / f"{basename}.sigmf-meta"

        # Convert samples to correct dtype
        target_dtype = DTYPE_MAP[datatype]
        if samples.dtype != target_dtype:
            samples = samples.astype(target_dtype)

        # Save data file
        samples.tofile(data_path)
        logger.info("Saved %d samples to %s", len(samples), data_path)

        # Create recording
        recording = cls(
            data_path=data_path,
            meta_path=meta_path,
            datatype=datatype,
            sample_rate=sample_rate,
            description=description,
        )

        # Add capture
        capture = SigMFCapture(
            sample_start=0,
            frequency=center_freq,
            datetime=datetime.now(timezone.utc).isoformat(),
        )
        recording.captures.append(capture)

        # Save metadata
        recording.save_metadata()

        return recording

    @classmethod
    def load(cls, path: Path | str) -> SigMFRecording:
        """Load a SigMF recording.

        Args:
            path: Path to .sigmf-meta or .sigmf-data file.

        Returns:
            SigMFRecording instance.
        """
        path = Path(path)

        if path.suffix == ".sigmf-data":
            meta_path = path.with_suffix(".sigmf-meta")
            data_path = path
        elif path.suffix == ".sigmf-meta":
            meta_path = path
            data_path = path.with_suffix(".sigmf-data")
        else:
            raise SigMFError(f"Invalid file extension: {path.suffix}")

        if not meta_path.exists():
            raise SigMFError(f"Metadata file not found: {meta_path}")
        if not data_path.exists():
            raise SigMFError(f"Data file not found: {data_path}")

        with open(meta_path) as f:
            metadata = json.load(f)

        global_meta = metadata.get("global", {})
        captures_meta = metadata.get("captures", [])
        annotations_meta = metadata.get("annotations", [])

        recording = cls(
            data_path=data_path,
            meta_path=meta_path,
            datatype=global_meta.get("core:datatype", "cf32_le"),
            sample_rate=global_meta.get("core:sample_rate", 0.0),
            version=global_meta.get("core:version", "1.0.0"),
            description=global_meta.get("core:description", ""),
            author=global_meta.get("core:author", ""),
            recorder=global_meta.get("core:recorder", ""),
            license=global_meta.get("core:license", ""),
            hw=global_meta.get("core:hw", ""),
        )

        # Parse captures
        for cap in captures_meta:
            recording.captures.append(
                SigMFCapture(
                    sample_start=cap.get("core:sample_start", 0),
                    frequency=cap.get("core:frequency"),
                    datetime=cap.get("core:datetime"),
                )
            )

        # Parse annotations
        for ann in annotations_meta:
            recording.annotations.append(
                SigMFAnnotation(
                    sample_start=ann.get("core:sample_start", 0),
                    sample_count=ann.get("core:sample_count", 0),
                    frequency_lower_edge=ann.get("core:freq_lower_edge"),
                    frequency_upper_edge=ann.get("core:freq_upper_edge"),
                    label=ann.get("core:label"),
                    comment=ann.get("core:comment"),
                )
            )

        return recording

    def to_numpy(self) -> NDArray[np.complex64]:
        """Load samples as numpy array.

        Returns:
            Complex samples array.
        """
        dtype = DTYPE_MAP.get(self.datatype, np.complex64)
        samples = np.fromfile(self.data_path, dtype=dtype)
        return samples.astype(np.complex64)

    def save_metadata(self) -> None:
        """Save metadata to .sigmf-meta file."""
        metadata = {
            "global": {
                "core:datatype": self.datatype,
                "core:sample_rate": self.sample_rate,
                "core:version": self.version,
                "core:description": self.description,
            },
            "captures": [],
            "annotations": [],
        }

        # Add optional global fields
        if self.author:
            metadata["global"]["core:author"] = self.author
        if self.recorder:
            metadata["global"]["core:recorder"] = self.recorder
        if self.license:
            metadata["global"]["core:license"] = self.license
        if self.hw:
            metadata["global"]["core:hw"] = self.hw

        # Add captures
        for cap in self.captures:
            cap_dict: dict[str, object] = {"core:sample_start": cap.sample_start}
            if cap.frequency is not None:
                cap_dict["core:frequency"] = cap.frequency
            if cap.datetime is not None:
                cap_dict["core:datetime"] = cap.datetime
            metadata["captures"].append(cap_dict)

        # Add annotations
        for ann in self.annotations:
            ann_dict: dict[str, object] = {
                "core:sample_start": ann.sample_start,
                "core:sample_count": ann.sample_count,
            }
            if ann.frequency_lower_edge is not None:
                ann_dict["core:freq_lower_edge"] = ann.frequency_lower_edge
            if ann.frequency_upper_edge is not None:
                ann_dict["core:freq_upper_edge"] = ann.frequency_upper_edge
            if ann.label is not None:
                ann_dict["core:label"] = ann.label
            if ann.comment is not None:
                ann_dict["core:comment"] = ann.comment
            metadata["annotations"].append(ann_dict)

        with open(self.meta_path, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info("Saved metadata to %s", self.meta_path)

    def add_annotation(
        self,
        sample_start: int,
        sample_count: int,
        label: str | None = None,
        comment: str | None = None,
        freq_lower: float | None = None,
        freq_upper: float | None = None,
    ) -> None:
        """Add an annotation to the recording.

        Args:
            sample_start: Start sample index.
            sample_count: Number of samples.
            label: Signal label/type.
            comment: Additional comment.
            freq_lower: Lower frequency edge in Hz.
            freq_upper: Upper frequency edge in Hz.
        """
        self.annotations.append(
            SigMFAnnotation(
                sample_start=sample_start,
                sample_count=sample_count,
                label=label,
                comment=comment,
                frequency_lower_edge=freq_lower,
                frequency_upper_edge=freq_upper,
            )
        )

    @property
    def duration_seconds(self) -> float:
        """Get recording duration in seconds."""
        if self.sample_rate <= 0:
            return 0.0
        num_samples = self.data_path.stat().st_size // np.dtype(
            DTYPE_MAP[self.datatype]
        ).itemsize
        return num_samples / self.sample_rate

    @property
    def center_frequency(self) -> float | None:
        """Get center frequency from first capture."""
        if self.captures:
            return self.captures[0].frequency
        return None

    def __repr__(self) -> str:
        return (
            f"SigMFRecording("
            f"path={self.data_path.name}, "
            f"rate={self.sample_rate/1e6:.3f}MHz, "
            f"freq={self.center_frequency and self.center_frequency/1e6:.3f}MHz, "
            f"duration={self.duration_seconds:.2f}s)"
        )
