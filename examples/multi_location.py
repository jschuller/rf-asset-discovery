"""Compare signals across locations using Delta Lake time travel."""

from pathlib import Path

from rf_asset_discovery.storage import UnifiedDB
from rf_asset_discovery.storage.delta_store import DeltaStore


def main() -> None:
    db_path = Path("data/unified.duckdb")
    delta_path = Path("data/delta")

    with UnifiedDB(db_path) as db:
        # Query signals by location
        for location in ["NYC Office", "Home Lab"]:
            signals = db.conn.execute(
                "SELECT frequency_hz, power_db FROM signals WHERE location_name = ?",
                [location],
            ).fetchall()
            print(f"{location}: {len(signals)} signals")

    # Delta Lake time travel
    if delta_path.exists():
        store = DeltaStore(delta_path)
        history = store.history()
        print(f"\nDelta versions: {len(history)}")

        # Compare versions
        if len(history) >= 2:
            v1 = store.read_signals(version=0)
            v2 = store.read_signals()
            new_freqs = set(v2["frequency_hz"]) - set(v1["frequency_hz"])
            print(f"New frequencies since v0: {len(new_freqs)}")


if __name__ == "__main__":
    main()
