"""Tests for MastrConnector — Phase 7, Plan 03.

Marktstammdatenregister (BNetzA) provides a registry of all energy
production units in Germany. Tests verify Ostalbkreis filtering and
Lage field classification.
"""
from __future__ import annotations

import pandas as pd
import pytest

from app.connectors.mastr import MastrConnector, LANDKREIS_FILTER, _classify_installation
from app.config import ConnectorConfig, Town, TownBbox


@pytest.fixture
def mastr_config() -> ConnectorConfig:
    return ConnectorConfig(
        connector_class="MastrConnector",
        poll_interval_seconds=86400,
        enabled=True,
        config={},
    )


@pytest.fixture
def aalen_town() -> Town:
    return Town(
        id="aalen",
        display_name="Aalen (Württemberg)",
        country="DE",
        timezone="Europe/Berlin",
        bbox=TownBbox(
            lon_min=9.9700,
            lat_min=48.7600,
            lon_max=10.2200,
            lat_max=48.9000,
        ),
        connectors=[],
    )


@pytest.fixture
def connector(mastr_config: ConnectorConfig, aalen_town: Town) -> MastrConnector:
    return MastrConnector(mastr_config, aalen_town)


def test_mastr_landkreis_filter(connector: MastrConnector) -> None:
    """Only units within Ostalbkreis are returned after filtering.

    Given a DataFrame with rows from Ostalbkreis and Stuttgart,
    only the Ostalbkreis rows are kept.
    """
    import json

    sample_df = pd.DataFrame([
        {
            "EinheitMastrNummer": "SEE100001",
            "Landkreis": "Ostalbkreis",
            "Breitengrad": 48.84,
            "Laengengrad": 10.09,
            "Nettonennleistung": 10.0,
            "Inbetriebnahmedatum": "2020-01-01",
            "Lage": "Bauliche Anlagen (Hausdach, Gebaeude und Freiflaechenanlagen)",
            "Technologie": "solar",
            "AnlagenbetreiberMastrNummer": "ABR100001",
            "Standort": "Aalen",
        },
        {
            "EinheitMastrNummer": "SEE100002",
            "Landkreis": "Stuttgart",
            "Breitengrad": 48.78,
            "Laengengrad": 9.18,
            "Nettonennleistung": 5.0,
            "Inbetriebnahmedatum": "2019-06-15",
            "Lage": "Freiflaeche",
            "Technologie": "solar",
            "AnlagenbetreiberMastrNummer": "ABR100002",
            "Standort": "Stuttgart",
        },
        {
            "EinheitMastrNummer": "SEE100003",
            "Landkreis": "Ostalbkreis",
            "Breitengrad": 48.85,
            "Laengengrad": 10.10,
            "Nettonennleistung": 200.0,
            "Inbetriebnahmedatum": "2018-03-20",
            "Lage": "Freiflaeche",
            "Technologie": "wind",
            "AnlagenbetreiberMastrNummer": "ABR100003",
            "Standort": "Ellwangen",
        },
    ])

    # Serialize sample data as the connector would receive
    raw = sample_df.to_json(orient="records").encode()
    filtered = connector._filter_by_landkreis(raw)

    assert len(filtered) == 2
    for row in filtered:
        assert row["Landkreis"] == LANDKREIS_FILTER


def test_mastr_lage_field_mapping(connector: MastrConnector) -> None:
    """Lage field is correctly mapped to installation type labels.

    'Bauliche Anlagen (Hausdach, ...)' maps to 'solar_rooftop'
    'Freiflaeche' maps to 'solar_ground'
    wind technology maps to 'wind'
    storage technology maps to 'battery'
    """
    # solar rooftop
    row_rooftop = {
        "Lage": "Bauliche Anlagen (Hausdach, Gebaeude und Freiflaechenanlagen)",
        "Technologie": "solar",
    }
    assert _classify_installation(row_rooftop) == "solar_rooftop"

    # solar rooftop variant with "Aufdach"
    row_aufdach = {
        "Lage": "Aufdach",
        "Technologie": "solar",
    }
    assert _classify_installation(row_aufdach) == "solar_rooftop"

    # solar ground
    row_ground = {
        "Lage": "Freiflaeche",
        "Technologie": "solar",
    }
    assert _classify_installation(row_ground) == "solar_ground"

    # wind turbine
    row_wind = {
        "Lage": "",
        "Technologie": "wind",
    }
    assert _classify_installation(row_wind) == "wind"

    # battery storage
    row_battery = {
        "Lage": "",
        "Technologie": "storage",
    }
    assert _classify_installation(row_battery) == "battery"


def test_mastr_normalize_returns_empty(connector: MastrConnector) -> None:
    """normalize() returns empty list — MaStR is features-only, no time-series."""
    raw = b'[]'
    result = connector.normalize(raw)
    assert result == []


def test_mastr_landkreis_constant() -> None:
    """LANDKREIS_FILTER is set to the correct value for Aalen's district."""
    assert LANDKREIS_FILTER == "Ostalbkreis"
