"""Tests for town YAML config loading and Pydantic validation."""
import pytest
from pathlib import Path
from pydantic import ValidationError

from app.config import load_town, Town, ConnectorConfig, TownBbox

# Resolve to the project root's towns/ directory
TOWNS_DIR = Path(__file__).parent.parent.parent / "towns"


def test_load_aalen():
    town = load_town("aalen", towns_dir=TOWNS_DIR)
    assert town.id == "aalen"
    assert town.display_name == "Aalen (Württemberg)"
    assert town.country == "DE"


def test_load_example():
    town = load_town("example", towns_dir=TOWNS_DIR)
    assert town.id == "example"
    assert town.display_name == "Example Town"


def test_aalen_bbox():
    town = load_town("aalen", towns_dir=TOWNS_DIR)
    assert town.bbox.lon_min == pytest.approx(9.9700)
    assert town.bbox.lat_min == pytest.approx(48.7600)
    assert town.bbox.lon_max == pytest.approx(10.2200)
    assert town.bbox.lat_max == pytest.approx(48.9000)


def test_missing_town_raises_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_town("nonexistent_town_xyz", towns_dir=TOWNS_DIR)


def test_invalid_yaml_raises_validation():
    """An empty dict (missing required fields) must raise ValidationError."""
    with pytest.raises(ValidationError):
        Town.model_validate({})


def test_town_id_slug_validation():
    """Town id with spaces or special characters must raise ValidationError."""
    with pytest.raises(ValidationError):
        Town.model_validate({
            "id": "Bad ID!",
            "display_name": "Bad Town",
            "bbox": {"lon_min": 0, "lat_min": 0, "lon_max": 1, "lat_max": 1},
        })


def test_connectors_field_defaults_to_empty_list():
    """A town YAML without a connectors key should load with connectors=[]."""
    town = Town.model_validate({
        "id": "minimal",
        "display_name": "Minimal Town",
        "bbox": {"lon_min": 0, "lat_min": 0, "lon_max": 1, "lat_max": 1},
    })
    assert town.connectors == []
