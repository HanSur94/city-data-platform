"""Tests for PLAT-09: Admin health endpoint with per-domain staleness thresholds."""
import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock

from app.main import app
from app.config import Town, TownBbox, ConnectorConfig
from app.routers.admin import classify_staleness, STALENESS_THRESHOLDS

MOCK_TOWN = Town(
    id="aalen",
    display_name="Aalen (Württemberg)",
    country="DE",
    bbox=TownBbox(lon_min=9.9, lat_min=48.7, lon_max=10.2, lat_max=48.9),
    connectors=[
        ConnectorConfig(
            connector_class="WeatherConnector",
            poll_interval_seconds=3600,
            enabled=True,
            config={},
        ),
        ConnectorConfig(
            connector_class="UBAConnector",
            poll_interval_seconds=3600,
            enabled=True,
            config={},
        ),
    ],
)


@pytest.fixture
async def client():
    from app.dependencies import get_current_town
    app.dependency_overrides[get_current_town] = lambda: MOCK_TOWN
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_admin_health_returns_200(client):
    """GET /api/admin/health?town=aalen returns 200."""
    with patch("app.routers.admin.get_db", return_value=AsyncMock()):
        resp = await client.get("/api/admin/health?town=aalen")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_health_response_structure(client):
    """Response contains summary dict with green/yellow/red/never_fetched keys."""
    with patch("app.routers.admin.get_db", return_value=AsyncMock()):
        resp = await client.get("/api/admin/health?town=aalen")
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    summary = data["summary"]
    for key in ("green", "yellow", "red", "never_fetched"):
        assert key in summary, f"Summary missing key: {key}"
    assert "connectors" in data
    assert "town" in data
    assert "town_display_name" in data
    assert "checked_at" in data


@pytest.mark.asyncio
async def test_admin_health_unknown_town_404(client):
    """Unknown town returns 404."""
    with patch("app.routers.admin.get_db", return_value=AsyncMock()):
        resp = await client.get("/api/admin/health?town=notexist")
    assert resp.status_code == 404


# ── Unit tests for classify_staleness ────────────────────────────────────────


def test_classify_staleness_never_fetched():
    """None last_fetch gives never_fetched status."""
    now = datetime.now(tz=timezone.utc)
    status, staleness = classify_staleness(None, now, "weather")
    assert status == "never_fetched"
    assert staleness is None


def test_classify_staleness_green():
    """Recent fetch within yellow threshold → green."""
    now = datetime.now(tz=timezone.utc)
    last_fetch = now - timedelta(minutes=30)  # 30 min — well within 1h yellow
    status, staleness = classify_staleness(last_fetch, now, "weather")
    assert status == "green"
    assert staleness is not None
    assert staleness < STALENESS_THRESHOLDS["weather"]["yellow"]


def test_classify_staleness_yellow():
    """Fetch between yellow and red threshold → yellow."""
    now = datetime.now(tz=timezone.utc)
    # weather yellow=3600, red=7200 — use 5400 (1.5h)
    last_fetch = now - timedelta(seconds=5400)
    status, staleness = classify_staleness(last_fetch, now, "weather")
    assert status == "yellow"


def test_classify_staleness_red():
    """Fetch beyond red threshold → red."""
    now = datetime.now(tz=timezone.utc)
    # weather red=7200 — use 10800 (3h)
    last_fetch = now - timedelta(seconds=10800)
    status, staleness = classify_staleness(last_fetch, now, "weather")
    assert status == "red"


def test_classify_staleness_transit_domain():
    """Transit domain has 1d/2d thresholds — 12h should be green."""
    now = datetime.now(tz=timezone.utc)
    last_fetch = now - timedelta(hours=12)
    status, staleness = classify_staleness(last_fetch, now, "transit")
    assert status == "green"


def test_classify_staleness_unknown_domain():
    """Unknown domain falls back to default thresholds without crashing."""
    now = datetime.now(tz=timezone.utc)
    # Very fresh — should be green regardless of domain
    last_fetch = now - timedelta(minutes=5)
    status, staleness = classify_staleness(last_fetch, now, "unknown_domain_xyz")
    assert status == "green"


def test_classify_staleness_naive_datetime():
    """Naive datetime (no tzinfo) is handled without crashing."""
    now = datetime.now(tz=timezone.utc)
    # Naive datetime as stored by some DB drivers
    last_fetch = datetime.utcnow() - timedelta(minutes=10)
    assert last_fetch.tzinfo is None
    status, staleness = classify_staleness(last_fetch, now, "weather")
    assert status in ("green", "yellow", "red", "never_fetched")
    assert staleness is not None


def test_staleness_thresholds_cover_all_expected_domains():
    """All 9 expected domains are present in STALENESS_THRESHOLDS."""
    expected = {
        "air_quality", "weather", "transit", "water",
        "traffic", "energy", "community", "infrastructure", "demographics",
    }
    assert expected.issubset(STALENESS_THRESHOLDS.keys())
