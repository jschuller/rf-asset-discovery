#!/usr/bin/env python3
"""Simple FM radio listener example.

This example demonstrates how to tune to an FM station
and listen using the sdr-toolkit.

Usage:
    python examples/fm_listener.py [--freq FREQ_MHZ] [--duration SECONDS]

Example:
    python examples/fm_listener.py --freq 101.9 --duration 30

Requirements:
    - RTL-SDR device connected
    - On Apple Silicon: export DYLD_LIBRARY_PATH=/opt/homebrew/lib
"""

import argparse
import sys

from sdr_toolkit.apps.fm_radio import FMRadio


def main() -> int:
    parser = argparse.ArgumentParser(description="Listen to FM radio")
    parser.add_argument(
        "--freq",
        type=float,
        default=101.9,
        help="FM station frequency in MHz (default: 101.9 WFAN-FM NYC)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=30,
        help="Listen duration in seconds (default: 30, 0 for continuous)",
    )
    parser.add_argument(
        "--gain",
        type=str,
        default="auto",
        help="Receiver gain in dB or 'auto' (default: auto)",
    )
    args = parser.parse_args()

    print(f"Tuning to {args.freq} MHz...")
    print(f"Duration: {args.duration if args.duration > 0 else 'continuous'} seconds")
    print("Press Ctrl+C to stop")
    print()

    try:
        radio = FMRadio(freq_mhz=args.freq, gain=args.gain)

        if args.duration > 0:
            radio.listen(duration=args.duration)
        else:
            radio.listen()  # Continuous until Ctrl+C

        return 0

    except KeyboardInterrupt:
        print("\nStopped by user")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
