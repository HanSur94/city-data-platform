"""Tests for AutobahnConnector — Phase 7, Plan 02 (TRAF-04).

Autobahn GmbH des Bundes provides roadworks and closures via REST API
at verkehr.autobahn.de. Tests cover: JSON parsing, distance filtering.

License: Datenlizenz Deutschland – Zero – Version 2.0
"""
from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.config import ConnectorConfig, Town, TownBbox
from app.connectors.autobahn import AutobahnConnector, _haversine
from app.connectors.base import Observation


# ---------------------------------------------------------------------------
# Sample Autobahn API response data
# ---------------------------------------------------------------------------

# Roadwork near Aalen (~10km away)
ROADWORK_NEAR = {
    "identifier": "rw-001",
    "coordinate": {"lat": "48.84", "long": "10.20"},
    "title": "Baustelle A7 Aalen",
    "subtitle": "Fahrbahnerneuerung",
    "description": "Fahrstreifenreduzierung auf 1 Spur",
    "isBlocked": False,
    "extent": "10.15,48.80,10.25,48.88",
}

# Closure near Aalen (~5km away)
CLOSURE_NEAR = {
    "identifier": "cl-001",
    "coordinate": {"lat": "48.88", "long": "10.09"},
    "title": "Vollsperrung A7",
    "subtitle": "Unfall",
    "description": "Vollsperrung für 2 Stunden",
    "isBlocked": True,
    "extent": "10.05,48.85,10.15,48.92",
}

# Roadwork far away (~100km from Aalen)
ROADWORK_FAR = {
    "identifier": "rw-far-001",
    "coordinate": {"lat": "49.50", "long": "11.10"},
    "title": "Baustelle A3 Nuernberg",
    "subtitle": "Brückenarbeiten",
    "description": "Gesperrte Spur",
    "isBlocked": False,
    "extent": "11.05,49.45,11.15,49.55",
}

SAMPLE_ROADWORKS_RESPONSE = {"roadworks": [ROADWORK_NEAR, ROADWORK_FAR]}
SAMPLE_CLOSURES_RESPONSE = {"closures": [CLOSURE_NEAR]}

# Combined fetch() response format: list of all entries from both roads
SAMPLE_COMBINED_BYTES = json.dumps({
    "roadworks": [ROADWORK_NEAR, ROADWORK_FAR],
    "closures": [CLOSURE_NEAR],
}).encode()


@pytest.fixture
def autobahn_config() -> ConnectorConfig:
    return ConnectorConfig(
        connector_class="AutobahnConnector",
        poll_interval_seconds=300,
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
def connector(autobahn_config, aalen_town) -> AutobahnConnector:
    return AutobahnConnector(config=autobahn_config, town=aalen_town)


# ---------------------------------------------------------------------------
# _haversine unit tests
# ---------------------------------------------------------------------------

def test_haversine_same_point() -> None:
    """Distance from a point to itself is 0."""
    dist = _haversine(48.84, 10.09, 48.84, 10.09)
    assert dist == pytest.approx(0.0, abs=0.001)


def test_haversine_known_distance() -> None:
    """Distance between Aalen and Stuttgart is roughly 73km."""
    # Stuttgart center: 48.7758, 9.1829
    # Aalen center: 48.84, 10.09
    dist = _haversine(48.84, 10.09, 48.7758, 9.1829)
    # Approximate check: should be roughly 60-85km
    assert 60 < dist < 85, f"Expected ~73km, got {dist:.1f}km"


def test_haversine_near_aalen() -> None:
    """Point ~10km from Aalen returns distance < 15km."""
    # ROADWORK_NEAR is at (48.84, 10.20)
    dist = _haversine(48.84, 10.09, 48.84, 10.20)
    assert dist < 15.0


def test_haversine_far_from_aalen() -> None:
    """Point ~100km from Aalen returns distance > 50km."""
    # ROADWORK_FAR is at (49.50, 11.10)
    dist = _haversine(48.84, 10.09, 49.50, 11.10)
    assert dist > 50.0


# ---------------------------------------------------------------------------
# normalize() tests
# ---------------------------------------------------------------------------

def test_autobahn_normalize_returns_empty_list(connector: AutobahnConnector) -> None:
    """normalize() returns empty list — Autobahn data is features-only."""
    result = connector.normalize(SAMPLE_COMBINED_BYTES)
    assert isinstance(result, list)
    assert len(result) == 0, "AutobahnConnector.normalize() must return []"


# ---------------------------------------------------------------------------
# run() integration tests (mocked)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_autobahn_roadworks_parse(connector: AutobahnConnector) -> None:
    """Autobahn API roadworks JSON is parsed: near entries result in upsert_feature calls."""
    upsert_calls = []

    async def mock_upsert(source_id, domain, geometry_wkt, properties):
        upsert_calls.append({
            "source_id": source_id,
            "domain": domain,
            "geometry_wkt": geometry_wkt,
            "properties": properties,
        })
        return f"uuid-{source_id}"

    async def mock_update_staleness():
        pass

    connector.upsert_feature = mock_upsert
    connector._update_staleness = mock_update_staleness

    class MockResponse:
        def __init__(self, data):
            self._data = data
        def json(self):
            return self._data
        def raise_for_status(self):
            pass
        @property
        def content(self):
            return json.dumps(self._data).encode()

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        # Sequence: A7 roadworks, A7 closures, A6 roadworks, A6 closures
        mock_client.get = AsyncMock(side_effect=[
            MockResponse({"roadworks": [ROADWORK_NEAR, ROADWORK_FAR]}),
            MockResponse({"closures": [CLOSURE_NEAR]}),
            MockResponse({"roadworks": []}),
            MockResponse({"closures": []}),
        ])
        mock_cls.return_value = mock_client

        await connector.run()

    # Should upsert features for near entries: ROADWORK_NEAR and CLOSURE_NEAR
    # ROADWORK_FAR (>50km) should be filtered out
    source_ids = [c["source_id"] for c in upsert_calls]
    assert "autobahn:rw-001" in source_ids, "Near roadwork should be upserted"
    assert "autobahn:cl-001" in source_ids, "Near closure should be upserted"
    assert "autobahn:rw-far-001" not in source_ids, "Far roadwork should be filtered"


@pytest.mark.asyncio
async def test_autobahn_filter_by_distance(connector: AutobahnConnector) -> None:
    """Only roadworks within 50km of town center are upserted."""
    upsert_calls = []

    async def mock_upsert(source_id, domain, geometry_wkt, properties):
        upsert_calls.append(source_id)
        return f"uuid-{source_id}"

    async def mock_update_staleness():
        pass

    connector.upsert_feature = mock_upsert
    connector._update_staleness = mock_update_staleness

    class MockResponse:
        def __init__(self, data):
            self._data = data
        def json(self):
            return self._data
        def raise_for_status(self):
            pass

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        # ROADWORK_FAR is ~100km from Aalen -> must be filtered
        mock_client.get = AsyncMock(side_effect=[
            MockResponse({"roadworks": [ROADWORK_NEAR, ROADWORK_FAR]}),
            MockResponse({"closures": []}),
            MockResponse({"roadworks": []}),
            MockResponse({"closures": []}),
        ])
        mock_cls.return_value = mock_client

        await connector.run()

    assert "autobahn:rw-far-001" not in upsert_calls
    assert "autobahn:rw-001" in upsert_calls


@pytest.mark.asyncio
async def test_autobahn_feature_properties(connector: AutobahnConnector) -> None:
    """Upserted features have correct properties from API response."""
    upserted = {}

    async def mock_upsert(source_id, domain, geometry_wkt, properties):
        upserted[source_id] = {"domain": domain, "geometry": geometry_wkt, "props": properties}
        return f"uuid-{source_id}"

    async def mock_update_staleness():
        pass

    connector.upsert_feature = mock_upsert
    connector._update_staleness = mock_update_staleness

    class MockResponse:
        def __init__(self, data):
            self._data = data
        def json(self):
            return self._data
        def raise_for_status(self):
            pass

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=[
            MockResponse({"roadworks": [ROADWORK_NEAR]}),
            MockResponse({"closures": [CLOSURE_NEAR]}),
            MockResponse({"roadworks": []}),
            MockResponse({"closures": []}),
        ])
        mock_cls.return_value = mock_client

        await connector.run()

    assert "autobahn:rw-001" in upserted
    rw = upserted["autobahn:rw-001"]
    assert rw["domain"] == "traffic"
    # Coordinate may render as 10.2 or 10.20 depending on float precision
    assert "10.2" in rw["geometry"] and "48.84" in rw["geometry"]
    assert rw["props"]["title"] == "Baustelle A7 Aalen"
    assert rw["props"]["is_blocked"] is False
    assert rw["props"]["type"] == "roadwork"

    assert "autobahn:cl-001" in upserted
    cl = upserted["autobahn:cl-001"]
    assert cl["props"]["is_blocked"] is True
    assert cl["props"]["type"] == "closure"
