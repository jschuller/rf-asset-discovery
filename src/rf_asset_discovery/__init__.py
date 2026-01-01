"""RF Asset Discovery - Production-quality RTL-SDR toolkit with agentic capabilities."""

from rf_asset_discovery.core.config import (
    APPLE_SILICON_SAMPLE_RATE,
    DEFAULT_FFT_SIZE,
    DEFAULT_SAMPLE_RATE,
    FM_AUDIO_RATE,
    FM_DEVIATION_HZ,
)
from rf_asset_discovery.core.device import SDRDevice
from rf_asset_discovery.core.exceptions import (
    DeviceError,
    DeviceNotFoundError,
    SDRError,
    USBError,
)

__version__ = "0.1.0"

__all__ = [
    # Device
    "SDRDevice",
    # Config
    "DEFAULT_SAMPLE_RATE",
    "APPLE_SILICON_SAMPLE_RATE",
    "FM_DEVIATION_HZ",
    "FM_AUDIO_RATE",
    "DEFAULT_FFT_SIZE",
    # Exceptions
    "SDRError",
    "DeviceError",
    "DeviceNotFoundError",
    "USBError",
]
