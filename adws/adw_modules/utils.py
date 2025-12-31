"""Utility functions for SDR agentic workflows."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from adws.adw_modules.data_models import (
    AnalysisResult,
    RecordingResult,
    ScanResult,
    WorkflowState,
)

logger = logging.getLogger(__name__)


def ensure_output_dir(path: Path | str) -> Path:
    """Ensure output directory exists.

    Args:
        path: Directory path.

    Returns:
        Path object for the directory.
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_workflow_state(state: WorkflowState, output_dir: Path | str) -> Path:
    """Save workflow state to JSON file.

    Args:
        state: Workflow state to save.
        output_dir: Output directory.

    Returns:
        Path to saved file.
    """
    output_dir = ensure_output_dir(output_dir)
    filename = f"{state.adw_id}_state.json"
    filepath = output_dir / filename

    with open(filepath, "w") as f:
        json.dump(state.model_dump(mode="json"), f, indent=2, default=str)

    logger.info("Saved workflow state to %s", filepath)
    return filepath


def load_workflow_state(filepath: Path | str) -> WorkflowState:
    """Load workflow state from JSON file.

    Args:
        filepath: Path to state file.

    Returns:
        WorkflowState object.
    """
    with open(filepath) as f:
        data = json.load(f)
    return WorkflowState(**data)


def save_scan_result(result: ScanResult, output_dir: Path | str) -> Path:
    """Save scan result to JSON file.

    Args:
        result: Scan result to save.
        output_dir: Output directory.

    Returns:
        Path to saved file.
    """
    output_dir = ensure_output_dir(output_dir)
    filename = f"{result.adw_id}_scan.json"
    filepath = output_dir / filename

    with open(filepath, "w") as f:
        json.dump(result.model_dump(mode="json"), f, indent=2, default=str)

    logger.info("Saved scan result to %s", filepath)
    return filepath


def save_recording_result(result: RecordingResult, output_dir: Path | str) -> Path:
    """Save recording result to JSON file."""
    output_dir = ensure_output_dir(output_dir)
    filename = f"{result.adw_id}_recording.json"
    filepath = output_dir / filename

    with open(filepath, "w") as f:
        json.dump(result.model_dump(mode="json"), f, indent=2, default=str)

    logger.info("Saved recording result to %s", filepath)
    return filepath


def save_analysis_result(result: AnalysisResult, output_dir: Path | str) -> Path:
    """Save analysis result to JSON file."""
    output_dir = ensure_output_dir(output_dir)
    filename = f"{result.adw_id}_analysis.json"
    filepath = output_dir / filename

    with open(filepath, "w") as f:
        json.dump(result.model_dump(mode="json"), f, indent=2, default=str)

    logger.info("Saved analysis result to %s", filepath)
    return filepath


def format_frequency(freq_hz: float) -> str:
    """Format frequency for display.

    Args:
        freq_hz: Frequency in Hz.

    Returns:
        Formatted string (e.g., "100.1 MHz").
    """
    if freq_hz >= 1e9:
        return f"{freq_hz / 1e9:.3f} GHz"
    elif freq_hz >= 1e6:
        return f"{freq_hz / 1e6:.3f} MHz"
    elif freq_hz >= 1e3:
        return f"{freq_hz / 1e3:.3f} kHz"
    else:
        return f"{freq_hz:.0f} Hz"


def format_duration(seconds: float) -> str:
    """Format duration for display.

    Args:
        seconds: Duration in seconds.

    Returns:
        Formatted string (e.g., "2m 30s").
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.0f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def format_file_size(bytes_: int) -> str:
    """Format file size for display.

    Args:
        bytes_: Size in bytes.

    Returns:
        Formatted string (e.g., "1.5 MB").
    """
    if bytes_ >= 1e9:
        return f"{bytes_ / 1e9:.2f} GB"
    elif bytes_ >= 1e6:
        return f"{bytes_ / 1e6:.2f} MB"
    elif bytes_ >= 1e3:
        return f"{bytes_ / 1e3:.2f} KB"
    else:
        return f"{bytes_} bytes"


def generate_report(
    scan_result: ScanResult | None = None,
    recording_result: RecordingResult | None = None,
    analysis_result: AnalysisResult | None = None,
) -> str:
    """Generate a human-readable report from results.

    Args:
        scan_result: Optional scan result.
        recording_result: Optional recording result.
        analysis_result: Optional analysis result.

    Returns:
        Formatted report string.
    """
    lines = []
    lines.append("=" * 60)
    lines.append("SDR WORKFLOW REPORT")
    lines.append("=" * 60)
    lines.append("")

    if scan_result:
        lines.append("SPECTRUM SCAN")
        lines.append("-" * 40)
        lines.append(
            f"Range: {scan_result.start_freq_mhz:.1f} - {scan_result.end_freq_mhz:.1f} MHz"
        )
        lines.append(f"Duration: {format_duration(scan_result.scan_time_seconds)}")
        lines.append(f"Noise Floor: {scan_result.noise_floor_db:.1f} dB")
        lines.append(f"Signals Found: {scan_result.num_signals}")
        lines.append("")

        if scan_result.peaks:
            lines.append("Top Signals:")
            for i, peak in enumerate(scan_result.get_strongest(10), 1):
                label = f" ({peak.label})" if peak.label else ""
                lines.append(
                    f"  {i}. {peak.frequency_mhz:.3f} MHz: {peak.power_db:.1f} dB{label}"
                )
        lines.append("")

    if recording_result:
        lines.append("RECORDING")
        lines.append("-" * 40)
        lines.append(f"File: {recording_result.recording_path}")
        lines.append(f"Frequency: {recording_result.center_freq_mhz:.3f} MHz")
        lines.append(f"Duration: {format_duration(recording_result.duration_seconds)}")
        lines.append(f"Sample Rate: {recording_result.sample_rate_hz / 1e6:.3f} MHz")
        lines.append(f"Samples: {recording_result.num_samples:,}")
        lines.append(f"Size: {format_file_size(recording_result.file_size_bytes)}")
        lines.append("")

    if analysis_result:
        lines.append("ANALYSIS")
        lines.append("-" * 40)
        lines.append(f"Type: {analysis_result.analysis_type}")
        lines.append(f"Signal Type: {analysis_result.signal_type.value}")
        lines.append(f"Signal Strength: {analysis_result.signal_strength_db:.1f} dB")
        lines.append(f"SNR: {analysis_result.snr_db:.1f} dB")
        if analysis_result.bandwidth_khz:
            lines.append(f"Bandwidth: {analysis_result.bandwidth_khz:.1f} kHz")
        if analysis_result.modulation:
            lines.append(f"Modulation: {analysis_result.modulation}")
        lines.append("")
        if analysis_result.summary:
            lines.append("Summary:")
            lines.append(f"  {analysis_result.summary}")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)
