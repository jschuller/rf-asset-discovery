"""Audio playback with sounddevice."""

from __future__ import annotations

import logging
from collections import deque
from threading import Lock
from typing import TYPE_CHECKING

import numpy as np
import sounddevice as sd

from sdr_toolkit.core.config import FM_AUDIO_RATE

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)


class AudioPlayer:
    """Audio player with buffered playback.

    Uses a deque-based buffer for efficient audio streaming.

    Example:
        >>> player = AudioPlayer(sample_rate=48000)
        >>> player.start()
        >>> player.write(audio_samples)
        >>> player.stop()
    """

    def __init__(
        self,
        sample_rate: int = FM_AUDIO_RATE,
        channels: int = 1,
        buffer_size: int = 4096,
        device: int | str | None = None,
    ) -> None:
        """Initialize audio player.

        Args:
            sample_rate: Audio sample rate in Hz.
            channels: Number of audio channels.
            buffer_size: Size of audio buffer in samples.
            device: Audio device index or name.
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.buffer_size = buffer_size
        self.device = device

        self._buffer: deque[float] = deque(maxlen=buffer_size * 10)
        self._lock = Lock()
        self._stream: sd.OutputStream | None = None
        self._running = False

    def start(self) -> None:
        """Start audio playback."""
        if self._running:
            return

        self._stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            callback=self._audio_callback,
            blocksize=self.buffer_size,
            device=self.device,
        )
        self._stream.start()
        self._running = True
        logger.debug("Audio playback started")

    def stop(self) -> None:
        """Stop audio playback."""
        if not self._running:
            return

        self._running = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        logger.debug("Audio playback stopped")

    def write(self, samples: NDArray[np.float64]) -> None:
        """Write samples to audio buffer.

        Args:
            samples: Audio samples to play.
        """
        with self._lock:
            self._buffer.extend(samples.flatten())

    def clear(self) -> None:
        """Clear audio buffer."""
        with self._lock:
            self._buffer.clear()

    @property
    def buffer_level(self) -> int:
        """Get current buffer level in samples."""
        with self._lock:
            return len(self._buffer)

    @property
    def is_running(self) -> bool:
        """Check if player is running."""
        return self._running

    def _audio_callback(
        self,
        outdata: NDArray[np.float32],
        frames: int,
        time: object,
        status: sd.CallbackFlags,
    ) -> None:
        """Audio callback for sounddevice."""
        if status:
            logger.warning("Audio callback status: %s", status)

        with self._lock:
            available = len(self._buffer)

            if available < frames:
                # Underrun - fill with silence
                outdata.fill(0)
                if available > 0:
                    for i in range(available):
                        outdata[i, 0] = self._buffer.popleft()
                return

            # Fill output buffer
            for i in range(frames):
                outdata[i, 0] = self._buffer.popleft()

    def __enter__(self) -> AudioPlayer:
        """Context manager entry."""
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Context manager exit."""
        self.stop()


class StereoAudioPlayer(AudioPlayer):
    """Audio player for stereo playback."""

    def __init__(
        self,
        sample_rate: int = FM_AUDIO_RATE,
        buffer_size: int = 4096,
        device: int | str | None = None,
    ) -> None:
        """Initialize stereo audio player."""
        super().__init__(
            sample_rate=sample_rate,
            channels=2,
            buffer_size=buffer_size,
            device=device,
        )
        self._left_buffer: deque[float] = deque(maxlen=buffer_size * 10)
        self._right_buffer: deque[float] = deque(maxlen=buffer_size * 10)

    def write_stereo(
        self,
        left: NDArray[np.float64],
        right: NDArray[np.float64],
    ) -> None:
        """Write stereo samples.

        Args:
            left: Left channel samples.
            right: Right channel samples.
        """
        with self._lock:
            self._left_buffer.extend(left.flatten())
            self._right_buffer.extend(right.flatten())

    def _audio_callback(
        self,
        outdata: NDArray[np.float32],
        frames: int,
        time: object,
        status: sd.CallbackFlags,
    ) -> None:
        """Stereo audio callback."""
        if status:
            logger.warning("Audio callback status: %s", status)

        with self._lock:
            available = min(len(self._left_buffer), len(self._right_buffer))

            if available < frames:
                outdata.fill(0)
                for i in range(available):
                    outdata[i, 0] = self._left_buffer.popleft()
                    outdata[i, 1] = self._right_buffer.popleft()
                return

            for i in range(frames):
                outdata[i, 0] = self._left_buffer.popleft()
                outdata[i, 1] = self._right_buffer.popleft()


def list_audio_devices() -> list[dict[str, object]]:
    """List available audio devices.

    Returns:
        List of device information dictionaries.
    """
    devices = sd.query_devices()
    result: list[dict[str, object]] = []

    for i, dev in enumerate(devices):
        if dev["max_output_channels"] > 0:
            result.append({
                "index": i,
                "name": dev["name"],
                "channels": dev["max_output_channels"],
                "default_samplerate": dev["default_samplerate"],
                "is_default": i == sd.default.device[1],
            })

    return result


def get_default_output_device() -> int | None:
    """Get default audio output device index."""
    default = sd.default.device
    if isinstance(default, tuple):
        return default[1]
    return default
