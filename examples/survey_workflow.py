"""Full survey lifecycle: create, execute segments, promote signals."""

from pathlib import Path

from rf_asset_discovery.apps.survey import SurveyManager
from rf_asset_discovery.storage import SignalState, UnifiedDB


def main() -> None:
    db_path = Path("data/unified.duckdb")
    db_path.parent.mkdir(exist_ok=True)

    with UnifiedDB(db_path) as db:
        manager = SurveyManager(db)

        # Create survey
        survey = manager.create_survey(
            name="FM Band Survey",
            start_hz=87.5e6,
            end_hz=108e6,
            location_name="Home Lab",
        )
        print(f"Created: {survey.survey_id}")

        # Check segments
        segments = manager.get_segments(survey.survey_id)
        print(f"Segments: {len(segments)}")

        # Get signals (after execution)
        signals = manager.get_signals(survey.survey_id)
        for sig in signals[:5]:
            print(f"  {sig.frequency_hz/1e6:.2f} MHz: {sig.power_db:.1f} dB")

        # Promote strong signals
        for sig in signals:
            if sig.detection_count >= 3:
                manager.update_signal_state(sig.signal_id, SignalState.PROMOTED)


if __name__ == "__main__":
    main()
