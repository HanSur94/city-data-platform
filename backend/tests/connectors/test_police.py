"""Tests for PoliceConnector cleanup SQL.

The database driver is asyncpg, which cannot take a text bind cast to interval:
the cleanup uses make_interval(days => :days) with an integer bind.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import ConnectorConfig, Town
from app.connectors.police import PoliceConnector


@pytest.fixture
def connector(aalen_town: Town) -> PoliceConnector:
    config = ConnectorConfig(
        connector_class="PoliceConnector", poll_interval_seconds=900, enabled=True, config={}
    )
    return PoliceConnector(config=config, town=aalen_town)


def _session_factory(session: AsyncMock) -> MagicMock:
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=session)
    context.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=context)


@pytest.mark.asyncio
async def test_cleanup_uses_make_interval_with_integer_bind(connector: PoliceConnector) -> None:
    session = AsyncMock()
    session.execute.return_value = MagicMock(rowcount=2)

    with patch("app.db.AsyncSessionLocal", _session_factory(session)):
        await connector._cleanup_old_reports(7)

    session.execute.assert_awaited_once()
    statement, params = session.execute.await_args.args
    sql = str(statement)
    assert "make_interval(days => :days)" in sql
    assert "::interval" not in sql
    assert params == {"town_id": "aalen", "days": 7}
    assert isinstance(params["days"], int)
    session.commit.assert_awaited_once()
