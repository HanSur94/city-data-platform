"""Tests for multi-town config loading (PLAT-09).

Validates that adding a new town YAML requires zero code changes —
load_town() accepts any valid town slug.
"""
import pytest
from pathlib import Path

from app.config import load_town

# Use the project-level towns/ directory relative to this file's location
TOWNS_DIR = Path(__file__).parent.parent.parent / "towns"


def test_load_ulm_succeeds():
    """load_town('ulm') returns a valid Town object without code changes."""
    town = load_town("ulm", towns_dir=TOWNS_DIR)
    assert town is not None


def test_load_ulm_id():
    """Loaded Ulm town has correct id."""
    town = load_town("ulm", towns_dir=TOWNS_DIR)
    assert town.id == "ulm"


def test_load_ulm_display_name():
    """Loaded Ulm town has correct display_name."""
    town = load_town("ulm", towns_dir=TOWNS_DIR)
    assert town.display_name == "Ulm (Donau)"


def test_load_ulm_bbox_valid():
    """Ulm bbox is logically valid (lon_min < lon_max, lat_min < lat_max)."""
    town = load_town("ulm", towns_dir=TOWNS_DIR)
    bbox = town.bbox
    assert bbox.lon_min < bbox.lon_max, "lon_min must be less than lon_max"
    assert bbox.lat_min < bbox.lat_max, "lat_min must be less than lat_max"


def test_load_ulm_connectors_count():
    """Ulm has at least 3 connectors configured."""
    town = load_town("ulm", towns_dir=TOWNS_DIR)
    assert len(town.connectors) >= 3


def test_load_aalen_regression():
    """load_town('aalen') still works after adding ulm — regression test."""
    town = load_town("aalen", towns_dir=TOWNS_DIR)
    assert town.id == "aalen"
    assert town.display_name == "Aalen (Württemberg)"
    assert len(town.connectors) >= 1


def test_load_nonexistent_raises():
    """load_town('nonexistent') raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_town("nonexistent", towns_dir=TOWNS_DIR)
