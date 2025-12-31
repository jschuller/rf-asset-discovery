"""RTL-SDR device management with context manager and retry logic."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Self

import numpy as np

from sdr_toolkit.core.config import (
    DEFAULT_GAIN,
    get_platform_config,
    is_apple_silicon,
)
from sdr_toolkit.core.exceptions import (
    DeviceBusyError,
    DeviceError,
    DeviceNotFoundError,
    FrequencyError,
    GainError,
    SampleRateError,
    USBError,
)

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)


@dataclass
class SDRDevice:
    """RTL-SDR device wrapper with automatic resource management.

    Provides context manager protocol for safe device handling,
    platform-specific optimizations, and retry logic for reliability.

    Example:
        >>> with SDRDevice(center_freq=100.1e6) as sdr:
        ...     samples = sdr.read_samples(1024)
        ...     print(f"Read {len(samples)} samples")
    """

    sample_rate: float = field(default_factory=lambda: get_platform_config().sample_rate)
    center_freq: float = 100.0e6  # 100 MHz default
    gain: float | str = DEFAULT_GAIN
    ppm_correction: int = 0
    device_index: int = 0

    # Internal state
    _sdr: object = field(default=None, repr=False, init=False)
    _is_open: bool = field(default=False, repr=False, init=False)
    _config: object = field(default=None, repr=False, init=False)

    def __post_init__(self) -> None:
        """Initialize platform config."""
        self._config = get_platform_config()

    def __enter__(self) -> Self:
        """Open device and configure for use."""
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Close device and release resources."""
        self.close()

    def open(self) -> None:
        """Open and configure the RTL-SDR device.

        Raises:
            DeviceNotFoundError: If no device is found.
            DeviceBusyError: If device is already in use.
            USBError: If USB communication fails.
        """
        if self._is_open:
            return

        try:
            from rtlsdr import RtlSdr
        except ImportError as e:
            raise DeviceError(
                "pyrtlsdr not installed",
                "Install with: pip install pyrtlsdr",
            ) from e

        max_retries = getattr(self._config, "max_retries", 3)
        retry_delay_ms = getattr(self._config, "retry_delay_ms", 500)

        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                logger.debug(
                    "Opening device (attempt %d/%d)",
                    attempt + 1,
                    max_retries,
                )
                self._sdr = RtlSdr(self.device_index)
                self._configure_device()
                self._is_open = True
                logger.info(
                    "Device opened: %.3f MHz @ %.3f MS/s",
                    self.center_freq / 1e6,
                    self.sample_rate / 1e6,
                )
                return

            except OSError as e:
                last_error = e
                error_str = str(e).lower()

                if "no supported devices found" in error_str:
                    raise DeviceNotFoundError(str(e)) from e
                elif "resource busy" in error_str or "usb claim" in error_str:
                    raise DeviceBusyError(str(e)) from e
                elif "libusb" in error_str:
                    # USB error - retry
                    logger.warning("USB error on attempt %d: %s", attempt + 1, e)
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay_ms / 1000)
                    continue
                else:
                    raise DeviceError("Failed to open device", str(e)) from e

            except Exception as e:
                last_error = e
                logger.warning("Unexpected error on attempt %d: %s", attempt + 1, e)
                if attempt < max_retries - 1:
                    time.sleep(retry_delay_ms / 1000)
                continue

        # All retries exhausted
        raise DeviceError(
            "Failed to open device after retries",
            str(last_error) if last_error else None,
        )

    def _configure_device(self) -> None:
        """Apply device configuration settings."""
        if self._sdr is None:
            return

        # Sample rate
        try:
            self._sdr.sample_rate = self.sample_rate
        except Exception as e:
            raise SampleRateError(self.sample_rate, str(e)) from e

        # Center frequency
        try:
            self._sdr.center_freq = self.center_freq
        except Exception as e:
            raise FrequencyError(self.center_freq, str(e)) from e

        # Gain
        try:
            if self.gain == "auto":
                self._sdr.set_agc_mode(True)
            else:
                self._sdr.set_agc_mode(False)
                self._sdr.gain = float(self.gain)
        except Exception as e:
            raise GainError(self.gain, str(e)) from e

        # PPM correction
        if self.ppm_correction != 0:
            try:
                self._sdr.freq_correction = self.ppm_correction
            except Exception as e:
                logger.warning("Failed to set PPM correction: %s", e)

    def close(self) -> None:
        """Close device and release resources."""
        if self._sdr is not None and self._is_open:
            try:
                self._sdr.close()
                logger.debug("Device closed")
            except Exception as e:
                logger.warning("Error closing device: %s", e)
            finally:
                self._sdr = None
                self._is_open = False

    def read_samples(self, num_samples: int) -> NDArray[np.complex64]:
        """Read IQ samples from the device.

        Args:
            num_samples: Number of complex samples to read.

        Returns:
            Complex64 numpy array of IQ samples.

        Raises:
            DeviceError: If device is not open or read fails.
        """
        if not self._is_open or self._sdr is None:
            raise DeviceError("Device is not open")

        max_retries = 3 if is_apple_silicon() else 1

        for attempt in range(max_retries):
            try:
                samples = self._sdr.read_samples(num_samples)
                return np.asarray(samples, dtype=np.complex64)

            except Exception as e:
                error_str = str(e).lower()
                if "overflow" in error_str or "libusb" in error_str:
                    if attempt < max_retries - 1:
                        logger.warning(
                            "USB overflow, retrying (%d/%d)",
                            attempt + 1,
                            max_retries,
                        )
                        time.sleep(0.1)
                        continue
                raise USBError(-1, str(e)) from e

        raise DeviceError("Failed to read samples after retries")

    @property
    def is_open(self) -> bool:
        """Check if device is currently open."""
        return self._is_open

    def set_center_freq(self, freq: float) -> None:
        """Change center frequency.

        Args:
            freq: New center frequency in Hz.

        Raises:
            FrequencyError: If frequency is invalid.
        """
        if not self._is_open or self._sdr is None:
            self.center_freq = freq
            return

        try:
            self._sdr.center_freq = freq
            self.center_freq = freq
        except Exception as e:
            raise FrequencyError(freq, str(e)) from e

    def set_sample_rate(self, rate: float) -> None:
        """Change sample rate.

        Args:
            rate: New sample rate in Hz.

        Raises:
            SampleRateError: If rate is invalid or unsupported.
        """
        if not self._is_open or self._sdr is None:
            self.sample_rate = rate
            return

        try:
            self._sdr.sample_rate = rate
            self.sample_rate = rate
        except Exception as e:
            raise SampleRateError(rate, str(e)) from e

    def set_gain(self, gain: float | str) -> None:
        """Change gain setting.

        Args:
            gain: Gain in dB or "auto" for AGC.

        Raises:
            GainError: If gain is invalid.
        """
        if not self._is_open or self._sdr is None:
            self.gain = gain
            return

        try:
            if gain == "auto":
                self._sdr.set_agc_mode(True)
            else:
                self._sdr.set_agc_mode(False)
                self._sdr.gain = float(gain)
            self.gain = gain
        except Exception as e:
            raise GainError(gain, str(e)) from e

    def get_tuner_gains(self) -> list[float]:
        """Get list of supported gain values.

        Returns:
            List of supported gain values in dB.
        """
        if not self._is_open or self._sdr is None:
            raise DeviceError("Device is not open")
        return list(self._sdr.valid_gains_db)

    def get_device_info(self) -> dict[str, object]:
        """Get device information.

        Returns:
            Dictionary with device details.
        """
        info: dict[str, object] = {
            "sample_rate": self.sample_rate,
            "center_freq": self.center_freq,
            "gain": self.gain,
            "ppm_correction": self.ppm_correction,
            "is_open": self._is_open,
        }

        if self._is_open and self._sdr is not None:
            try:
                info["tuner_type"] = str(getattr(self._sdr, "tuner_type", "unknown"))
                info["valid_gains"] = self.get_tuner_gains()
            except Exception:
                pass

        return info


def list_devices() -> list[dict[str, str]]:
    """List available RTL-SDR devices.

    Returns:
        List of device information dictionaries.
    """
    try:
        from rtlsdr import RtlSdr
    except ImportError:
        return []

    devices: list[dict[str, str]] = []
    device_index = 0

    while True:
        try:
            name = RtlSdr.get_device_name(device_index)
            serial = RtlSdr.get_device_serial_addresses()[device_index]
            devices.append({
                "index": str(device_index),
                "name": name,
                "serial": serial,
            })
            device_index += 1
        except (IndexError, OSError):
            break

    return devices
