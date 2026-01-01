"""Listen to FM radio station."""

import sys

from rf_asset_discovery.apps.fm_radio import FMRadio


def main(freq_mhz: float = 101.9, duration: int = 30) -> int:
    print(f"FM: {freq_mhz} MHz for {duration}s (Ctrl+C to stop)")

    try:
        radio = FMRadio(freq_mhz=freq_mhz)
        radio.listen(duration=duration if duration > 0 else None)
        return 0
    except KeyboardInterrupt:
        print("\nStopped")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    freq = float(sys.argv[1]) if len(sys.argv) > 1 else 101.9
    dur = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    sys.exit(main(freq, dur))
