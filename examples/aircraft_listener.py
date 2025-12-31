#!/usr/bin/env python3
"""Aircraft band listener example - monitor ATC communications.

This example demonstrates how to listen to aircraft communications
on the VHF airband (118-137 MHz) using AM demodulation.

Usage:
    python examples/aircraft_listener.py [--freq FREQ_MHZ] [--duration SECONDS]

Example:
    # Listen to JFK Tower
    python examples/aircraft_listener.py --freq 119.1 --duration 60

    # Listen to NY Approach
    python examples/aircraft_listener.py --freq 125.95 --duration 120

    # Show common frequencies
    python examples/aircraft_listener.py --list

Requirements:
    - RTL-SDR device connected
    - On Apple Silicon: export DYLD_LIBRARY_PATH=/opt/homebrew/lib

Note:
    Aircraft communications use AM modulation, not FM.
    This is different from FM broadcast radio.
"""

import argparse
import sys

from sdr_toolkit.apps.am_radio import AMRadio

# NYC Metro Area Aircraft Frequencies
NYC_AIRCRAFT_FREQUENCIES = {
    "JFK Tower": 119.1,
    "JFK Ground": 121.9,
    "LGA Tower": 118.7,
    "LGA Ground": 121.7,
    "EWR Tower": 118.3,
    "EWR Ground": 121.8,
    "TEB Tower": 119.5,
    "TEB Ground": 121.9,
    "NY Approach North": 125.95,
    "NY Approach South": 127.4,
    "NY Departure": 135.9,
    "NY ARTCC": 128.55,
    "Emergency": 121.5,
    "ATIS JFK": 128.725,
    "ATIS LGA": 125.95,
    "ATIS EWR": 115.1,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Listen to aircraft communications")
    parser.add_argument(
        "--freq",
        type=float,
        default=119.1,
        help="Frequency in MHz (default: 119.1 JFK Tower)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Listen duration in seconds (default: 60, 0 for continuous)",
    )
    parser.add_argument(
        "--gain",
        type=str,
        default="auto",
        help="Receiver gain in dB or 'auto' (default: auto)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List common NYC area frequencies",
    )
    args = parser.parse_args()

    if args.list:
        print("NYC Metro Area Aircraft Frequencies")
        print("=" * 45)
        print()
        print("Towers (local control):")
        for name, freq in NYC_AIRCRAFT_FREQUENCIES.items():
            if "Tower" in name:
                print(f"  {freq:7.3f} MHz : {name}")
        print()
        print("Ground Control:")
        for name, freq in NYC_AIRCRAFT_FREQUENCIES.items():
            if "Ground" in name:
                print(f"  {freq:7.3f} MHz : {name}")
        print()
        print("Approach/Departure/ARTCC:")
        for name, freq in NYC_AIRCRAFT_FREQUENCIES.items():
            if any(x in name for x in ["Approach", "Departure", "ARTCC"]):
                print(f"  {freq:7.3f} MHz : {name}")
        print()
        print("Other:")
        for name, freq in NYC_AIRCRAFT_FREQUENCIES.items():
            if any(x in name for x in ["Emergency", "ATIS"]):
                print(f"  {freq:7.3f} MHz : {name}")
        print()
        return 0

    # Find if this is a known frequency
    freq_name = None
    for name, freq in NYC_AIRCRAFT_FREQUENCIES.items():
        if abs(freq - args.freq) < 0.01:
            freq_name = name
            break

    print(f"Aircraft Band Listener")
    print(f"Frequency: {args.freq} MHz", end="")
    if freq_name:
        print(f" ({freq_name})")
    else:
        print()
    print(f"Duration: {args.duration if args.duration > 0 else 'continuous'} seconds")
    print("Press Ctrl+C to stop")
    print()

    try:
        radio = AMRadio(freq_mhz=args.freq, gain=args.gain)

        if args.duration > 0:
            radio.play(duration=args.duration)
        else:
            radio.play()  # Continuous until Ctrl+C

        return 0

    except KeyboardInterrupt:
        print("\nStopped by user")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
