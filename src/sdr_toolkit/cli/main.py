"""CLI entry points for SDR Toolkit."""

from __future__ import annotations

import argparse
import logging
import sys

from sdr_toolkit.apps.am_radio import AMRadio
from sdr_toolkit.apps.fm_radio import FMRadio
from sdr_toolkit.apps.recorder import SignalRecorder
from sdr_toolkit.apps.scanner import SpectrumScanner
from sdr_toolkit.core.config import FM_BAND_END_MHZ, FM_BAND_START_MHZ

# Aircraft band constants
AIRCRAFT_BAND_START_MHZ = 118.0
AIRCRAFT_BAND_END_MHZ = 137.0


def setup_logging(verbose: bool) -> None:
    """Configure logging based on verbosity."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )


def fm_radio() -> None:
    """FM Radio CLI entry point."""
    parser = argparse.ArgumentParser(
        description="FM Radio - Listen to FM broadcast stations"
    )
    parser.add_argument(
        "-f",
        "--freq",
        type=float,
        default=100.1,
        help="Station frequency in MHz (default: 100.1)",
    )
    parser.add_argument(
        "-g",
        "--gain",
        type=str,
        default="auto",
        help="Gain in dB or 'auto' (default: auto)",
    )
    parser.add_argument(
        "-d",
        "--duration",
        type=float,
        default=None,
        help="Duration in seconds (default: indefinite)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--device",
        type=int,
        default=0,
        help="SDR device index (default: 0)",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    # Parse gain
    gain: float | str
    if args.gain == "auto":
        gain = "auto"
    else:
        try:
            gain = float(args.gain)
        except ValueError:
            print(f"Error: Invalid gain value: {args.gain}", file=sys.stderr)
            sys.exit(1)

    print(f"FM Radio - Tuning to {args.freq} MHz")
    print("Press Ctrl+C to stop\n")

    try:
        radio = FMRadio(
            freq_mhz=args.freq,
            gain=gain,
            device_index=args.device,
        )
        radio.play(duration=args.duration)
    except KeyboardInterrupt:
        print("\nStopped")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def am_radio() -> None:
    """AM Radio CLI entry point (aircraft band)."""
    parser = argparse.ArgumentParser(
        description="AM Radio - Listen to AM signals (aircraft band, etc.)"
    )
    parser.add_argument(
        "-f",
        "--freq",
        type=float,
        default=119.1,
        help="Frequency in MHz (default: 119.1 JFK Tower)",
    )
    parser.add_argument(
        "-g",
        "--gain",
        type=str,
        default="auto",
        help="Gain in dB or 'auto' (default: auto)",
    )
    parser.add_argument(
        "-d",
        "--duration",
        type=float,
        default=None,
        help="Duration in seconds (default: indefinite)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--device",
        type=int,
        default=0,
        help="SDR device index (default: 0)",
    )
    parser.add_argument(
        "--aircraft",
        action="store_true",
        help="Show common NYC aircraft frequencies",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    if args.aircraft:
        print("NYC Area Aircraft Frequencies:")
        print("-" * 40)
        print("  119.1 MHz : JFK Tower")
        print("  118.7 MHz : LGA Tower")
        print("  118.3 MHz : EWR Tower")
        print("  119.5 MHz : TEB Tower")
        print("  121.5 MHz : Emergency")
        print("  125.95 MHz: NY Approach/Departure")
        print("  128.55 MHz: NY ARTCC")
        print()

    # Parse gain
    gain: float | str
    if args.gain == "auto":
        gain = "auto"
    else:
        try:
            gain = float(args.gain)
        except ValueError:
            print(f"Error: Invalid gain value: {args.gain}", file=sys.stderr)
            sys.exit(1)

    print(f"AM Radio - Tuning to {args.freq} MHz")
    if AIRCRAFT_BAND_START_MHZ <= args.freq <= AIRCRAFT_BAND_END_MHZ:
        print("(Aircraft band)")
    print("Press Ctrl+C to stop\n")

    try:
        radio = AMRadio(
            freq_mhz=args.freq,
            gain=gain,
            device_index=args.device,
        )
        radio.play(duration=args.duration)
    except KeyboardInterrupt:
        print("\nStopped")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def scanner() -> None:
    """Spectrum Scanner CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Spectrum Scanner - Find signals in frequency range"
    )
    parser.add_argument(
        "-s",
        "--start",
        type=float,
        default=FM_BAND_START_MHZ,
        help=f"Start frequency in MHz (default: {FM_BAND_START_MHZ})",
    )
    parser.add_argument(
        "-e",
        "--end",
        type=float,
        default=FM_BAND_END_MHZ,
        help=f"End frequency in MHz (default: {FM_BAND_END_MHZ})",
    )
    parser.add_argument(
        "--step",
        type=float,
        default=200,
        help="Step size in kHz (default: 200)",
    )
    parser.add_argument(
        "-t",
        "--threshold",
        type=float,
        default=-30,
        help="Detection threshold in dB (default: -30)",
    )
    parser.add_argument(
        "-g",
        "--gain",
        type=str,
        default="auto",
        help="Gain in dB or 'auto' (default: auto)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--device",
        type=int,
        default=0,
        help="SDR device index (default: 0)",
    )
    parser.add_argument(
        "--fm",
        action="store_true",
        help="Quick scan of FM broadcast band",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    # Parse gain
    gain: float | str
    if args.gain == "auto":
        gain = "auto"
    else:
        try:
            gain = float(args.gain)
        except ValueError:
            print(f"Error: Invalid gain value: {args.gain}", file=sys.stderr)
            sys.exit(1)

    if args.fm:
        print("Scanning FM broadcast band (87.5 - 108 MHz)...")
        start_freq = FM_BAND_START_MHZ
        end_freq = FM_BAND_END_MHZ
    else:
        print(f"Scanning {args.start} - {args.end} MHz...")
        start_freq = args.start
        end_freq = args.end

    try:
        scanner_instance = SpectrumScanner(
            gain=gain,
            threshold_db=args.threshold,
            device_index=args.device,
        )

        result = scanner_instance.scan(
            start_freq * 1e6,
            end_freq * 1e6,
            step_hz=args.step * 1e3,
        )

        print(f"\nScan completed in {result.scan_time_seconds:.1f} seconds")
        print(f"Noise floor: {result.noise_floor_db:.1f} dB")
        print(f"Signals found: {len(result.peaks)}\n")

        if result.peaks:
            print("Detected signals:")
            print("-" * 40)
            for peak in result.peaks[:20]:  # Show top 20
                print(f"  {peak.frequency_hz/1e6:8.3f} MHz : {peak.power_db:6.1f} dB")
            if len(result.peaks) > 20:
                print(f"  ... and {len(result.peaks) - 20} more")

    except KeyboardInterrupt:
        print("\nScan cancelled")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def recorder() -> None:
    """Signal Recorder CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Signal Recorder - Record IQ samples or FM audio"
    )
    parser.add_argument(
        "-f",
        "--freq",
        type=float,
        required=True,
        help="Center frequency in MHz",
    )
    parser.add_argument(
        "-d",
        "--duration",
        type=float,
        default=10,
        help="Recording duration in seconds (default: 10)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=".",
        help="Output directory or file (default: current directory)",
    )
    parser.add_argument(
        "-g",
        "--gain",
        type=str,
        default="auto",
        help="Gain in dB or 'auto' (default: auto)",
    )
    parser.add_argument(
        "--fm",
        action="store_true",
        help="Record demodulated FM audio (WAV) instead of IQ",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--device",
        type=int,
        default=0,
        help="SDR device index (default: 0)",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    # Parse gain
    gain: float | str
    if args.gain == "auto":
        gain = "auto"
    else:
        try:
            gain = float(args.gain)
        except ValueError:
            print(f"Error: Invalid gain value: {args.gain}", file=sys.stderr)
            sys.exit(1)

    try:
        recorder_instance = SignalRecorder(
            center_freq_mhz=args.freq,
            gain=gain,
            device_index=args.device,
        )

        if args.fm:
            print(f"Recording FM audio at {args.freq} MHz for {args.duration}s...")
            output_path = args.output
            if not output_path.endswith(".wav"):
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"{output_path}/fm_{args.freq}MHz_{timestamp}.wav"

            result = recorder_instance.record_fm_audio(
                duration=args.duration,
                output_path=output_path,
            )
        else:
            print(f"Recording IQ at {args.freq} MHz for {args.duration}s...")
            result = recorder_instance.record_iq(
                duration=args.duration,
                output_dir=args.output,
            )

        print(f"\nRecording saved to: {result.path}")
        print(f"Duration: {result.duration_seconds:.1f} seconds")
        print(f"Samples: {result.num_samples:,}")

    except KeyboardInterrupt:
        print("\nRecording cancelled")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    # Default to fm_radio if run directly
    fm_radio()
