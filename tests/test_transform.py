"""Tests for the bronze -> silver -> gold MedallionTransformer on an in-memory DuckDB."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

import pytest

pytest.importorskip("duckdb")

if TYPE_CHECKING:
    from rf_asset_discovery.apps.transform import MedallionTransformer

# (signal_id, frequency_hz, power_db, freq_band, detection_count)
SIGNALS = [
    ("fm", 101.9e6, 25.0, "fm_broadcast", 3),  # silver + gold, LOW risk
    ("ism433", 433.92e6, 15.0, "ism_433", 2),  # silver + gold, Purdue 0, HIGH risk
    ("ism900_weak", 915.0e6, 5.0, "ism_900", 2),  # silver only: below the gold power gate
    ("odd_band", 2.1e9, 20.0, "cellular_2100", 4),  # silver only: protocol UNKNOWN
    ("fm_once", 98.5e6, 12.0, "fm_broadcast", 1),  # dropped by min_detections=2
    ("negative", 99.1e6, -3.0, "fm_broadcast", 5),  # dropped: power below 0 dB
    ("unknown", 300.0e6, 30.0, "unknown", 5),  # dropped: excluded band
    ("gap", 1.0e9, 30.0, "gap", 5),  # dropped: excluded band
    ("no_band", 50.0e6, 30.0, None, 5),  # dropped: no band
]


@pytest.fixture
def transformer() -> Iterator[MedallionTransformer]:
    """A transformer on an in-memory database seeded with main.signals."""
    from rf_asset_discovery.apps.transform import MedallionTransformer

    with MedallionTransformer(":memory:") as t:
        t.conn.execute(
            """
            CREATE TABLE main.signals (
                signal_id VARCHAR, frequency_hz DOUBLE, power_db DOUBLE,
                bandwidth_hz DOUBLE, freq_band VARCHAR, detection_count INTEGER,
                state VARCHAR, first_seen TIMESTAMP, last_seen TIMESTAMP,
                survey_id VARCHAR, segment_id VARCHAR, location_name VARCHAR,
                year INTEGER, month INTEGER
            )
            """
        )
        for signal_id, freq_hz, power_db, band, detections in SIGNALS:
            t.conn.execute(
                """
                INSERT INTO main.signals VALUES (
                    ?, ?, ?, 25000, ?, ?, 'active',
                    TIMESTAMP '2026-01-01 10:00:00', TIMESTAMP '2026-01-01 11:00:00',
                    'survey1', 'seg1', 'Lab', 2026, 1
                )
                """,
                [signal_id, freq_hz, power_db, band, detections],
            )
        yield t


def _ids(t: MedallionTransformer, sql: str) -> set[str]:
    return {row[0] for row in t.conn.execute(sql).fetchall()}


def test_full_pipeline_applies_silver_and_gold_gates(transformer: MedallionTransformer) -> None:
    results = transformer.run_full_pipeline(min_silver_detections=2)
    by_table = {(r.layer, r.table): r for r in results}

    assert by_table[("bronze", "signals")].success
    assert by_table[("bronze", "signals")].rows_created == len(SIGNALS)
    assert not by_table[("bronze", "scan_sessions")].success  # source table absent

    silver = by_table[("silver", "verified_signals")]
    assert silver.success
    assert silver.rows_created == 4
    assert _ids(transformer, "SELECT signal_id FROM silver.verified_signals") == {
        "fm",
        "ism433",
        "ism900_weak",
        "odd_band",
    }

    gold = by_table[("gold", "rf_assets")]
    assert gold.success
    assert gold.rows_source == gold.rows_created == 2
    assert _ids(transformer, "SELECT source_signal_id FROM gold.rf_assets") == {"fm", "ism433"}


def test_gold_classification_columns(transformer: MedallionTransformer) -> None:
    transformer.run_full_pipeline(min_silver_detections=2)
    rows = transformer.conn.execute(
        """
        SELECT source_signal_id, name, rf_protocol, cmdb_ci_class, purdue_level,
               security_posture, risk_level, location_name
        FROM gold.rf_assets ORDER BY source_signal_id
        """
    ).fetchall()

    assert rows == [
        (
            "fm",
            "fm_broadcast_101.9MHz",
            "FM_BROADCAST",
            "RF_BROADCAST_TRANSMITTER",
            5,
            "COMPLIANT",
            "LOW",
            "Lab",
        ),
        (
            "ism433",
            "ism_433_433.9MHz",
            "OOK",
            "RF_IOT_DEVICE",
            0,
            "REQUIRES_REVIEW",
            "HIGH",
            "Lab",
        ),
    ]


def test_default_silver_gate_keeps_single_detections(transformer: MedallionTransformer) -> None:
    transformer.migrate_to_bronze()
    result = transformer.bronze_to_silver()

    assert result.success
    assert result.rows_created == 5  # fm_once passes min_detections=1


def test_band_inventory_counts_bronze_signals_by_band(transformer: MedallionTransformer) -> None:
    transformer.migrate_to_bronze()
    result = transformer.create_band_inventory()

    assert result.success
    counts = dict(
        transformer.conn.execute(
            "SELECT freq_band, signal_count FROM silver.band_inventory"
        ).fetchall()
    )
    assert counts["fm_broadcast"] == 3
    assert counts["ism_433"] == 1
    assert None not in counts


def test_dry_run_counts_without_creating_tables(transformer: MedallionTransformer) -> None:
    results = transformer.run_full_pipeline(min_silver_detections=2, dry_run=True)

    silver, gold = results
    assert silver.rows_source == 4
    assert silver.rows_created == 0
    assert not gold.success  # no silver layer yet, so gold has nothing to read
    assert not transformer.schema_exists("silver")


def test_status_reports_layer_counts(transformer: MedallionTransformer) -> None:
    transformer.run_full_pipeline(min_silver_detections=2)
    status = transformer.get_status()

    assert status.schemas_exist == {"bronze": True, "silver": True, "gold": True}
    assert status.bronze_tables == {"signals": len(SIGNALS)}
    assert status.silver_tables["verified_signals"] == 4
    assert status.gold_tables == {"rf_assets": 2}
