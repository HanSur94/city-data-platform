"""Integration tests for BKG VG250 administrative boundary data in PostGIS.

These tests run AFTER the load_vg250.py script has been executed.
They verify:
1. At least one row exists for Aalen in the features table
2. Geometry is in WGS84 (EPSG:4326) — coordinates fall in Baden-Württemberg
3. Properties JSONB contains expected BKG metadata (gen, ags fields)
"""
import pytest
from sqlalchemy import text


def test_aalen_boundary_exists(db_conn):
    """At least one administrative boundary feature for Aalen must exist."""
    result = db_conn.execute(
        text(
            "SELECT COUNT(*) FROM features "
            "WHERE town_id = 'aalen' AND domain = 'administrative'"
        )
    )
    count = result.scalar()
    assert count >= 1, (
        f"Expected at least 1 administrative feature for town_id='aalen', got {count}. "
        "Run: scripts/load_vg250.py aalen 08136088"
    )


def test_aalen_boundary_geometry_is_wgs84(db_conn):
    """Geometry must be in WGS84 (SRID 4326)."""
    result = db_conn.execute(
        text(
            "SELECT ST_SRID(geometry) FROM features "
            "WHERE town_id = 'aalen' AND domain = 'administrative' "
            "LIMIT 1"
        )
    )
    srid = result.scalar()
    assert srid == 4326, f"Expected SRID 4326 (WGS84), got {srid}"


def test_aalen_boundary_coordinates_in_bw(db_conn):
    """Aalen boundary centroid must fall within Baden-Württemberg extent.

    BW approximate bounds: lon 7.5-10.5, lat 47.5-49.8
    Aalen is approximately at lon 10.09, lat 48.84
    """
    result = db_conn.execute(
        text(
            "SELECT ST_X(ST_Centroid(geometry)), ST_Y(ST_Centroid(geometry)) "
            "FROM features "
            "WHERE town_id = 'aalen' AND domain = 'administrative' "
            "LIMIT 1"
        )
    )
    row = result.fetchone()
    assert row is not None, "No boundary row to check coordinates"
    lon, lat = row[0], row[1]
    assert 7.5 <= lon <= 10.5, f"Longitude {lon} outside Baden-Württemberg (7.5-10.5)"
    assert 47.5 <= lat <= 49.8, f"Latitude {lat} outside Baden-Württemberg (47.5-49.8)"


def test_aalen_boundary_properties_contain_ags(db_conn):
    """Properties JSONB must contain 'ags' field with correct value '08136088'."""
    result = db_conn.execute(
        text(
            "SELECT properties->>'ags' FROM features "
            "WHERE town_id = 'aalen' AND domain = 'administrative' "
            "LIMIT 1"
        )
    )
    ags = result.scalar()
    assert ags == "08136088", f"Expected AGS '08136088', got '{ags}'"


def test_aalen_boundary_source_id(db_conn):
    """Source ID must be 'bkg_vg250' for traceability."""
    result = db_conn.execute(
        text(
            "SELECT source_id FROM features "
            "WHERE town_id = 'aalen' AND domain = 'administrative' "
            "LIMIT 1"
        )
    )
    source_id = result.scalar()
    assert source_id == "bkg_vg250", f"Expected source_id 'bkg_vg250', got '{source_id}'"


def test_aalen_boundary_is_multipolygon(db_conn):
    """Aalen administrative boundary geometry type must be (Multi)Polygon."""
    result = db_conn.execute(
        text(
            "SELECT ST_GeometryType(geometry) FROM features "
            "WHERE town_id = 'aalen' AND domain = 'administrative' "
            "LIMIT 1"
        )
    )
    geom_type = result.scalar()
    assert geom_type in ("ST_Polygon", "ST_MultiPolygon"), (
        f"Expected ST_Polygon or ST_MultiPolygon, got {geom_type}"
    )
