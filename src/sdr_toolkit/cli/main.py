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
    parser.add_argument(
        "--aircraft",
        action="store_true",
        help="Quick scan of aircraft band (118-137 MHz)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        dest="show_all",
        help="Show all detected signals (no limit)",
    )
    parser.add_argument(
        "--plain",
        action="store_true",
        help="Use plain text output (no rich formatting)",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    # Try to use rich display
    use_rich = not args.plain
    if use_rich:
        try:
            from sdr_toolkit.ui import display_scan_results, print_banner
        except ImportError:
            use_rich = False

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
        start_freq = FM_BAND_START_MHZ
        end_freq = FM_BAND_END_MHZ
        band_name = "FM Broadcast"
    elif args.aircraft:
        start_freq = AIRCRAFT_BAND_START_MHZ
        end_freq = AIRCRAFT_BAND_END_MHZ
        band_name = "Aircraft"
    else:
        start_freq = args.start
        end_freq = args.end
        band_name = None

    if use_rich:
        title = f"Scanning {start_freq} - {end_freq} MHz"
        subtitle = f"({band_name})" if band_name else None
        print_banner(title, subtitle)
    else:
        if band_name:
            print(f"Scanning {band_name} band ({start_freq} - {end_freq} MHz)...")
        else:
            print(f"Scanning {start_freq} - {end_freq} MHz...")

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

        if use_rich:
            display_scan_results(result, show_all=args.show_all)
        else:
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


def iot_scan() -> None:
    """IoT Device Scanner CLI entry point."""
    parser = argparse.ArgumentParser(
        description="IoT Scanner - Discover IoT devices using rtl_433"
    )
    parser.add_argument(
        "-f",
        "--freq",
        type=str,
        action="append",
        default=None,
        help="Frequency to scan (e.g., 433.92M). Can specify multiple.",
    )
    parser.add_argument(
        "-d",
        "--duration",
        type=int,
        default=0,
        help="Duration in seconds (default: 0 = indefinite)",
    )
    parser.add_argument(
        "-H",
        "--hop",
        type=int,
        default=30,
        help="Frequency hop time in seconds (default: 30)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Save device registry to JSON file",
    )
    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help="Store discoveries in UnifiedDB",
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
        help="Show all decoded packets",
    )
    parser.add_argument(
        "--device",
        type=int,
        default=0,
        help="SDR device index (default: 0)",
    )
    parser.add_argument(
        "--plain",
        action="store_true",
        help="Use plain text output (no rich formatting)",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    # Import IoT modules
    try:
        from sdr_toolkit.decoders.iot import (
            DeviceRegistry,
            RTL433Decoder,
            RTL433Error,
            check_rtl433_available,
        )
    except ImportError as e:
        print(f"Error: IoT module not available: {e}", file=sys.stderr)
        sys.exit(1)

    # Check rtl_433 availability
    if not check_rtl433_available():
        print(
            "Error: rtl_433 not found. Install with:\n"
            "  macOS: brew install rtl_433\n"
            "  Linux: apt install rtl-433",
            file=sys.stderr,
        )
        sys.exit(1)

    # Default frequencies
    frequencies = args.freq or ["433.92M"]

    # Parse gain
    gain: str | int
    if args.gain == "auto":
        gain = "auto"
    else:
        try:
            gain = int(args.gain)
        except ValueError:
            print(f"Error: Invalid gain value: {args.gain}", file=sys.stderr)
            sys.exit(1)

    # Setup database if requested
    db = None
    if args.db:
        try:
            from pathlib import Path

            from sdr_toolkit.storage import UnifiedDB

            db = UnifiedDB(Path(args.db))
            db.connect()
        except Exception as e:
            print(f"Warning: Could not open database: {e}", file=sys.stderr)

    # Create registry
    registry = DeviceRegistry(db=db)
    if db:
        scan_id = db.start_scan_session("iot", {"frequencies": frequencies})
        registry.set_scan_id(scan_id)

    print(f"IoT Scanner - Monitoring {', '.join(frequencies)}")
    print("Press Ctrl+C to stop\n")

    try:
        with RTL433Decoder(
            frequencies=frequencies,
            hop_time_seconds=args.hop,
            device_index=args.device,
            gain=gain,
        ) as decoder:
            import time

            start_time = time.time()
            last_summary = start_time

            for packet in decoder.stream_packets():
                device = registry.process_packet(packet)

                if args.verbose:
                    print(
                        f"[{packet.protocol_type.value}] {device.model} "
                        f"({device.device_id}) - packets: {device.packet_count}"
                    )

                # Print summary every 10 seconds
                if time.time() - last_summary >= 10:
                    stats = registry.get_stats()
                    print(
                        f"\n--- Devices: {stats['total_devices']} | "
                        f"Packets: {stats['total_packets']} ---\n"
                    )
                    last_summary = time.time()

                # Check duration
                if args.duration > 0 and time.time() - start_time >= args.duration:
                    print(f"\nDuration ({args.duration}s) reached.")
                    break

    except RTL433Error as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nStopped")
    finally:
        # Print final summary
        print("\n" + "=" * 50)
        print("IoT Scan Summary")
        print("=" * 50)

        stats = registry.get_stats()
        print(f"Total devices: {stats['total_devices']}")
        print(f"Total packets: {stats['total_packets']}")

        if stats["devices_by_protocol"]:
            print("\nBy protocol:")
            for proto, count in stats["devices_by_protocol"].items():
                print(f"  {proto}: {count}")

        devices = registry.get_all_devices()
        if devices:
            print("\nDiscovered devices:")
            print("-" * 50)
            for device in devices[:20]:
                print(
                    f"  {device.model} ({device.device_id})\n"
                    f"    Protocol: {device.protocol_type.value}\n"
                    f"    Packets: {device.packet_count}"
                )
                if device.last_temperature_c is not None:
                    print(f"    Temp: {device.last_temperature_c:.1f}C")
                if device.last_humidity_pct is not None:
                    print(f"    Humidity: {device.last_humidity_pct:.0f}%")

            if len(devices) > 20:
                print(f"  ... and {len(devices) - 20} more")

        # Save output if requested
        if args.output:
            from pathlib import Path

            registry.to_json(Path(args.output))
            print(f"\nDevices saved to: {args.output}")

        # Close database
        if db:
            db.end_scan_session(scan_id, stats)
            db.close()
            print(f"Results stored in: {args.db}")


def spectrum_watch() -> None:
    """Spectrum Watch CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Spectrum Watch - Autonomous monitoring with alerts"
    )
    parser.add_argument(
        "intent",
        nargs="?",
        default=None,
        help="Natural language watch description (e.g., 'Watch aircraft band')",
    )
    parser.add_argument(
        "-b",
        "--band",
        type=str,
        default=None,
        help="Predefined band: fm, aircraft, marine, amateur, weather",
    )
    parser.add_argument(
        "-f",
        "--freq",
        type=float,
        default=None,
        help="Specific frequency to watch in MHz",
    )
    parser.add_argument(
        "-t",
        "--threshold",
        type=float,
        default=-30,
        help="Detection threshold in dB (default: -30)",
    )
    parser.add_argument(
        "--ntfy",
        type=str,
        default=None,
        help="ntfy.sh topic for push notifications",
    )
    parser.add_argument(
        "-i",
        "--interval",
        type=float,
        default=5.0,
        help="Scan interval in seconds (default: 5)",
    )
    parser.add_argument(
        "--baseline",
        type=float,
        default=60.0,
        help="Baseline duration in seconds (default: 60)",
    )
    parser.add_argument(
        "--baseline-scans",
        type=int,
        default=12,
        help="Number of baseline scans (default: 12)",
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

    # Import watch modules
    try:
        import asyncio

        from adws.adw_spectrum_watch import SpectrumWatch, run_watch_cli
        from adws.adw_modules.watch_config import (
            FrequencyBand,
            WatchConfig,
            AlertCondition,
            create_watch_for_band,
            create_watch_for_frequency,
            parse_natural_language,
        )
    except ImportError as e:
        print(
            f"Error: Watch modules not available: {e}\n"
            "Make sure pydantic and httpx are installed.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Build configuration
    config: WatchConfig | None = None

    if args.intent:
        # Natural language parsing
        config = parse_natural_language(args.intent)
        config.threshold_db = args.threshold

    elif args.band:
        # Predefined band
        band_map = {
            "fm": FrequencyBand.FM_BROADCAST,
            "aircraft": FrequencyBand.AIRCRAFT_VHF,
            "aviation": FrequencyBand.AIRCRAFT_VHF,
            "marine": FrequencyBand.MARINE_VHF,
            "amateur": FrequencyBand.AMATEUR_2M,
            "ham": FrequencyBand.AMATEUR_2M,
            "2m": FrequencyBand.AMATEUR_2M,
            "70cm": FrequencyBand.AMATEUR_70CM,
            "weather": FrequencyBand.NOAA_WEATHER,
            "noaa": FrequencyBand.NOAA_WEATHER,
            "adsb": FrequencyBand.ADSB,
        }

        band = band_map.get(args.band.lower())
        if band is None:
            print(
                f"Error: Unknown band '{args.band}'. "
                f"Options: {', '.join(band_map.keys())}",
                file=sys.stderr,
            )
            sys.exit(1)

        config = create_watch_for_band(band, threshold_db=args.threshold)

    elif args.freq:
        # Specific frequency
        config = create_watch_for_frequency(
            args.freq * 1e6,
            threshold_db=args.threshold,
        )

    else:
        # Default to FM band
        print("No watch target specified, defaulting to FM broadcast band")
        config = create_watch_for_band(
            FrequencyBand.FM_BROADCAST,
            threshold_db=args.threshold,
        )

    # Apply common settings
    config.scan_interval_seconds = args.interval
    config.baseline_scans = args.baseline_scans

    # Add ntfy notification if specified
    if args.ntfy:
        config.notifications.append(f"ntfy:{args.ntfy}")

    # Run the watch
    try:
        asyncio.run(run_watch_cli(config, ntfy_topic=args.ntfy))
    except KeyboardInterrupt:
        print("\nWatch stopped")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    # Default to fm_radio if run directly
    fm_radio()
