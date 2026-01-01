"""Custom exception hierarchy for SDR operations."""

from __future__ import annotations


class SDRError(Exception):
    """Base exception for all SDR-related errors."""

    def __init__(self, message: str, details: str | None = None) -> None:
        self.message = message
        self.details = details
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


class DeviceError(SDRError):
    """Error related to SDR device operations."""

    pass


class DeviceNotFoundError(DeviceError):
    """No SDR device found or device is not accessible."""

    def __init__(self, details: str | None = None) -> None:
        super().__init__("No SDR device found", details)


class USBError(DeviceError):
    """USB communication error with SDR device."""

    def __init__(self, error_code: int, details: str | None = None) -> None:
        self.error_code = error_code
        message = f"USB error (code {error_code})"
        super().__init__(message, details)


class DeviceBusyError(DeviceError):
    """Device is busy or already in use."""

    def __init__(self, details: str | None = None) -> None:
        super().__init__("Device is busy or in use by another process", details)


class SampleRateError(DeviceError):
    """Invalid or unsupported sample rate."""

    def __init__(self, sample_rate: float, details: str | None = None) -> None:
        self.sample_rate = sample_rate
        message = f"Unsupported sample rate: {sample_rate / 1e6:.3f} MHz"
        super().__init__(message, details)


class FrequencyError(DeviceError):
    """Invalid or out-of-range frequency."""

    def __init__(self, frequency: float, details: str | None = None) -> None:
        self.frequency = frequency
        message = f"Invalid frequency: {frequency / 1e6:.3f} MHz"
        super().__init__(message, details)


class GainError(DeviceError):
    """Invalid gain setting."""

    def __init__(self, gain: float | str, details: str | None = None) -> None:
        self.gain = gain
        message = f"Invalid gain setting: {gain}"
        super().__init__(message, details)


class SignalProcessingError(SDRError):
    """Error during signal processing operations."""

    pass


class DemodulationError(SignalProcessingError):
    """Error during signal demodulation."""

    pass


class RecordingError(SDRError):
    """Error during signal recording."""

    pass


class SigMFError(RecordingError):
    """Error with SigMF format operations."""

    pass
