"""rtl_433 subprocess wrapper for IoT signal decoding.

Provides a Python interface to rtl_433 with JSON streaming,
multi-frequency support, and graceful process management.
"""

from __future__ import annotations

import json
import logging
import shutil
import signal
import subprocess
from collections.abc import Iterator
from datetime import datetime
from types import TracebackType
from typing import Any

from rf_asset_discovery.decoders.iot.classifier import (
    classify_protocol,
    extract_device_id,
    extract_telemetry,
)
from rf_asset_discovery.decoders.iot.models import IoTPacket

logger = logging.getLogger(__name__)


class RTL433Error(Exception):
    """Exception for rtl_433 subprocess errors."""

    pass


def check_rtl433_available() -> bool:
    """Check if rtl_433 binary is available in PATH.

    Returns:
        True if rtl_433 is found and executable.
    """
    return shutil.which("rtl_433") is not None


class RTL433Decoder:
    """rtl_433 subprocess wrapper with JSON streaming.

    Provides context manager interface for safe process management
    and iterators for streaming decoded packets.

    Example:
        >>> with RTL433Decoder(frequencies=["433.92M"]) as decoder:
        ...     for packet in decoder.stream_packets():
        ...         print(f"{packet.model}: {packet.device_id}")

    Attributes:
        frequencies: List of frequencies to scan (e.g., ["433.92M", "315M"]).
        hop_time_seconds: Dwell time per frequency when hopping.
        device_index: RTL-SDR device index.
        gain: Gain setting ("auto" or dB value).
    """

    def __init__(
        self,
        frequencies: list[str] | None = None,
        protocols: list[int] | None = None,
        hop_time_seconds: int = 30,
        device_index: int = 0,
        gain: str | int = "auto",
    ) -> None:
        """Initialize rtl_433 decoder.

        Args:
            frequencies: Frequencies to scan (default: ["433.92M"]).
            protocols: Protocol IDs to enable (-R flags). None = all.
            hop_time_seconds: Dwell time per frequency for multi-freq.
            device_index: RTL-SDR device index.
            gain: Gain setting ("auto" or dB value).
        """
        self.frequencies = frequencies or ["433.92M"]
        self.protocols = protocols
        self.hop_time_seconds = hop_time_seconds
        self.device_index = device_index
        self.gain = gain

        self._process: subprocess.Popen[str] | None = None
        self._running = False

    def __enter__(self) -> RTL433Decoder:
        """Context manager entry - start decoder."""
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Context manager exit - stop decoder."""
        self.stop()

    def _build_command(self) -> list[str]:
        """Build rtl_433 command line arguments.

        Returns:
            List of command arguments.
        """
        cmd = ["rtl_433"]

        # Device selection
        cmd.extend(["-d", str(self.device_index)])

        # Gain
        if self.gain == "auto":
            cmd.extend(["-g", "0"])  # 0 = auto gain
        else:
            cmd.extend(["-g", str(self.gain)])

        # Frequencies
        for freq in self.frequencies:
            cmd.extend(["-f", freq])

        # Hop time for multi-frequency
        if len(self.frequencies) > 1:
            cmd.extend(["-H", str(self.hop_time_seconds)])

        # Protocol selection
        if self.protocols:
            for proto in self.protocols:
                cmd.extend(["-R", str(proto)])

        # Output format: JSON with UTC timestamps
        cmd.extend(["-F", "json", "-M", "utc"])

        return cmd

    def start(self) -> None:
        """Start rtl_433 subprocess.

        Raises:
            RTL433Error: If rtl_433 is not available or fails to start.
        """
        if not check_rtl433_available():
            raise RTL433Error(
                "rtl_433 not found in PATH. Install with: "
                "brew install rtl_433 (macOS) or apt install rtl-433 (Linux)"
            )

        cmd = self._build_command()
        logger.info("Starting rtl_433: %s", " ".join(cmd))

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
            )
            self._running = True
            logger.info("rtl_433 started (PID: %d)", self._process.pid)
        except OSError as e:
            raise RTL433Error(f"Failed to start rtl_433: {e}") from e

    def stop(self) -> None:
        """Stop rtl_433 subprocess gracefully."""
        self._running = False

        if self._process is None:
            return

        logger.info("Stopping rtl_433...")

        # Try graceful termination first
        try:
            self._process.send_signal(signal.SIGTERM)
            self._process.wait(timeout=5)
            logger.info("rtl_433 stopped gracefully")
        except subprocess.TimeoutExpired:
            # Force kill if graceful fails
            logger.warning("rtl_433 didn't stop gracefully, killing...")
            self._process.kill()
            self._process.wait()
        finally:
            self._process = None

    def is_running(self) -> bool:
        """Check if decoder is currently running.

        Returns:
            True if subprocess is running.
        """
        if not self._running or self._process is None:
            return False
        return self._process.poll() is None

    def stream_raw(self) -> Iterator[dict[str, Any]]:
        """Stream raw JSON packets from rtl_433.

        Yields decoded JSON dicts without classification.

        Yields:
            Raw JSON dict from rtl_433 stdout.

        Raises:
            RTL433Error: If decoder not running.
        """
        if self._process is None or self._process.stdout is None:
            raise RTL433Error("Decoder not started. Use context manager or call start().")

        while self._running and self._process.poll() is None:
            line = self._process.stdout.readline()
            if not line:
                continue

            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
                yield data
            except json.JSONDecodeError as e:
                logger.debug("Failed to parse JSON: %s - %s", e, line[:100])
                continue

    def stream_packets(self) -> Iterator[IoTPacket]:
        """Stream classified IoT packets.

        Decodes JSON, extracts device ID, classifies protocol,
        and extracts telemetry values.

        Yields:
            IoTPacket with classification and telemetry.

        Example:
            >>> with RTL433Decoder() as decoder:
            ...     for packet in decoder.stream_packets():
            ...         print(f"{packet.protocol_type}: {packet.device_id}")
        """
        for raw_json in self.stream_raw():
            try:
                packet = self._parse_packet(raw_json)
                if packet:
                    yield packet
            except Exception as e:
                logger.debug("Failed to parse packet: %s", e)
                continue

    def _parse_packet(self, raw_json: dict[str, Any]) -> IoTPacket | None:
        """Parse raw JSON into IoTPacket.

        Args:
            raw_json: Decoded JSON from rtl_433.

        Returns:
            IoTPacket if valid, None otherwise.
        """
        # Must have model field
        model = raw_json.get("model")
        if not model:
            return None

        # Extract device ID
        device_id = extract_device_id(raw_json)

        # Classify protocol
        protocol_type = classify_protocol(model)

        # Parse timestamp
        time_str = raw_json.get("time")
        if time_str:
            try:
                timestamp = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            except ValueError:
                timestamp = datetime.now()
        else:
            timestamp = datetime.now()

        # Extract telemetry
        telemetry = extract_telemetry(raw_json)

        # Get frequency if available
        freq_mhz = raw_json.get("freq")
        if freq_mhz is None and "freq1" in raw_json:
            freq_mhz = raw_json["freq1"]

        return IoTPacket(
            raw_json=raw_json,
            timestamp=timestamp,
            model=model,
            device_id=device_id,
            protocol_type=protocol_type,
            frequency_mhz=freq_mhz,
            rssi_db=telemetry.get("rssi_db"),
            temperature_c=telemetry.get("temperature_c"),
            humidity_pct=telemetry.get("humidity_pct"),
            pressure_kpa=telemetry.get("pressure_kpa"),
            battery_ok=telemetry.get("battery_ok"),
            channel=telemetry.get("channel"),
        )

    def read_single(self, timeout_seconds: float = 30) -> IoTPacket | None:
        """Read a single packet with timeout.

        Useful for testing or one-shot reads.

        Args:
            timeout_seconds: Maximum time to wait.

        Returns:
            First decoded packet or None if timeout.
        """
        import time

        start = time.time()
        for packet in self.stream_packets():
            return packet

            if time.time() - start > timeout_seconds:
                break

        return None
