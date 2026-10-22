"""Tests for dashboard.py: empty and untransformed databases, and path resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

duckdb = pytest.importorskip("duckdb")
pytest.importorskip("streamlit")
pytest.importorskip("pandas")

from streamlit.testing.v1 import AppTest  # noqa: E402

import dashboard  # noqa: E402

REPO_DATA = Path(dashboard.__file__).resolve().parent / "data"


def _make_db(path: Path, *, layers: bool, bronze_rows: int = 0) -> None:
    """A database with empty silver and gold layers, or with no layers at all."""
    conn = duckdb.connect(str(path))
    conn.execute("CREATE TABLE scans (frequency_hz DOUBLE)")  # what rfad-scan leaves behind
    if layers:
        conn.execute("CREATE SCHEMA bronze")
        conn.execute("CREATE SCHEMA silver")
        conn.execute("CREATE SCHEMA gold")
        conn.execute("CREATE TABLE bronze.signals (frequency_hz DOUBLE, power_db DOUBLE)")
        conn.execute(
            "CREATE TABLE silver.verified_signals (freq_band VARCHAR, power_db DOUBLE)"
        )
        conn.execute(
            "CREATE TABLE gold.rf_assets (rf_frequency_hz DOUBLE, rf_signal_strength_db DOUBLE, "
            "rf_protocol VARCHAR, cmdb_ci_class VARCHAR, risk_level VARCHAR)"
        )
        for i in range(bronze_rows):
            conn.execute("INSERT INTO bronze.signals VALUES (?, ?)", [433.92e6 + i, -20.0])
    conn.close()


def _run_dashboard(data_dir: str) -> None:
    """AppTest script: run the dashboard against data_dir."""
    from pathlib import Path

    import dashboard

    dashboard.main(Path(data_dir))


def _app(data_dir: Path) -> AppTest:
    at = AppTest.from_function(_run_dashboard, kwargs={"data_dir": str(data_dir)})
    return at.run(timeout=30)


def test_find_database_does_not_depend_on_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    found = dashboard.find_database()
    assert found is not None
    path, _ = found
    assert path.parent == REPO_DATA
    assert path.is_absolute()


def test_find_database_prefers_unified_then_example(tmp_path: Path) -> None:
    assert dashboard.find_database(tmp_path) is None
    (tmp_path / "example.duckdb").touch()
    assert dashboard.find_database(tmp_path) == (tmp_path / "example.duckdb", True)
    (tmp_path / "unified.duckdb").touch()
    assert dashboard.find_database(tmp_path) == (tmp_path / "unified.duckdb", False)


def test_layer_counts_none_without_medallion_schemas(tmp_path: Path) -> None:
    _make_db(tmp_path / "unified.duckdb", layers=False)
    conn = duckdb.connect(str(tmp_path / "unified.duckdb"), read_only=True)
    assert dashboard.get_layer_counts(conn) is None


def test_promotion_rate_with_empty_silver() -> None:
    assert dashboard.promotion_rate({"bronze": 5, "silver": 0, "gold": 0}) == "n/a"
    assert dashboard.promotion_rate({"bronze": 5, "silver": 4, "gold": 1}) == "25.0%"


def test_app_without_layers_explains_how_to_build_them(tmp_path: Path) -> None:
    _make_db(tmp_path / "unified.duckdb", layers=False)
    at = _app(tmp_path)
    assert not at.exception
    assert any("rfad-transform full" in w.value for w in at.warning)


def test_app_with_empty_silver_renders(tmp_path: Path) -> None:
    _make_db(tmp_path / "unified.duckdb", layers=True, bronze_rows=3)
    at = _app(tmp_path)
    assert not at.exception
    assert [m.value for m in at.metric] == ["3", "0", "0", "n/a"]


def test_app_without_database_shows_error(tmp_path: Path) -> None:
    at = _app(tmp_path)
    assert not at.exception
    assert any("No database found" in e.value for e in at.error)


@pytest.mark.skipif(
    not (REPO_DATA / "example.duckdb").exists(), reason="data/example.duckdb not present"
)
def test_app_renders_example_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    example_only = tmp_path / "data"
    example_only.mkdir()
    (example_only / "example.duckdb").write_bytes((REPO_DATA / "example.duckdb").read_bytes())
    monkeypatch.chdir(tmp_path)
    at = _app(example_only)
    assert not at.exception
    assert len(at.metric) == 4
