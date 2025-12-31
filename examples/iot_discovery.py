#!/usr/bin/env python3
"""IoT device discovery example - discover 433 MHz devices.

This example demonstrates how to discover and track IoT devices
using rtl_433 on common ISM bands (433.92 MHz, 315 MHz, 868 MHz).

Usage:
    python examples/iot_discovery.py [--freq FREQ] [--duration SECONDS]

Example:
    # Discover devices on 433.92 MHz for 5 minutes
    python examples/iot_discovery.py --freq 433.92M --duration 300

    # Multi-frequency hopping (weather stations + TPMS)
    python examples/iot_discovery.py --freq 433.92M,315M --duration 600

    # Persist discovered devices to database
    python examples/iot_discovery.py --duration 300 --db data/unified.duckdb

Requirements:
    - rtl_433 installed: brew install rtl_433 (macOS) or apt install rtl-433
    - RTL-SDR device connected
    - On Apple Silicon: export DYLD_LIBRARY_PATH=/opt/homebrew/lib

Device Types Detected:
    - Weather stations (Acurite, Oregon, LaCrosse, Ambient)
    - TPMS sensors (tire pressure monitoring)
    - Temperature/humidity sensors
    - Door/window sensors
    - Motion detectors
    - Smoke detectors
    - Generic OOK remotes
"""

import argparse
import sys
from pathlib import Path

from sdr_toolkit.decoders.iot import (
    DeviceRegistry,
    RTL433Decoder,
    check_rtl433_available,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover IoT devices on ISM bands")
    parser.add_argument(
        "--freq",
        type=str,
        default="433.92M",
        help="Frequency or frequencies (comma-separated, e.g., 433.92M,315M)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Discovery duration in seconds (default: 60, 0 for continuous)",
    )
    parser.add_argument(
        "--gain",
        type=int,
        default=None,
        help="Receiver gain in dB (default: auto)",
    )
    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help="Path to DuckDB database for persistence",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON file for device registry",
    )
    args = parser.parse_args()

    # Check rtl_433 availability
    if not check_rtl433_available():
        print("Error: rtl_433 not found in PATH")
        print("Install with: brew install rtl_433 (macOS) or apt install rtl-433")
        return 1

    # Parse frequencies
    frequencies = [f.strip() for f in args.freq.split(",")]

    print("IoT Device Discovery")
    print("=" * 45)
    print(f"Frequencies: {', '.join(frequencies)}")
    print(f"Duration: {args.duration if args.duration > 0 else 'continuous'} seconds")
    print("Press Ctrl+C to stop")
    print()

    registry = DeviceRegistry()

    try:
        with RTL433Decoder(
            frequencies=frequencies,
            duration_seconds=args.duration if args.duration > 0 else None,
            gain=args.gain,
        ) as decoder:
            print("Listening for devices...")
            print()

            for packet in decoder.stream_packets():
                device = registry.process_packet(packet)

                # Print device info
                info = f"[{device.protocol_type.value:15}] {device.model}"
                if packet.temperature_c is not None:
                    info += f" | Temp: {packet.temperature_c:.1f}C"
                if packet.humidity_pct is not None:
                    info += f" | Humidity: {packet.humidity_pct}%"
                if packet.pressure_kpa is not None:
                    info += f" | Pressure: {packet.pressure_kpa:.1f} kPa"

                print(info)

    except KeyboardInterrupt:
        print("\nStopped by user")

    # Print summary
    print()
    print("=" * 45)
    print("Discovery Summary")
    print("=" * 45)
    stats = registry.get_stats()
    print(f"Total packets: {stats['total_packets']}")
    print(f"Unique devices: {stats['total_devices']}")
    print()

    if stats["devices_by_protocol"]:
        print("Devices by protocol:")
        for protocol, count in sorted(stats["devices_by_protocol"].items()):
            print(f"  {protocol}: {count}")
        print()

    # List all devices
    devices = registry.get_all_devices()
    if devices:
        print("Discovered devices:")
        for device in devices:
            print(f"  - {device.device_id} ({device.packet_count} packets)")

    # Save registry to JSON if requested
    if args.output:
        output_path = Path(args.output)
        registry.to_json(output_path)
        print(f"\nRegistry saved to: {output_path}")

    # Sync to database if requested
    if args.db:
        try:
            from sdr_toolkit.storage import UnifiedDB

            db_path = Path(args.db)
            with UnifiedDB(db_path) as db:
                inserted = registry.sync_to_db(db)
                print(f"\nSynced {inserted} devices to database: {db_path}")
        except ImportError:
            print("\nWarning: storage module not available, skipping database sync")
            print("Install with: pip install sdr-toolkit[storage]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
