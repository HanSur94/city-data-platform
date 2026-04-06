"""Tests for EEA EAQI 6-tier per-pollutant AQI scale in geojson.py."""
import pytest
from app.schemas.geojson import eaqi_from_readings


@pytest.mark.parametrize("pm25,pm10,no2,o3,expected", [
    # All low — good (tier 0)
    (3, 8, 8, 40, (0, "good", "#50F0E6")),
    # pm25=30 > 25 → tier 3; pm10=60 > 50 → tier 3; no2=60 > 50 → tier 3; o3=140 > 130 → tier 3 poor
    (30, 60, 60, 140, (3, "poor", "#FF5050")),
    # pm25=60: 50 < 60 <= 75 → tier 4 very_poor
    (60, 5, 5, 5, (4, "very_poor", "#960032")),
    # All None — unknown gray
    (None, None, None, None, (0, "unknown", "#9e9e9e")),
    # pm10=120: 100 < 120 <= 150 → tier 4 very_poor
    (None, 120, None, None, (4, "very_poor", "#960032")),
    # Extremely poor: pm25=80 → tier 5 (75 < 80 <= inf → tier 5 extremely_poor)
    (80, None, None, None, (5, "extremely_poor", "#7D2181")),
    # Extremely poor: pm25=100 → tier 5
    (100, None, None, None, (5, "extremely_poor", "#7D2181")),
    # O3 threshold check: o3=55 → tier 1 fair (50 < 55 <= 100)
    (None, None, None, 55, (1, "fair", "#50CCAA")),
    # Good boundary: pm25=5 → tier 0
    (5, None, None, None, (0, "good", "#50F0E6")),
    # Fair boundary: pm25=6 → tier 1
    (6, None, None, None, (1, "fair", "#50CCAA")),
    # no2=150: 100 < 150 <= 200 → tier 4 very_poor
    (None, None, 150, None, (4, "very_poor", "#960032")),
    # o3=250: 240 < 250 <= 380 → tier 4 very_poor (worst wins)
    (3, 3, 3, 250, (4, "very_poor", "#960032")),
])
def test_eaqi_from_readings(pm25, pm10, no2, o3, expected):
    result = eaqi_from_readings(pm25=pm25, pm10=pm10, no2=no2, o3=o3)
    assert result == expected, f"eaqi_from_readings({pm25=}, {pm10=}, {no2=}, {o3=}) = {result!r}, expected {expected!r}"


def test_eaqi_from_readings_returns_tuple():
    """Return type must be a 3-tuple (int, str, str)."""
    result = eaqi_from_readings(pm25=10, pm10=None, no2=None, o3=None)
    tier_idx, label, color = result
    assert isinstance(tier_idx, int)
    assert isinstance(label, str)
    assert color.startswith("#")


def test_old_aqi_tier_removed():
    """Old aqi_tier() function must not exist in geojson module."""
    import app.schemas.geojson as geojson_module
    assert not hasattr(geojson_module, "aqi_tier"), "aqi_tier() must be removed"
    assert not hasattr(geojson_module, "AQI_TIERS"), "AQI_TIERS must be removed"


def test_eaqi_breakpoints_exported():
    """EAQI_BREAKPOINTS constant must be importable."""
    from app.schemas.geojson import EAQI_BREAKPOINTS
    assert "pm25" in EAQI_BREAKPOINTS
    assert "pm10" in EAQI_BREAKPOINTS
    assert "no2" in EAQI_BREAKPOINTS
    assert "o3" in EAQI_BREAKPOINTS
    # Each list should have 6 thresholds
    for pollutant, thresholds in EAQI_BREAKPOINTS.items():
        assert len(thresholds) == 6, f"{pollutant} should have 6 thresholds"
