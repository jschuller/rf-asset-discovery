"""Discover IoT devices on 433 MHz ISM band."""

import sys

from sdr_toolkit.decoders.iot import DeviceRegistry, RTL433Decoder, check_rtl433_available


def main(freq: str = "433.92M", duration: int = 60) -> int:
    if not check_rtl433_available():
        print("Error: rtl_433 not found. Install: brew install rtl_433")
        return 1

    frequencies = [f.strip() for f in freq.split(",")]
    print(f"IoT Discovery: {', '.join(frequencies)} for {duration}s (Ctrl+C to stop)")

    registry = DeviceRegistry()

    try:
        with RTL433Decoder(frequencies=frequencies, duration_seconds=duration or None) as decoder:
            for packet in decoder.stream_packets():
                device = registry.process_packet(packet)
                info = f"[{device.protocol_type.value:15}] {device.model}"
                if packet.temperature_c is not None:
                    info += f" {packet.temperature_c:.1f}C"
                if packet.humidity_pct is not None:
                    info += f" {packet.humidity_pct}%"
                print(info)
    except KeyboardInterrupt:
        print("\nStopped")

    stats = registry.get_stats()
    print(f"\nPackets: {stats['total_packets']} | Devices: {stats['total_devices']}")
    for proto, count in stats.get("devices_by_protocol", {}).items():
        print(f"  {proto}: {count}")

    return 0


if __name__ == "__main__":
    f = sys.argv[1] if len(sys.argv) > 1 else "433.92M"
    d = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    sys.exit(main(f, d))
