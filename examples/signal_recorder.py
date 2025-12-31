#!/usr/bin/env python3
"""Signal recorder example - capture IQ samples to SigMF format.

This example records RF signals and saves them in SigMF format
for later analysis.

Usage:
    python examples/signal_recorder.py --freq FREQ_MHZ [--duration SECONDS]

Example:
    # Record FM station for 10 seconds
    python examples/signal_recorder.py --freq 101.9 --duration 10

    # Record NOAA weather for 30 seconds
    python examples/signal_recorder.py --freq 162.55 --duration 30

Requirements:
    - RTL-SDR device connected
    - On Apple Silicon: export DYLD_LIBRARY_PATH=/opt/homebrew/lib
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from sdr_toolkit.apps.recorder import SignalRecorder
from sdr_toolkit.io.sigmf import SigMFRecording
from sdr_toolkit.dsp.spectrum import compute_power_spectrum_hz, estimate_noise_floor


def main() -> int:
    parser = argparse.ArgumentParser(description="Record RF signal to SigMF")
    parser.add_argument(
        "--freq",
        type=float,
        required=True,
        help="Center frequency in MHz",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=10,
        help="Recording duration in seconds (default: 10)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./recordings",
        help="Output directory (default: ./recordings)",
    )
    parser.add_argument(
        "--gain",
        type=str,
        default="auto",
        help="Receiver gain in dB or 'auto' (default: auto)",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Analyze recording after capture",
    )
    args = parser.parse_args()

    # Create dated output directory
    today = datetime.now().strftime("%Y-%m-%d")
    output_dir = Path(args.output_dir) / today
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Recording {args.freq} MHz for {args.duration} seconds")
    print(f"Output directory: {output_dir}")
    print()

    try:
        # Record
        recorder = SignalRecorder(center_freq_mhz=args.freq, gain=args.gain)
        result = recorder.record_iq(
            duration=args.duration,
            output_dir=output_dir,
        )

        print("Recording complete!")
        print(f"  Path: {result.path}")
        print(f"  Duration: {result.duration_seconds:.1f} seconds")
        print(f"  Samples: {result.num_samples:,}")
        print(f"  Sample rate: {result.sample_rate / 1e6:.3f} MHz")

        # Calculate file size
        data_path = Path(str(result.path).replace("-meta", "-data"))
        if data_path.exists():
            size_mb = data_path.stat().st_size / 1024 / 1024
            print(f"  File size: {size_mb:.2f} MB")

        # Optional analysis
        if args.analyze:
            print()
            print("Analyzing recording...")

            meta_path = Path(str(result.path).replace("-data", "-meta"))
            recording = SigMFRecording.load(meta_path)
            samples = recording.to_numpy()

            # Compute spectrum
            freqs_hz, power_db = compute_power_spectrum_hz(
                samples[:65536],
                sample_rate=recording.sample_rate,
                center_freq=recording.center_frequency,
                fft_size=2048,
            )
            noise_floor = estimate_noise_floor(power_db)

            print(f"  Peak power: {power_db.max():.1f} dB")
            print(f"  Noise floor: {noise_floor:.1f} dB")
            print(f"  Dynamic range: {power_db.max() - noise_floor:.1f} dB")

            # Find peak frequency
            import numpy as np
            peak_idx = np.argmax(power_db)
            peak_freq_hz = freqs_hz[peak_idx]
            print(f"  Peak frequency: {peak_freq_hz / 1e6:.3f} MHz")

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
