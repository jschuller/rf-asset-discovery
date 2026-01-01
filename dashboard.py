"""SDR Toolkit Dashboard - Streamlit MVP.

Run with: streamlit run dashboard.py
"""

import streamlit as st
import duckdb
import pandas as pd

# Page config
st.set_page_config(
    page_title="SDR Toolkit Dashboard",
    page_icon="📡",
    layout="wide",
)

st.title("📡 SDR Toolkit - RF Asset Dashboard")


@st.cache_resource
def get_connection():
    """Get DuckDB connection (cached)."""
    return duckdb.connect("data/unified.duckdb", read_only=True)


def get_layer_counts(conn) -> dict:
    """Get record counts for each layer."""
    bronze = conn.execute("SELECT COUNT(*) FROM bronze.signals").fetchone()[0]
    silver = conn.execute("SELECT COUNT(*) FROM silver.verified_signals").fetchone()[0]
    gold = conn.execute("SELECT COUNT(*) FROM gold.rf_assets").fetchone()[0]
    return {"bronze": bronze, "silver": silver, "gold": gold}


def get_band_distribution(conn) -> pd.DataFrame:
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


def get_risk_distribution(conn) -> pd.DataFrame:
    """Get asset count by risk level."""
    return conn.execute("""
        SELECT
            risk_level as "Risk Level",
            COUNT(*) as Assets
        FROM gold.rf_assets
        GROUP BY risk_level
        ORDER BY Assets DESC
    """).fetchdf()


def get_protocol_distribution(conn) -> pd.DataFrame:
    """Get asset count by protocol."""
    return conn.execute("""
        SELECT
            rf_protocol as Protocol,
            COUNT(*) as Assets
        FROM gold.rf_assets
        GROUP BY rf_protocol
        ORDER BY Assets DESC
    """).fetchdf()


def get_top_signals(conn, limit: int = 15) -> pd.DataFrame:
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


def get_power_histogram(conn) -> pd.DataFrame:
    """Get power distribution for histogram."""
    return conn.execute("""
        SELECT
            ROUND(power_db, 0) as power_bin,
            COUNT(*) as count
        FROM silver.verified_signals
        GROUP BY power_bin
        ORDER BY power_bin
    """).fetchdf()


def main():
    """Main dashboard layout."""
    try:
        conn = get_connection()
    except Exception as e:
        st.error(f"Could not connect to database: {e}")
        st.info("Make sure data/unified.duckdb exists.")
        return

    # Metrics row
    counts = get_layer_counts(conn)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Bronze Signals", f"{counts['bronze']:,}")
    col2.metric("Silver Verified", f"{counts['silver']:,}")
    col3.metric("Gold Assets", f"{counts['gold']:,}")
    col4.metric("Promotion Rate", f"{counts['gold'] / counts['silver'] * 100:.1f}%")

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
    st.caption("SDR Toolkit Dashboard | Data from DuckDB medallion architecture")


if __name__ == "__main__":
    main()
