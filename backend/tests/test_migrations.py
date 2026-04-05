"""Tests that verify the Alembic migration created the correct schema.

Run AFTER `alembic upgrade head` has been executed against the test database.
All tests use the `db_conn` fixture from conftest.py (sync psycopg2 connection).
"""
import pytest
from sqlalchemy import text


HYPERTABLES = [
    "air_quality_readings",
    "transit_positions",
    "water_readings",
    "energy_readings",
]

REGULAR_TABLES = ["features", "towns", "sources"]


def test_hypertables_exist(db_conn):
    """All four domain hypertables must exist in TimescaleDB metadata."""
    result = db_conn.execute(
        text("SELECT hypertable_name FROM timescaledb_information.hypertables")
    )
    found = {row[0] for row in result}
    for table in HYPERTABLES:
        assert table in found, f"Hypertable '{table}' not found. Found: {found}"


def test_features_table_exists(db_conn):
    result = db_conn.execute(
        text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name='features'"
        )
    )
    rows = result.fetchall()
    assert len(rows) == 1, "Table 'features' not found in public schema"


def test_towns_table_exists(db_conn):
    result = db_conn.execute(
        text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name='towns'"
        )
    )
    assert result.fetchone() is not None, "Table 'towns' not found"


def test_sources_table_exists(db_conn):
    result = db_conn.execute(
        text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name='sources'"
        )
    )
    assert result.fetchone() is not None, "Table 'sources' not found"


def test_postgis_extension(db_conn):
    result = db_conn.execute(
        text("SELECT extname FROM pg_extension WHERE extname = 'postgis'")
    )
    assert result.fetchone() is not None, "PostGIS extension not installed"


def test_timescaledb_extension(db_conn):
    result = db_conn.execute(
        text("SELECT extname FROM pg_extension WHERE extname = 'timescaledb'")
    )
    assert result.fetchone() is not None, "TimescaleDB extension not installed"


def test_features_geometry_gist_index(db_conn):
    result = db_conn.execute(
        text(
            "SELECT indexname FROM pg_indexes "
            "WHERE tablename = 'features' AND indexdef LIKE '%gist%'"
        )
    )
    rows = result.fetchall()
    assert len(rows) >= 1, "No GiST index on features.geometry found"


def test_retention_policies(db_conn):
    """Each hypertable should have a retention policy (drop_chunks job)."""
    result = db_conn.execute(
        text(
            "SELECT hypertable_name FROM timescaledb_information.jobs "
            "WHERE proc_name = 'policy_retention'"
        )
    )
    found = {row[0] for row in result}
    for table in HYPERTABLES:
        assert table in found, f"No retention policy for '{table}'. Found: {found}"
