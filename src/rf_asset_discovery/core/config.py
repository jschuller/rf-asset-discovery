"""Configuration constants and platform-specific settings."""

from __future__ import annotations

import platform
from dataclasses import dataclass, field
from typing import Literal

# =============================================================================
# Sample Rates
# =============================================================================
DEFAULT_SAMPLE_RATE: float = 2.048e6  # 2.048 MHz - common default
APPLE_SILICON_SAMPLE_RATE: float = 1.024e6  # Lower for USB stability on M-series
MIN_SAMPLE_RATE: float = 225.001e3  # RTL-SDR minimum
MAX_SAMPLE_RATE: float = 3.2e6  # RTL-SDR maximum (may be unstable)

# =============================================================================
# FM Broadcast Parameters
# =============================================================================
FM_DEVIATION_HZ: float = 75_000  # FM broadcast deviation (75 kHz)
FM_AUDIO_RATE: int = 48_000  # Audio sample rate for output
FM_STEREO_PILOT_HZ: float = 19_000  # Stereo pilot tone frequency
FM_BAND_START_MHZ: float = 87.5  # FM broadcast band start
FM_BAND_END_MHZ: float = 108.0  # FM broadcast band end

# =============================================================================
# FFT / Spectrum Analysis
# =============================================================================
DEFAULT_FFT_SIZE: int = 2048
DEFAULT_WINDOW: Literal["hamming", "hann", "blackman", "bartlett", "none"] = "hamming"
DEFAULT_OVERLAP: float = 0.5  # 50% overlap for spectrograms

# =============================================================================
# Device Defaults
# =============================================================================
DEFAULT_GAIN: str = "auto"  # or float in dB
DEFAULT_PPM_CORRECTION: int = 0  # Frequency correction in PPM
DEFAULT_BANDWIDTH: float = 0  # 0 = automatic based on sample rate

# =============================================================================
# Retry Logic (for Apple Silicon USB stability)
# =============================================================================
MAX_RETRIES: int = 3
RETRY_DELAY_MS: int = 500
USB_RESET_DELAY_MS: int = 1000


@dataclass
class SDRConfig:
    """Platform-specific SDR configuration."""

    sample_rate: float = DEFAULT_SAMPLE_RATE
    gain: float | str = DEFAULT_GAIN
    ppm_correction: int = DEFAULT_PPM_CORRECTION
    max_retries: int = MAX_RETRIES
    retry_delay_ms: int = RETRY_DELAY_MS
    buffer_size: int = 256 * 1024  # 256 KB default
    use_agc: bool = False
    extra_settings: dict[str, object] = field(default_factory=dict)


@dataclass
class AppleSiliconConfig(SDRConfig):
    """Configuration optimized for macOS Apple Silicon."""

    sample_rate: float = APPLE_SILICON_SAMPLE_RATE
    max_retries: int = 5  # More retries for USB stability
    retry_delay_ms: int = 1000  # Longer delay between retries
    buffer_size: int = 128 * 1024  # Smaller buffer for stability


@dataclass
class LinuxConfig(SDRConfig):
    """Configuration for Linux (Debian, ParrotOS, etc.)."""

    sample_rate: float = DEFAULT_SAMPLE_RATE
    max_retries: int = 3
    buffer_size: int = 256 * 1024


def get_platform_config() -> SDRConfig:
    """Get platform-appropriate SDR configuration.

    Returns:
        SDRConfig: Configuration optimized for the current platform.
    """
    system = platform.system()
    machine = platform.machine()

    if system == "Darwin" and machine == "arm64":
        return AppleSiliconConfig()
    elif system == "Linux":
        return LinuxConfig()
    else:
        return SDRConfig()


def is_apple_silicon() -> bool:
    """Check if running on Apple Silicon."""
    return platform.system() == "Darwin" and platform.machine() == "arm64"


def get_dyld_library_path() -> str | None:
    """Get DYLD_LIBRARY_PATH for Homebrew on Apple Silicon."""
    if is_apple_silicon():
        return "/opt/homebrew/lib"
    return None
