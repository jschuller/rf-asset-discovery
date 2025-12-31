"""Record IQ samples to SigMF format."""

import sys
from datetime import datetime
from pathlib import Path

from sdr_toolkit.apps.recorder import SignalRecorder


def main(freq_mhz: float = 101.9, duration: float = 10) -> int:
    output_dir = Path("recordings") / datetime.now().strftime("%Y-%m-%d")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Recording {freq_mhz} MHz for {duration}s → {output_dir}")

    try:
        recorder = SignalRecorder(center_freq_mhz=freq_mhz)
        result = recorder.record_iq(duration=duration, output_dir=output_dir)

        print(f"Saved: {result.path}")
        print(f"Samples: {result.num_samples:,} @ {result.sample_rate/1e6:.1f} MHz")

        data_path = Path(str(result.path).replace("-meta", "-data"))
        if data_path.exists():
            print(f"Size: {data_path.stat().st_size / 1024 / 1024:.1f} MB")

        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    freq = float(sys.argv[1]) if len(sys.argv) > 1 else 101.9
    dur = float(sys.argv[2]) if len(sys.argv) > 2 else 10
    sys.exit(main(freq, dur))
