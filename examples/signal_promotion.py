"""Signal lifecycle: discovered → confirmed → promoted to asset."""

from pathlib import Path

from sdr_toolkit.apps.survey import SurveyManager
from sdr_toolkit.storage import Signal, SignalState, UnifiedDB


def main() -> None:
    db_path = Path("data/unified.duckdb")
    db_path.parent.mkdir(exist_ok=True)

    with UnifiedDB(db_path) as db:
        manager = SurveyManager(db)

        # Create adhoc survey
        survey = manager.create_adhoc_survey(
            name="Signal Lifecycle Demo",
            start_hz=433e6,
            end_hz=434e6,
            location_name="Demo",
        )

        # Record signal (starts as DISCOVERED)
        signal = Signal(
            survey_id=survey.survey_id,
            frequency_hz=433.92e6,
            power_db=-35.0,
            location_name="Demo",
            year=2025,
            month=12,
        )
        db.record_signal(signal)
        print(f"Created: {signal.signal_id} [{signal.state}]")

        # Confirm signal
        manager.update_signal_state(signal.signal_id, SignalState.CONFIRMED)
        print(f"Confirmed: {signal.signal_id}")

        # Promote to asset
        manager.update_signal_state(signal.signal_id, SignalState.PROMOTED)
        print(f"Promoted: {signal.signal_id}")

        # List assets
        assets = db.get_all_assets()
        print(f"\nAssets: {len(assets)}")


if __name__ == "__main__":
    main()
