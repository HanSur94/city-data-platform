"""Tests for GET /api/metadata/layers: per-layer connector status.

compute_layer_status / newest_fetch are pure functions and are tested without
any database. The endpoint tests use a mocked DB session.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import ConnectorConfig, Town, TownBbox
from app.db import get_db
from app.dependencies import get_current_town
from app.main import app
from app.routers.metadata import (
    LAYER_METADATA_REGISTRY,
    MIN_STALE_SECONDS,
    STALE_INTERVAL_FACTOR,
    compute_layer_status,
    newest_fetch,
)

NOW = datetime(2026, 11, 16, 12, 0, 0, tzinfo=timezone.utc)


def _ago(seconds: int) -> datetime:
    return NOW - timedelta(seconds=seconds)


def _entry(connectors: list[str], interval: int | None) -> dict:
    return {"connector_classes": connectors, "update_interval_seconds": interval}


# ── compute_layer_status (pure) ──────────────────────────────────────────────


def test_constants():
    assert STALE_INTERVAL_FACTOR == 3
    assert MIN_STALE_SECONDS == 600


def test_static_when_no_connectors_even_with_fetches_for_others():
    entry = _entry([], None)
    assert compute_layer_status(entry, {"UBAConnector": _ago(10)}, NOW) == "static"


def test_never_fetched_when_no_connector_in_map():
    entry = _entry(["UBAConnector"], 300)
    assert compute_layer_status(entry, {}, NOW) == "never_fetched"
    assert compute_layer_status(entry, {"OtherConnector": _ago(1)}, NOW) == "never_fetched"


@pytest.mark.parametrize(
    "age,expected",
    [(60, "ok"), (900, "ok"), (901, "stale")],
)
def test_threshold_three_times_interval(age, expected):
    entry = _entry(["UBAConnector"], 300)
    assert compute_layer_status(entry, {"UBAConnector": _ago(age)}, NOW) == expected


@pytest.mark.parametrize("age,expected", [(599, "ok"), (601, "stale")])
def test_ten_minute_floor(age, expected):
    entry = _entry(["BusInterpolationConnector"], 30)
    assert compute_layer_status(entry, {"BusInterpolationConnector": _ago(age)}, NOW) == expected


def test_no_registry_interval_is_never_stale():
    entry = _entry(["HeatDemandConnector"], None)
    fetched = {"HeatDemandConnector": NOW - timedelta(days=30)}
    assert compute_layer_status(entry, fetched, NOW) == "ok"


def test_two_connectors_one_fresh_one_never_is_ok():
    entry = _entry(["UBAConnector", "SensorCommunityConnector"], 300)
    assert compute_layer_status(entry, {"UBAConnector": _ago(60)}, NOW) == "ok"


def test_two_connectors_one_old_one_never_is_stale():
    entry = _entry(["UBAConnector", "SensorCommunityConnector"], 300)
    assert compute_layer_status(entry, {"UBAConnector": _ago(7200)}, NOW) == "stale"


def test_newest_fetch_decides():
    entry = _entry(["UBAConnector", "SensorCommunityConnector"], 300)
    fetched = {"UBAConnector": _ago(7200), "SensorCommunityConnector": _ago(60)}
    assert compute_layer_status(entry, fetched, NOW) == "ok"


def test_poll_intervals_raise_the_threshold():
    entry = _entry(["GTFSConnector"], 1800)
    fetched = {"GTFSConnector": _ago(2 * 86400)}
    assert compute_layer_status(entry, fetched, NOW, poll_intervals={"GTFSConnector": 604800}) == "ok"
    # Without poll intervals the literal rule applies.
    assert compute_layer_status(entry, fetched, NOW) == "stale"


def test_poll_interval_smaller_than_registry_does_not_lower_threshold():
    entry = _entry(["UBAConnector"], 3600)
    fetched = {"UBAConnector": _ago(3 * 3600)}
    assert compute_layer_status(entry, fetched, NOW, poll_intervals={"UBAConnector": 60}) == "ok"


def test_naive_datetime_is_treated_as_utc():
    entry = _entry(["UBAConnector"], 300)
    naive = (NOW - timedelta(seconds=60)).replace(tzinfo=None)
    assert compute_layer_status(entry, {"UBAConnector": naive}, NOW) == "ok"
    naive_old = (NOW - timedelta(seconds=5000)).replace(tzinfo=None)
    assert compute_layer_status(entry, {"UBAConnector": naive_old}, NOW) == "stale"


# ── newest_fetch (pure) ──────────────────────────────────────────────────────


def test_newest_fetch_returns_newest():
    entry = _entry(["A", "B", "C"], 300)
    fetched = {"A": _ago(500), "B": _ago(100), "X": _ago(1)}
    assert newest_fetch(entry, fetched) == _ago(100)


def test_newest_fetch_none_when_nothing_fetched():
    assert newest_fetch(_entry(["A"], 300), {}) is None
    assert newest_fetch(_entry([], None), {"A": _ago(1)}) is None


def test_newest_fetch_normalises_naive_to_utc():
    naive = datetime(2026, 11, 16, 11, 0, 0)
    result = newest_fetch(_entry(["A"], 300), {"A": naive})
    assert result is not None and result.tzinfo is not None
    assert result == naive.replace(tzinfo=timezone.utc)


# ── endpoint ─────────────────────────────────────────────────────────────────

ENDPOINT_TOWN = Town(
    id="aalen",
    display_name="Aalen (Wuerttemberg)",
    country="DE",
    bbox=TownBbox(lon_min=9.9, lat_min=48.7, lon_max=10.2, lat_max=48.9),
    connectors=[
        ConnectorConfig(connector_class="GTFSConnector", poll_interval_seconds=604800, enabled=True, config={}),
        ConnectorConfig(connector_class="PegelonlineConnector", poll_interval_seconds=900, enabled=True, config={}),
        ConnectorConfig(connector_class="UBAConnector", poll_interval_seconds=3600, enabled=True, config={}),
        ConnectorConfig(connector_class="SensorCommunityConnector", poll_interval_seconds=300, enabled=True, config={}),
    ],
)

EXPECTED_ITEM_KEYS = {
    "layer_key",
    "source_name",
    "source_url",
    "data_type",
    "update_interval_seconds",
    "license",
    "license_url",
    "last_updated",
    "status",
}


def _session_with_rows(rows: list[dict]) -> AsyncMock:
    session = AsyncMock()
    result = MagicMock()
    result.mappings.return_value.all.return_value = rows
    session.execute.return_value = result
    return session


async def _make_client(session: AsyncMock):
    async def _db():
        yield session

    app.dependency_overrides[get_current_town] = lambda: ENDPOINT_TOWN
    app.dependency_overrides[get_db] = _db


def _teardown():
    app.dependency_overrides.pop(get_current_town, None)
    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_endpoint_status_per_layer():
    now = datetime.now(timezone.utc)
    rows = [
        {"connector_class": "GTFSConnector", "last_successful_fetch": now - timedelta(seconds=60)},
        {"connector_class": "PegelonlineConnector", "last_successful_fetch": now - timedelta(days=10)},
        {"connector_class": "UBAConnector", "last_successful_fetch": None},
    ]
    await _make_client(_session_with_rows(rows))
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/metadata/layers?town=aalen")
    finally:
        _teardown()

    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"town", "layers"}
    by_key = {item["layer_key"]: item for item in data["layers"]}
    assert len(by_key) == len(LAYER_METADATA_REGISTRY)
    for item in data["layers"]:
        assert EXPECTED_ITEM_KEYS <= set(item.keys())
        assert set(item.keys()) == EXPECTED_ITEM_KEYS
    assert by_key["transit"]["status"] == "ok"
    assert by_key["water"]["status"] == "stale"
    assert by_key["airQuality"]["status"] == "never_fetched"
    assert by_key["fernwaerme"]["status"] == "static"
    assert by_key["transit"]["last_updated"] is not None
    assert by_key["airQuality"]["last_updated"] is None


@pytest.mark.asyncio
async def test_endpoint_db_failure_falls_back_to_never_fetched():
    session = AsyncMock()
    session.execute.side_effect = RuntimeError("no sources table")
    await _make_client(session)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/metadata/layers?town=aalen")
    finally:
        _teardown()

    assert resp.status_code == 200
    for item in resp.json()["layers"]:
        meta = LAYER_METADATA_REGISTRY[item["layer_key"]]
        expected = "never_fetched" if meta["connector_classes"] else "static"
        assert item["status"] == expected, item["layer_key"]


@pytest.mark.asyncio
async def test_endpoint_unknown_town_404():
    await _make_client(_session_with_rows([]))
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.get("/api/metadata/layers?town=notexist")
    finally:
        _teardown()
    assert resp.status_code == 404


# ── registry links ───────────────────────────────────────────────────────────


def test_registry_has_no_mobidata_layer():
    assert "mobiData" not in LAYER_METADATA_REGISTRY


def test_registry_energy_is_fed_by_mastr_only():
    assert LAYER_METADATA_REGISTRY["energy"]["connector_classes"] == ["MastrConnector"]


def test_registry_road_noise_has_no_connector():
    assert LAYER_METADATA_REGISTRY["roadNoise"]["connector_classes"] == []


def test_registry_lubw_environment_is_fed_by_lubw_wfs():
    entry = LAYER_METADATA_REGISTRY["lubwEnv"]
    assert entry["connector_classes"] == ["LubwWfsConnector"]
    assert entry["data_type"] == "STATIC"
    assert entry["update_interval_seconds"] is None
    assert entry["source_name"]
