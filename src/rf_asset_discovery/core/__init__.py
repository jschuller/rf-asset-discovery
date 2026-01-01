"""Core SDR functionality - device management, configuration, exceptions."""

from rf_asset_discovery.core.config import (
    APPLE_SILICON_SAMPLE_RATE,
    DEFAULT_FFT_SIZE,
    DEFAULT_SAMPLE_RATE,
    DEFAULT_WINDOW,
    FM_AUDIO_RATE,
    FM_DEVIATION_HZ,
    get_platform_config,
)
from rf_asset_discovery.core.device import SDRDevice
from rf_asset_discovery.core.exceptions import (
    DeviceError,
    DeviceNotFoundError,
    SDRError,
    USBError,
)

__all__ = [
    "SDRDevice",
    "DEFAULT_SAMPLE_RATE",
    "APPLE_SILICON_SAMPLE_RATE",
    "FM_DEVIATION_HZ",
    "FM_AUDIO_RATE",
    "DEFAULT_FFT_SIZE",
    "DEFAULT_WINDOW",
    "get_platform_config",
    "SDRError",
    "DeviceError",
    "DeviceNotFoundError",
    "USBError",
]
