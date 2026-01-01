"""AM Radio application for aircraft and other AM signals."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from rf_asset_discovery.core.config import (
    APPLE_SILICON_SAMPLE_RATE,
    FM_AUDIO_RATE,
    get_platform_config,
    is_apple_silicon,
)
from rf_asset_discovery.core.device import SDRDevice
from rf_asset_discovery.dsp.demodulation import am_demodulate, compute_signal_strength
from rf_asset_discovery.io.audio import AudioPlayer

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Aircraft band constants
AIRCRAFT_BAND_START_MHZ = 118.0
AIRCRAFT_BAND_END_MHZ = 137.0


@dataclass
class AMRadio:
    """AM Radio receiver application.

    Designed for aircraft band (118-137 MHz) and other AM signals.

    Example:
        >>> radio = AMRadio(freq_mhz=119.1)  # JFK Tower
        >>> radio.play(duration=60)  # Listen for 60 seconds
    """

    freq_mhz: float = 119.1
    gain: float | str = "auto"
    sample_rate: float = field(default_factory=lambda: get_platform_config().sample_rate)
    audio_rate: int = FM_AUDIO_RATE
    device_index: int = 0

    # State
    _device: SDRDevice | None = field(default=None, repr=False, init=False)
    _player: AudioPlayer | None = field(default=None, repr=False, init=False)
    _running: bool = field(default=False, repr=False, init=False)

    def __post_init__(self) -> None:
        """Apply platform-specific defaults."""
        if is_apple_silicon() and self.sample_rate > APPLE_SILICON_SAMPLE_RATE:
            logger.info(
                "Reducing sample rate to %.0f for Apple Silicon stability",
                APPLE_SILICON_SAMPLE_RATE,
            )
            self.sample_rate = APPLE_SILICON_SAMPLE_RATE

    def play(self, duration: float | None = None) -> None:
        """Start AM radio playback.

        Args:
            duration: Playback duration in seconds (None = indefinite).
        """
        center_freq = self.freq_mhz * 1e6
        block_size = int(self.sample_rate * 0.1)  # 100ms blocks

        # Warn if outside aircraft band
        if not (AIRCRAFT_BAND_START_MHZ <= self.freq_mhz <= AIRCRAFT_BAND_END_MHZ):
            logger.info(
                "Frequency %.3f MHz is outside aircraft band (%.0f-%.0f MHz)",
                self.freq_mhz,
                AIRCRAFT_BAND_START_MHZ,
                AIRCRAFT_BAND_END_MHZ,
            )

        logger.info("Tuning to %.3f MHz (AM mode)...", self.freq_mhz)

        with SDRDevice(
            sample_rate=self.sample_rate,
            center_freq=center_freq,
            gain=self.gain,
            device_index=self.device_index,
        ) as device:
            self._device = device

            with AudioPlayer(sample_rate=self.audio_rate) as player:
                self._player = player
                self._running = True

                start_time = time.time()
                logger.info("Playing AM radio (Ctrl+C to stop)...")

                try:
                    while self._running:
                        if duration is not None:
                            elapsed = time.time() - start_time
                            if elapsed >= duration:
                                break

                        # Read samples
                        samples = device.read_samples(block_size)

                        # Demodulate using AM envelope detection
                        audio, _ = am_demodulate(
                            samples,
                            self.sample_rate,
                            self.audio_rate,
                        )

                        # Play audio
                        player.write(audio)

                        # Log signal strength periodically
                        if int(time.time()) % 5 == 0:
                            strength = compute_signal_strength(samples)
                            logger.debug("Signal strength: %.1f dB", strength)

                except KeyboardInterrupt:
                    logger.info("Stopped by user")
                finally:
                    self._running = False
                    self._device = None
                    self._player = None

    def stop(self) -> None:
        """Stop playback."""
        self._running = False

    def tune(self, freq_mhz: float) -> None:
        """Change frequency.

        Args:
            freq_mhz: New frequency in MHz.
        """
        self.freq_mhz = freq_mhz
        if self._device is not None and self._device.is_open:
            self._device.set_center_freq(freq_mhz * 1e6)
            logger.info("Tuned to %.3f MHz", freq_mhz)

    def set_gain(self, gain: float | str) -> None:
        """Change gain setting.

        Args:
            gain: New gain in dB or "auto".
        """
        self.gain = gain
        if self._device is not None and self._device.is_open:
            self._device.set_gain(gain)

    @property
    def is_playing(self) -> bool:
        """Check if radio is currently playing."""
        return self._running

    def get_signal_strength(self) -> float | None:
        """Get current signal strength in dB."""
        if self._device is None or not self._device.is_open:
            return None

        try:
            samples = self._device.read_samples(1024)
            return compute_signal_strength(samples)
        except Exception:
            return None


def play_am(
    freq_mhz: float = 119.1,
    duration: float | None = None,
    gain: float | str = "auto",
) -> None:
    """Play AM radio signal.

    Convenience function for quick AM listening.
    Default frequency is JFK Tower (119.1 MHz).

    Args:
        freq_mhz: Frequency in MHz.
        duration: Duration in seconds (None = until Ctrl+C).
        gain: Gain setting.
    """
    radio = AMRadio(freq_mhz=freq_mhz, gain=gain)
    radio.play(duration=duration)


def listen_aircraft(
    freq_mhz: float = 119.1,
    duration: float | None = None,
    gain: float | str = "auto",
) -> None:
    """Listen to aircraft communications.

    Convenience function for aircraft band monitoring.

    Common NYC area frequencies:
        - 119.1 MHz: JFK Tower
        - 118.7 MHz: LGA Tower
        - 118.3 MHz: EWR Tower
        - 119.5 MHz: TEB Tower
        - 121.5 MHz: Emergency frequency
        - 125.95 MHz: NY Approach/Departure

    Args:
        freq_mhz: Frequency in MHz (default: JFK Tower 119.1).
        duration: Duration in seconds (None = until Ctrl+C).
        gain: Gain setting.
    """
    if not (AIRCRAFT_BAND_START_MHZ <= freq_mhz <= AIRCRAFT_BAND_END_MHZ):
        logger.warning(
            "%.3f MHz is outside the aircraft band (%.0f-%.0f MHz)",
            freq_mhz,
            AIRCRAFT_BAND_START_MHZ,
            AIRCRAFT_BAND_END_MHZ,
        )

    radio = AMRadio(freq_mhz=freq_mhz, gain=gain)
    radio.play(duration=duration)
