"""Tests for register_sources() and fault-tolerant lifespan registration (F1)."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import ConnectorConfig, Town, TownBbox
from app.scheduler import register_sources


def _town(connectors: list[ConnectorConfig]) -> Town:
    return Town(
        id="aalen",
        display_name="Aalen",
        country="DE",
        bbox=TownBbox(lon_min=9.9, lat_min=48.7, lon_max=10.2, lat_max=48.9),
        connectors=connectors,
    )


def _mock_session_local():
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session, MagicMock(return_value=session)


@pytest.mark.asyncio
async def test_register_sources_upserts_enabled_registered_connectors():
    town = _town(
        [
            ConnectorConfig(connector_class="UBAConnector", poll_interval_seconds=3600),
            ConnectorConfig(
                connector_class="TomTomConnector",
                poll_interval_seconds=300,
                config={"api_key": "secret-test-key"},
            ),
            ConnectorConfig(connector_class="LadesaeulenConnector", enabled=False),
            ConnectorConfig(connector_class="NoSuchConnector"),
        ]
    )
    session, session_local = _mock_session_local()

    with patch("app.db.AsyncSessionLocal", session_local):
        n = await register_sources(town)

    assert n == 2
    assert session.execute.call_count == 2
    all_params = [c.args[1] for c in session.execute.call_args_list]
    by_id = {p["id"]: p for p in all_params}
    assert set(by_id) == {"aalen:UBAConnector", "aalen:TomTomConnector"}
    assert by_id["aalen:UBAConnector"]["domain"] == "air_quality"
    assert by_id["aalen:UBAConnector"]["poll_interval_seconds"] == 3600
    assert by_id["aalen:TomTomConnector"]["domain"] == "traffic"
    assert by_id["aalen:TomTomConnector"]["poll_interval_seconds"] == 300
    for params in all_params:
        assert "config" not in params
        assert "secret-test-key" not in str(params)
    for call in session.execute.call_args_list:
        sql = str(call.args[0])
        assert "ON CONFLICT (id)" in sql
        assert "last_successful_fetch" not in sql
        assert "validation_error_count" not in sql
        assert "config" not in sql.replace("connector_class", "")
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_register_sources_no_enabled_connectors():
    session, session_local = _mock_session_local()
    with patch("app.db.AsyncSessionLocal", session_local):
        n = await register_sources(_town([]))
    assert n == 0
    session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_register_sources_skips_duplicate_connector_class():
    town = _town(
        [
            ConnectorConfig(connector_class="UBAConnector"),
            ConnectorConfig(connector_class="UBAConnector"),
        ]
    )
    session, session_local = _mock_session_local()
    with patch("app.db.AsyncSessionLocal", session_local):
        n = await register_sources(town)
    assert n == 1
    assert session.execute.call_count == 1


@pytest.mark.asyncio
async def test_lifespan_survives_sources_write_failure():
    from app.main import app, lifespan

    town = _town([])
    session, session_local = _mock_session_local()
    mock_scheduler = MagicMock()
    mock_setup = MagicMock()

    with (
        patch("app.main.load_town", return_value=town),
        patch("app.main.set_current_town"),
        patch("app.main.AsyncSessionLocal", session_local),
        patch(
            "app.main.register_sources",
            AsyncMock(side_effect=OSError("db down")),
        ),
        patch("app.main.setup_scheduler", mock_setup),
        patch("app.main.scheduler", mock_scheduler),
    ):
        async with lifespan(app):
            pass

    mock_setup.assert_called_once()
    mock_scheduler.start.assert_called_once()
