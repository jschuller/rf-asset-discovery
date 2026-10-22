"""RF Asset Discovery Dashboard - Streamlit MVP.

Run with: streamlit run dashboard.py
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

# Resolved from this file, not the working directory, so the dashboard finds
# its data wherever `streamlit run` is started
DATA_DIR = Path(__file__).resolve().parent / "data"

MISSING_LAYERS_HELP = (
    "This database has no medallion layers yet (bronze.signals, "
    "silver.verified_signals, gold.rf_assets). Build them with "
    "`uv run rfad-transform full --db <path>`."
)


def find_database(data_dir: Path = DATA_DIR) -> tuple[Path, bool] | None:
    """Locate the database to show.

    Args:
        data_dir: Directory holding unified.duckdb or example.duckdb.

    Returns:
        (path, is_example), or None if neither database exists.
    """
    unified = data_dir / "unified.duckdb"
    if unified.exists():
        return unified, False
    example = data_dir / "example.duckdb"
    if example.exists():
        return example, True
    return None


@st.cache_resource
def get_connection(db_path: str) -> duckdb.DuckDBPyConnection:
    """Open a read-only DuckDB connection (cached per path)."""
    return duckdb.connect(db_path, read_only=True)


def get_layer_counts(conn: duckdb.DuckDBPyConnection) -> dict[str, int] | None:
    """Get record counts for each layer.

    Returns:
        Counts per layer, or None if a layer's schema or table is missing
        (e.g. a database from rfad-scan before rfad-transform has run).
    """
    try:
        bronze = conn.execute("SELECT COUNT(*) FROM bronze.signals").fetchone()
        silver = conn.execute("SELECT COUNT(*) FROM silver.verified_signals").fetchone()
        gold = conn.execute("SELECT COUNT(*) FROM gold.rf_assets").fetchone()
    except duckdb.CatalogException:
        return None
    return {
        "bronze": bronze[0] if bronze else 0,
        "silver": silver[0] if silver else 0,
        "gold": gold[0] if gold else 0,
    }


def promotion_rate(counts: dict[str, int]) -> str:
    """Share of silver signals promoted to gold, or "n/a" when silver is empty."""
    if not counts["silver"]:
        return "n/a"
    return f"{counts['gold'] / counts['silver'] * 100:.1f}%"


def get_band_distribution(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Get signal count by frequency band."""
    return conn.execute("""
        SELECT
            freq_band as Band,
            COUNT(*) as Signals,
            ROUND(AVG(power_db), 1) as "Avg Power (dB)",
            ROUND(MAX(power_db), 1) as "Max Power (dB)"
        FROM silver.verified_signals
        WHERE freq_band IS NOT NULL
        GROUP BY freq_band
        ORDER BY Signals DESC
        LIMIT 15
    """).fetchdf()


def get_risk_distribution(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Get asset count by risk level."""
    return conn.execute("""
        SELECT
            risk_level as "Risk Level",
            COUNT(*) as Assets
        FROM gold.rf_assets
        GROUP BY risk_level
        ORDER BY Assets DESC
    """).fetchdf()


def get_protocol_distribution(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Get asset count by protocol."""
    return conn.execute("""
        SELECT
            rf_protocol as Protocol,
            COUNT(*) as Assets
        FROM gold.rf_assets
        GROUP BY rf_protocol
        ORDER BY Assets DESC
    """).fetchdf()


def get_top_signals(conn: duckdb.DuckDBPyConnection, limit: int = 15) -> pd.DataFrame:
    """Get strongest signals."""
    return conn.execute(f"""
        SELECT
            ROUND(rf_frequency_hz / 1e6, 2) as "Freq (MHz)",
            ROUND(rf_signal_strength_db, 1) as "Power (dB)",
            rf_protocol as Protocol,
            cmdb_ci_class as "CMDB Class",
            risk_level as Risk
        FROM gold.rf_assets
        ORDER BY rf_signal_strength_db DESC
        LIMIT {limit}
    """).fetchdf()


def get_power_histogram(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """Get power distribution for histogram."""
    return conn.execute("""
        SELECT
            ROUND(power_db, 0) as power_bin,
            COUNT(*) as count
        FROM silver.verified_signals
        GROUP BY power_bin
        ORDER BY power_bin
    """).fetchdf()


def main(data_dir: Path = DATA_DIR) -> None:
    """Main dashboard layout."""
    st.set_page_config(
        page_title="RF Asset Discovery Dashboard",
        page_icon="📡",
        layout="wide",
    )
    st.title("📡 RF Asset Discovery - RF Asset Dashboard")

    found = find_database(data_dir)
    if found is None:
        st.error(
            f"No database found in {data_dir}. Run rfad-scan, or restore "
            "data/example.duckdb from the repository."
        )
        return
    db_path, is_example = found
    if is_example:
        st.info("📊 Using example dataset. Run rfad-scan to collect your own data.")

    try:
        conn = get_connection(str(db_path))
    except duckdb.Error as e:
        st.error(f"Could not open {db_path}: {e}")
        return

    # Metrics row
    counts = get_layer_counts(conn)
    if counts is None:
        st.warning(MISSING_LAYERS_HELP)
        return
    if not counts["silver"]:
        st.info(
            "No verified (silver) signals yet. Silver needs repeated detections: "
            "run more survey passes, then `uv run rfad-transform full`."
        )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Bronze Signals", f"{counts['bronze']:,}")
    col2.metric("Silver Verified", f"{counts['silver']:,}")
    col3.metric("Gold Assets", f"{counts['gold']:,}")
    col4.metric("Promotion Rate", promotion_rate(counts))

    st.divider()

    # Charts row 1
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Assets by Frequency Band")
        band_df = get_band_distribution(conn)
        st.bar_chart(band_df.set_index("Band")["Signals"])

    with col2:
        st.subheader("Risk Level Distribution")
        risk_df = get_risk_distribution(conn)
        st.bar_chart(risk_df.set_index("Risk Level")["Assets"])

    st.divider()

    # Charts row 2
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Protocol Distribution")
        proto_df = get_protocol_distribution(conn)
        st.bar_chart(proto_df.set_index("Protocol")["Assets"])

    with col2:
        st.subheader("Power Distribution (dB)")
        power_df = get_power_histogram(conn)
        st.bar_chart(power_df.set_index("power_bin")["count"])

    st.divider()

    # Top signals table
    st.subheader("🔥 Top 15 Strongest Signals")
    top_df = get_top_signals(conn, 15)
    st.dataframe(top_df, use_container_width=True, hide_index=True)

    # Band details table
    st.subheader("📊 Band Statistics")
    st.dataframe(band_df, use_container_width=True, hide_index=True)

    # Footer
    st.divider()
    st.caption("RF Asset Discovery Dashboard | Data from DuckDB medallion architecture")


if __name__ == "__main__":
    main()
