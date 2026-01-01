"""CLI for {{ cookiecutter.project_name }}."""

from pathlib import Path

from {{ cookiecutter.project_slug }}.apps.transform import MedallionTransformer


def transform() -> None:
    """Run medallion transformation pipeline."""
    db_path = Path("data/{{ cookiecutter.project_slug }}.duckdb")

    if not db_path.exists():
        print(f"Database not found: {db_path}")
        print("Create bronze layer data first.")
        return

    with MedallionTransformer(db_path) as transformer:
        # Show current status
        status = transformer.get_status()
        print(f"Current state:")
        print(f"  Bronze: {status.bronze_count:,}")
        print(f"  Silver: {status.silver_count:,}")
        print(f"  Gold:   {status.gold_count:,}")
        print()

        # Run pipeline
        print("Running transformation pipeline...")
        results = transformer.run_full_pipeline()

        for result in results:
            status_icon = "✓" if result.success else "✗"
            print(
                f"  {status_icon} {result.layer}: "
                f"{result.rows_source:,} → {result.rows_created:,} "
                f"({result.duration_seconds:.2f}s)"
            )
            if result.error:
                print(f"    Error: {result.error}")

        # Final status
        final = transformer.get_status()
        print()
        print(f"Final state:")
        print(f"  Bronze: {final.bronze_count:,}")
        print(f"  Silver: {final.silver_count:,}")
        print(f"  Gold:   {final.gold_count:,}")


if __name__ == "__main__":
    transform()
