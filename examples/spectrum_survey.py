#!/usr/bin/env python3
"""Spectrum survey example - scan and log signals.

This example scans a frequency range and reports all detected signals,
sorted by signal strength.

Usage:
    python examples/spectrum_survey.py [--start START] [--end END] [--threshold DB]

Example:
    # Scan FM broadcast band
    python examples/spectrum_survey.py --start 87.5 --end 108.0

    # Scan aircraft band with lower threshold
    python examples/spectrum_survey.py --start 118 --end 137 --threshold -40

Requirements:
    - RTL-SDR device connected
    - On Apple Silicon: export DYLD_LIBRARY_PATH=/opt/homebrew/lib
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from sdr_toolkit.apps.scanner import SpectrumScanner


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan spectrum and log signals")
    parser.add_argument(
        "--start",
        type=float,
        default=87.5,
        help="Start frequency in MHz (default: 87.5)",
    )
    parser.add_argument(
        "--end",
        type=float,
        default=108.0,
        help="End frequency in MHz (default: 108.0)",
    )
    parser.add_argument(
        "--step",
        type=float,
        default=200,
        help="Step size in kHz (default: 200)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=-30,
        help="Detection threshold in dB (default: -30)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON file (optional)",
    )
    args = parser.parse_args()

    print(f"Scanning {args.start} - {args.end} MHz")
    print(f"Step: {args.step} kHz, Threshold: {args.threshold} dB")
    print()

    try:
        scanner = SpectrumScanner(threshold_db=args.threshold)
        result = scanner.scan(
            args.start * 1e6,
            args.end * 1e6,
            step_hz=args.step * 1e3,
        )

        print(f"Scan complete in {result.scan_time_seconds:.1f} seconds")
        print(f"Noise floor: {result.noise_floor_db:.1f} dB")
        print(f"Signals found: {len(result.peaks)}")
        print()

        # Sort by power
        sorted_peaks = sorted(result.peaks, key=lambda p: p.power_db, reverse=True)

        print("Signals detected (sorted by power):")
        print("-" * 50)
        print(f"{'Rank':>4}  {'Frequency':>10}  {'Power':>8}  {'Above Noise':>12}")
        print("-" * 50)

        for i, peak in enumerate(sorted_peaks[:25], 1):
            freq_mhz = peak.frequency_hz / 1e6
            above_noise = peak.power_db - result.noise_floor_db
            print(f"{i:4}  {freq_mhz:10.3f} MHz  {peak.power_db:+7.1f} dB  {above_noise:+11.1f} dB")

        if len(sorted_peaks) > 25:
            print(f"... and {len(sorted_peaks) - 25} more signals")

        # Save to JSON if requested
        if args.output:
            output_data = {
                "timestamp": datetime.now().isoformat(),
                "scan_range": {
                    "start_mhz": args.start,
                    "end_mhz": args.end,
                    "step_khz": args.step,
                },
                "results": {
                    "scan_time_seconds": result.scan_time_seconds,
                    "noise_floor_db": result.noise_floor_db,
                    "num_signals": len(result.peaks),
                },
                "signals": [
                    {
                        "frequency_mhz": p.frequency_hz / 1e6,
                        "power_db": p.power_db,
                    }
                    for p in sorted_peaks
                ],
            }

            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w") as f:
                json.dump(output_data, f, indent=2)

            print()
            print(f"Results saved to: {output_path}")

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
