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
    """Spectrum Scanner CLI entry point.

    Survey-first: All scans create ad-hoc surveys and route signals
    through the unified signals table.
    """
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
    parser.add_argument(
        "--db",
        type=str,
        default="data/unified.duckdb",
        help="DuckDB path (default: data/unified.duckdb)",
    )
    parser.add_argument(
        "-l",
        "--location",
        type=str,
        default=None,
        help="Location name (default: hostname)",
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

    # Survey-first: Setup database and create ad-hoc survey
    from datetime import datetime
    from pathlib import Path

    from sdr_toolkit.storage import UnifiedDB
    from sdr_toolkit.apps.survey.manager import SurveyManager

    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    scan_id = None
    survey = None

    try:
        with UnifiedDB(db_path) as db:
            manager = SurveyManager(db)

            # Create ad-hoc survey for this scan
            survey_name = f"Scan {band_name or 'custom'} {datetime.now():%Y%m%d_%H%M}"
            survey = manager.create_adhoc_survey(
                name=survey_name,
                start_hz=start_freq * 1e6,
                end_hz=end_freq * 1e6,
                location_name=args.location,
            )

            # Start scan session for audit trail
            scan_id = db.start_scan_session(
                "rf_spectrum",
                {
                    "start_freq_hz": start_freq * 1e6,
                    "end_freq_hz": end_freq * 1e6,
                    "step_hz": args.step * 1e3,
                    "threshold_db": args.threshold,
                    "gain": str(gain),
                    "band_name": band_name,
                    "survey_id": survey.survey_id,
                },
            )

            # Get the segment
            segment = manager.get_next_segment(survey.survey_id)
            if segment:
                manager.start_segment(segment.segment_id, scan_id)

            # Execute scan
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

            # Record signals to unified signals table
            for peak in result.peaks:
                manager.record_signal(
                    survey_id=survey.survey_id,
                    segment_id=segment.segment_id if segment else None,
                    frequency_hz=peak.frequency_hz,
                    power_db=peak.power_db,
                    scan_id=scan_id,
                )

            # Complete segment and survey
            if segment:
                manager.complete_segment(
                    segment.segment_id,
                    signals_found=len(result.peaks),
                    noise_floor_db=result.noise_floor_db,
                    scan_time_seconds=result.scan_time_seconds,
                )

            # End scan session
            db.end_scan_session(
                scan_id,
                {
                    "signals_found": len(result.peaks),
                    "noise_floor_db": result.noise_floor_db,
                    "scan_time_seconds": result.scan_time_seconds,
                },
            )

            print(f"\nResults stored in: {args.db}")
            print(f"  Survey ID: {survey.survey_id}")
            print(f"  Signals: {len(result.peaks)}")

    except KeyboardInterrupt:
        print("\nScan cancelled")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def recorder() -> None:
    """Signal Recorder CLI entry point.

    Survey-first: All recordings create ad-hoc surveys and route signals
    through the unified signals table with SigMF path linking.
    """
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
        default="recordings",
        help="Output directory (default: recordings)",
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
    parser.add_argument(
        "--db",
        type=str,
        default="data/unified.duckdb",
        help="DuckDB path (default: data/unified.duckdb)",
    )
    parser.add_argument(
        "-l",
        "--location",
        type=str,
        default=None,
        help="Location name (default: hostname)",
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

    # Survey-first: Setup database and create ad-hoc survey
    from datetime import datetime
    from pathlib import Path

    from sdr_toolkit.storage import UnifiedDB
    from sdr_toolkit.apps.survey.manager import SurveyManager

    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Ensure output directory exists
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        with UnifiedDB(db_path) as db:
            manager = SurveyManager(db)

            # Create ad-hoc survey for this recording
            record_type = "FM audio" if args.fm else "IQ"
            survey_name = f"Record {record_type} {args.freq}MHz {datetime.now():%Y%m%d_%H%M}"
            survey = manager.create_adhoc_survey(
                name=survey_name,
                start_hz=args.freq * 1e6 - 0.5e6,  # ±500 kHz around center
                end_hz=args.freq * 1e6 + 0.5e6,
                location_name=args.location,
            )

            # Start scan session for audit trail
            scan_id = db.start_scan_session(
                "recording",
                {
                    "center_freq_hz": args.freq * 1e6,
                    "duration_seconds": args.duration,
                    "gain": str(gain),
                    "type": "fm_audio" if args.fm else "iq",
                    "survey_id": survey.survey_id,
                },
            )

            # Get the segment
            segment = manager.get_next_segment(survey.survey_id)
            if segment:
                manager.start_segment(segment.segment_id, scan_id)

            # Execute recording
            recorder_instance = SignalRecorder(
                center_freq_mhz=args.freq,
                gain=gain,
                device_index=args.device,
            )

            if args.fm:
                print(f"Recording FM audio at {args.freq} MHz for {args.duration}s...")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = str(output_dir / f"fm_{args.freq}MHz_{timestamp}.wav")

                result = recorder_instance.record_fm_audio(
                    duration=args.duration,
                    output_path=output_path,
                )
            else:
                print(f"Recording IQ at {args.freq} MHz for {args.duration}s...")
                result = recorder_instance.record_iq(
                    duration=args.duration,
                    output_dir=str(output_dir),
                )

            print(f"\nRecording saved to: {result.path}")
            print(f"Duration: {result.duration_seconds:.1f} seconds")
            print(f"Samples: {result.num_samples:,}")

            # Record signal to unified signals table with SigMF path
            signal = manager.record_signal(
                survey_id=survey.survey_id,
                segment_id=segment.segment_id if segment else None,
                frequency_hz=args.freq * 1e6,
                power_db=0.0,  # Not measured during recording
                scan_id=scan_id,
            )

            # Update signal with SigMF path
            db.conn.execute(
                "UPDATE signals SET sigmf_path = ? WHERE signal_id = ?",
                [str(result.path), signal.signal_id],
            )

            # Complete segment and survey
            if segment:
                manager.complete_segment(
                    segment.segment_id,
                    signals_found=1,
                    scan_time_seconds=result.duration_seconds,
                )

            # End scan session
            db.end_scan_session(
                scan_id,
                {
                    "output_path": str(result.path),
                    "duration_seconds": result.duration_seconds,
                    "num_samples": result.num_samples,
                },
            )

            print(f"\nRecording indexed in: {args.db}")
            print(f"  Survey ID: {survey.survey_id}")
            print(f"  Signal ID: {signal.signal_id}")

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
        "--survey-id",
        type=str,
        default=None,
        help="Link discoveries to a survey (requires --db)",
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

    # Validate survey-id requires db
    if args.survey_id and not args.db:
        print("Error: --survey-id requires --db", file=sys.stderr)
        sys.exit(1)

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
        scan_id = db.start_scan_session(
            "iot",
            {
                "frequencies": frequencies,
                "survey_id": args.survey_id,
            },
        )
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


def spectrum_survey() -> None:
    """Spectrum Survey CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Spectrum Survey - Comprehensive frequency coverage with persistence"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Create new survey
    create_parser = subparsers.add_parser("create", help="Create a new survey")
    create_parser.add_argument(
        "--name",
        type=str,
        required=True,
        help="Survey name/description",
    )
    create_parser.add_argument(
        "--full",
        action="store_true",
        help="Full 24-1766 MHz coverage with gap filling (default)",
    )
    create_parser.add_argument(
        "--priority-only",
        action="store_true",
        help="Only scan priority bands (faster, no gaps)",
    )
    create_parser.add_argument(
        "-s",
        "--start",
        type=float,
        default=24.0,
        help="Start frequency in MHz (default: 24)",
    )
    create_parser.add_argument(
        "-e",
        "--end",
        type=float,
        default=1766.0,
        help="End frequency in MHz (default: 1766)",
    )
    create_parser.add_argument(
        "--db",
        type=str,
        default="data/unified.duckdb",
        help="DuckDB path (default: data/unified.duckdb)",
    )
    # Phase 2: Location/Run Context
    create_parser.add_argument(
        "-l",
        "--location",
        type=str,
        default=None,
        help="Location name for run differentiation (e.g., 'NYC Office')",
    )
    create_parser.add_argument(
        "-a",
        "--antenna",
        type=str,
        default=None,
        help="Antenna type (e.g., 'Discone', 'Stock RTL-SDR')",
    )
    create_parser.add_argument(
        "--notes",
        type=str,
        default=None,
        help="Conditions notes (e.g., 'Clear weather')",
    )

    # Resume survey
    resume_parser = subparsers.add_parser("resume", help="Resume an existing survey")
    resume_parser.add_argument("survey_id", help="Survey ID to resume")
    resume_parser.add_argument(
        "--max",
        type=int,
        default=None,
        help="Maximum segments to scan this run",
    )
    resume_parser.add_argument(
        "--db",
        type=str,
        default="data/unified.duckdb",
        help="DuckDB path",
    )

    # Execute next segment (for Ralph loops)
    next_parser = subparsers.add_parser("next", help="Execute next pending segment")
    next_parser.add_argument("survey_id", help="Survey ID")
    next_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON for Ralph integration",
    )
    next_parser.add_argument(
        "--db",
        type=str,
        default="data/unified.duckdb",
        help="DuckDB path",
    )

    # Status check
    status_parser = subparsers.add_parser("status", help="Show survey status")
    status_parser.add_argument(
        "survey_id",
        nargs="?",
        default=None,
        help="Survey ID (omit to list all)",
    )
    status_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    status_parser.add_argument(
        "--db",
        type=str,
        default="data/unified.duckdb",
        help="DuckDB path",
    )

    # List surveys
    list_parser = subparsers.add_parser("list", help="List all surveys")
    list_parser.add_argument(
        "--db",
        type=str,
        default="data/unified.duckdb",
        help="DuckDB path",
    )
    list_parser.add_argument(
        "-l",
        "--location",
        type=str,
        default=None,
        help="Filter by location name",
    )

    # Common options
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()
    setup_logging(args.verbose if hasattr(args, "verbose") else False)

    # Import survey modules
    try:
        import json as json_module
        from pathlib import Path

        from sdr_toolkit.storage import UnifiedDB
        from sdr_toolkit.apps.survey.manager import SurveyManager
        from sdr_toolkit.apps.survey.executor import SurveyExecutor
        from sdr_toolkit.apps.survey.band_catalog import (
            estimate_survey_duration,
            format_duration,
        )
    except ImportError as e:
        print(f"Error: Survey modules not available: {e}", file=sys.stderr)
        sys.exit(1)

    # Get database path
    db_path = Path(getattr(args, "db", "data/unified.duckdb"))

    try:
        with UnifiedDB(db_path) as db:
            manager = SurveyManager(db)

            if args.command == "create":
                # Create new survey
                full_coverage = not args.priority_only

                survey = manager.create_survey(
                    name=args.name,
                    start_hz=args.start * 1e6,
                    end_hz=args.end * 1e6,
                    full_coverage=full_coverage,
                    # Phase 2: Location/Run Context
                    location_name=args.location,
                    antenna_type=args.antenna,
                    conditions_notes=args.notes,
                )

                segments = manager.get_segments(survey.survey_id)
                est_time = estimate_survey_duration(segments)

                print(f"Created survey: {survey.name}")
                print(f"  ID: {survey.survey_id}")
                print(f"  Segments: {len(segments)}")
                print(f"  Estimated time: {format_duration(est_time)}")
                if survey.location_name:
                    print(f"  Location: {survey.location_name} (Run #{survey.run_number})")
                if survey.antenna_type:
                    print(f"  Antenna: {survey.antenna_type}")
                print(f"\nTo start: uv run sdr-survey resume {survey.survey_id}")

            elif args.command == "resume":
                # Resume existing survey
                survey = manager.get_survey(args.survey_id)
                if not survey:
                    print(f"Error: Survey {args.survey_id} not found", file=sys.stderr)
                    sys.exit(1)

                executor = SurveyExecutor(manager, db)
                result = executor.run_continuous(
                    args.survey_id,
                    max_segments=args.max,
                )

                print(f"\nSurvey {'completed' if result.complete else 'paused'}")
                print(f"  Segments this run: {result.segments_completed}")
                print(f"  Signals found: {result.total_signals}")
                print(f"  Time: {format_duration(result.total_time_seconds)}")

                if result.errors:
                    print("\nErrors:")
                    for err in result.errors:
                        print(f"  - {err}")

            elif args.command == "next":
                # Execute single segment (Ralph integration)
                segment = manager.get_next_segment(args.survey_id)

                if segment is None:
                    if args.json:
                        print(json_module.dumps({
                            "complete": True,
                            "message": "Survey complete - no pending segments",
                        }))
                    else:
                        print("Survey complete - no pending segments")
                        print("<promise>SURVEY COMPLETE</promise>")
                    sys.exit(0)

                executor = SurveyExecutor(manager, db)
                result = executor.execute_segment(segment)

                if args.json:
                    output = {
                        "segment": {
                            "id": segment.segment_id,
                            "name": segment.name,
                            "start_mhz": segment.start_freq_hz / 1e6,
                            "end_mhz": segment.end_freq_hz / 1e6,
                        },
                        "result": result.to_dict(),
                        "survey_state": manager.get_ralph_state(args.survey_id),
                    }
                    print(json_module.dumps(output, indent=2, default=str))
                else:
                    survey = manager.get_survey(args.survey_id)
                    print(f"Scanned: {segment.name}")
                    print(f"  Signals: {result.signals_found}")
                    print(f"  Time: {result.scan_time_seconds:.1f}s")
                    if survey:
                        print(f"  Progress: {survey.completion_pct:.1f}%")

            elif args.command == "status":
                if args.survey_id:
                    # Single survey status
                    survey = manager.get_survey(args.survey_id)
                    if not survey:
                        print(f"Error: Survey {args.survey_id} not found", file=sys.stderr)
                        sys.exit(1)

                    if args.json:
                        print(json_module.dumps(manager.get_ralph_state(args.survey_id), indent=2, default=str))
                    else:
                        segments = manager.get_segments(survey.survey_id)
                        pending = [s for s in segments if s.status.value == "pending"]
                        est_remaining = estimate_survey_duration(pending)

                        print(f"Survey: {survey.name}")
                        print(f"  ID: {survey.survey_id}")
                        print(f"  Status: {survey.status.value}")
                        print(f"  Progress: {survey.completed_segments}/{survey.total_segments} ({survey.completion_pct:.1f}%)")
                        print(f"  Signals: {survey.total_signals_found}")
                        print(f"  Remaining: {format_duration(est_remaining)}")
                else:
                    # List all surveys
                    surveys = manager.list_surveys()
                    if not surveys:
                        print("No surveys found")
                    else:
                        print(f"{'ID':<36} {'Name':<25} {'Status':<12} {'Progress'}")
                        print("-" * 90)
                        for s in surveys:
                            print(f"{s.survey_id} {s.name:<25} {s.status.value:<12} {s.completion_pct:.1f}%")

            elif args.command == "list":
                if args.location:
                    surveys = manager.list_surveys_by_location(args.location)
                    header = f"Surveys at '{args.location}'"
                else:
                    surveys = manager.list_surveys()
                    header = "All Surveys"

                if not surveys:
                    print(f"No surveys found{' at ' + args.location if args.location else ''}")
                else:
                    print(f"\n{header}")
                    print(f"{'ID':<36} {'Name':<20} {'Location':<15} {'Run':<4} {'Status':<12} {'Progress'}")
                    print("-" * 105)
                    for s in surveys:
                        loc = (s.location_name or "-")[:14]
                        run = str(s.run_number) if s.run_number else "-"
                        print(f"{s.survey_id} {s.name:<20} {loc:<15} {run:<4} {s.status.value:<12} {s.completion_pct:.1f}%")

    except KeyboardInterrupt:
        print("\nCancelled")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose if hasattr(args, "verbose") else False:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Default to fm_radio if run directly
    fm_radio()
