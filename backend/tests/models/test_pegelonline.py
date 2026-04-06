"""Tests for PEGELONLINE Pydantic models.

Covers:
- PegelonlineStation validates uuid, shortname, latitude, longitude, water.longname
- PegelonlineMeasurement extracts level_cm from timeseries W shortname
- Station with no timeseries returns level_cm=None (not ValueError)
- Station with timeseries but no currentMeasurement returns level_cm=None
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.pegelonline import (
    PegelonlineCurrentMeasurement,
    PegelonlineStation,
    PegelonlineTimeseries,
    PegelonlineWater,
)


SAMPLE_STATION_DICT = {
    "uuid": "be7ce40e-1234-5678-abcd-ef0123456789",
    "shortname": "PLOCHINGEN",
    "water": {"longname": "NECKAR"},
    "latitude": 48.707,
    "longitude": 9.419,
    "timeseries": [
        {
            "shortname": "W",
            "unit": "cm",
            "currentMeasurement": {
                "timestamp": "2026-04-06T01:30:00+02:00",
                "value": 159.0,
            },
        }
    ],
}


def test_station_valid_fields() -> None:
    """PegelonlineStation parses uuid, shortname, lat, lon, water.longname."""
    station = PegelonlineStation.model_validate(SAMPLE_STATION_DICT)
    assert station.uuid == "be7ce40e-1234-5678-abcd-ef0123456789"
    assert station.shortname == "PLOCHINGEN"
    assert station.latitude == pytest.approx(48.707)
    assert station.longitude == pytest.approx(9.419)
    assert station.water.longname == "NECKAR"


def test_station_current_level_cm_returns_float() -> None:
    """current_level_cm() returns float for station with W timeseries."""
    station = PegelonlineStation.model_validate(SAMPLE_STATION_DICT)
    level = station.current_level_cm()
    assert level == pytest.approx(159.0)


def test_station_current_timestamp() -> None:
    """current_timestamp() returns the ISO timestamp string."""
    station = PegelonlineStation.model_validate(SAMPLE_STATION_DICT)
    ts = station.current_timestamp()
    assert ts == "2026-04-06T01:30:00+02:00"


def test_station_no_timeseries_returns_none() -> None:
    """Station with empty timeseries returns None, not a ValueError."""
    data = {**SAMPLE_STATION_DICT, "timeseries": []}
    station = PegelonlineStation.model_validate(data)
    assert station.current_level_cm() is None
    assert station.current_timestamp() is None


def test_station_timeseries_without_current_measurement_returns_none() -> None:
    """Station timeseries W with currentMeasurement=None returns None."""
    data = {
        **SAMPLE_STATION_DICT,
        "timeseries": [
            {
                "shortname": "W",
                "unit": "cm",
                "currentMeasurement": None,
            }
        ],
    }
    station = PegelonlineStation.model_validate(data)
    assert station.current_level_cm() is None


def test_station_timeseries_non_w_shortname_returns_none() -> None:
    """Station with only Q (discharge) timeseries returns None for level_cm."""
    data = {
        **SAMPLE_STATION_DICT,
        "timeseries": [
            {
                "shortname": "Q",
                "unit": "m3/s",
                "currentMeasurement": {
                    "timestamp": "2026-04-06T01:30:00+02:00",
                    "value": 42.5,
                },
            }
        ],
    }
    station = PegelonlineStation.model_validate(data)
    assert station.current_level_cm() is None


def test_station_missing_timeseries_defaults_to_empty() -> None:
    """timeseries field defaults to [] when absent from response."""
    data = {k: v for k, v in SAMPLE_STATION_DICT.items() if k != "timeseries"}
    station = PegelonlineStation.model_validate(data)
    assert station.timeseries == []
    assert station.current_level_cm() is None


def test_station_uuid_is_str() -> None:
    """uuid field is a plain string, not a UUID object."""
    station = PegelonlineStation.model_validate(SAMPLE_STATION_DICT)
    assert isinstance(station.uuid, str)


def test_station_lat_lon_are_floats() -> None:
    """latitude and longitude are floats."""
    station = PegelonlineStation.model_validate(SAMPLE_STATION_DICT)
    assert isinstance(station.latitude, float)
    assert isinstance(station.longitude, float)


def test_current_measurement_value_none() -> None:
    """PegelonlineCurrentMeasurement accepts value=None."""
    m = PegelonlineCurrentMeasurement.model_validate(
        {"timestamp": "2026-04-06T00:00:00+00:00", "value": None}
    )
    assert m.value is None


def test_water_longname() -> None:
    """PegelonlineWater parses longname correctly."""
    w = PegelonlineWater.model_validate({"longname": "NECKAR"})
    assert w.longname == "NECKAR"
