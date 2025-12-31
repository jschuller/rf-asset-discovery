"""Listen to aircraft band AM communications."""

import sys

from sdr_toolkit.apps.am_radio import AMRadio

NYC_FREQS = {
    "JFK Tower": 119.1,
    "JFK Ground": 121.9,
    "LGA Tower": 118.7,
    "EWR Tower": 118.3,
    "NY Approach": 125.95,
    "Emergency": 121.5,
}


def main(freq_mhz: float = 119.1, duration: int = 60) -> int:
    name = next((k for k, v in NYC_FREQS.items() if abs(v - freq_mhz) < 0.01), None)
    label = f"{freq_mhz} MHz" + (f" ({name})" if name else "")

    print(f"Aircraft: {label} for {duration}s (Ctrl+C to stop)")

    try:
        radio = AMRadio(freq_mhz=freq_mhz)
        radio.play(duration=duration if duration > 0 else None)
        return 0
    except KeyboardInterrupt:
        print("\nStopped")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    freq = float(sys.argv[1]) if len(sys.argv) > 1 else 119.1
    dur = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    sys.exit(main(freq, dur))
