"""Tests for the shared Overpass helper and its use by the four OSM connectors.

All HTTP traffic goes through httpx.MockTransport — no test touches the network.
"""
from __future__ import annotations

import functools
from typing import Any
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs

import httpx
import pytest

from app.config import ConnectorConfig, Town
from app.connectors import overpass_client
from app.connectors.cycling import CyclingInfraConnector
from app.connectors.osm_buildings import OsmBuildingsConnector
from app.connectors.overpass_client import (
    DEFAULT_OVERPASS_URLS,
    OVERPASS_USER_AGENT,
    overpass_query,
    overpass_urls_from_config,
)
from app.connectors.overpass_community import OverpassCommunityConnector
from app.connectors.overpass_roadworks import OverpassRoadworksConnector

MIRROR_A = "https://mirror-a.example/api/interpreter"
MIRROR_B = "https://mirror-b.example/api/interpreter"
OK_BODY: dict[str, Any] = {"elements": [{"type": "node", "id": 1}]}


def _transport(behaviour: dict[str, Any], seen: list[httpx.Request]) -> httpx.MockTransport:
    """Build a transport; behaviour maps host -> response / exception per request."""

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        action = behaviour[request.url.host]
        if isinstance(action, Exception):
            raise action
        if isinstance(action, httpx.Response):
            return action
        status, payload = action
        if isinstance(payload, (dict, list)):
            return httpx.Response(status, json=payload)
        return httpx.Response(status, text=payload)

    return httpx.MockTransport(handler)


# ---------------------------------------------------------------------------
# Helper behaviour
# ---------------------------------------------------------------------------


async def test_first_mirror_wins_single_request() -> None:
    seen: list[httpx.Request] = []
    transport = _transport({"mirror-a.example": (200, OK_BODY)}, seen)

    result = await overpass_query("QUERY-1", urls=[MIRROR_A, MIRROR_B], transport=transport)

    assert result == OK_BODY
    assert len(seen) == 1
    request = seen[0]
    assert request.method == "POST"
    assert parse_qs(request.content.decode())["data"] == ["QUERY-1"]
    assert "city-data-platform" in request.headers["user-agent"]
    assert request.headers["user-agent"] == OVERPASS_USER_AGENT


async def test_not_acceptable_falls_through_in_order() -> None:
    seen: list[httpx.Request] = []
    transport = _transport(
        {"mirror-a.example": (406, "not acceptable"), "mirror-b.example": (200, OK_BODY)},
        seen,
    )

    result = await overpass_query("q", urls=[MIRROR_A, MIRROR_B], transport=transport)

    assert result == OK_BODY
    assert [r.url.host for r in seen] == ["mirror-a.example", "mirror-b.example"]


@pytest.mark.parametrize(
    "first",
    [
        (429, "slow down"),
        (502, "bad gateway"),
        (504, "gateway timeout"),
        httpx.ConnectError("refused"),
        httpx.ReadTimeout("timed out"),
    ],
    ids=["429", "502", "504", "connect-error", "read-timeout"],
)
async def test_transient_failures_fall_through(first: Any) -> None:
    seen: list[httpx.Request] = []
    transport = _transport({"mirror-a.example": first, "mirror-b.example": (200, OK_BODY)}, seen)

    result = await overpass_query("q", urls=[MIRROR_A, MIRROR_B], transport=transport)

    assert result == OK_BODY
    assert [r.url.host for r in seen] == ["mirror-a.example", "mirror-b.example"]


@pytest.mark.parametrize(
    "bad_body",
    [(200, "<html>runtime error</html>"), (200, {"remark": "no elements here"})],
    ids=["html-body", "json-without-elements"],
)
async def test_unusable_200_falls_through(bad_body: Any) -> None:
    seen: list[httpx.Request] = []
    transport = _transport({"mirror-a.example": bad_body, "mirror-b.example": (200, OK_BODY)}, seen)

    result = await overpass_query("q", urls=[MIRROR_A, MIRROR_B], transport=transport)

    assert result == OK_BODY
    assert len(seen) == 2


async def test_query_error_is_raised_without_asking_next_mirror() -> None:
    seen: list[httpx.Request] = []
    transport = _transport(
        {"mirror-a.example": (400, "bad query"), "mirror-b.example": (200, OK_BODY)}, seen
    )

    with pytest.raises(httpx.HTTPStatusError) as excinfo:
        await overpass_query("q", urls=[MIRROR_A, MIRROR_B], transport=transport)

    assert excinfo.value.response.status_code == 400
    assert [r.url.host for r in seen] == ["mirror-a.example"]


async def test_all_mirrors_failing_raises_last_error() -> None:
    seen: list[httpx.Request] = []
    transport = _transport(
        {"mirror-a.example": httpx.ConnectError("refused"), "mirror-b.example": (504, "timeout")},
        seen,
    )

    with pytest.raises(httpx.HTTPStatusError) as excinfo:
        await overpass_query("q", urls=[MIRROR_A, MIRROR_B], transport=transport)

    assert excinfo.value.response.status_code == 504
    assert len(seen) == 2


async def test_all_mirrors_unusable_body_raises_value_error() -> None:
    seen: list[httpx.Request] = []
    transport = _transport(
        {"mirror-a.example": (200, "<html/>"), "mirror-b.example": (200, {"x": 1})}, seen
    )

    with pytest.raises(ValueError):
        await overpass_query("q", urls=[MIRROR_A, MIRROR_B], transport=transport)


async def test_empty_url_list_raises_value_error() -> None:
    with pytest.raises(ValueError):
        await overpass_query("q", urls=[])


def test_urls_from_config_defaults_and_override() -> None:
    assert overpass_urls_from_config({}) == list(DEFAULT_OVERPASS_URLS)
    assert overpass_urls_from_config({"overpass_urls": None}) == list(DEFAULT_OVERPASS_URLS)
    assert overpass_urls_from_config({"overpass_urls": [MIRROR_A]}) == [MIRROR_A]


@pytest.mark.parametrize("bad", [[], [""], [MIRROR_A, 5], "https://x.example", 7])
def test_urls_from_config_rejects_bad_values(bad: Any) -> None:
    with pytest.raises(ValueError, match="overpass_urls"):
        overpass_urls_from_config({"overpass_urls": bad})


def test_helper_module_defines_no_connector() -> None:
    from app.connectors.base import BaseConnector

    subclasses = [
        obj
        for obj in vars(overpass_client).values()
        if isinstance(obj, type) and issubclass(obj, BaseConnector) and obj is not BaseConnector
    ]
    assert subclasses == []


# ---------------------------------------------------------------------------
# The four connectors go through the helper
# ---------------------------------------------------------------------------

CONNECTORS = [
    (OverpassCommunityConnector, "overpass_community"),
    (OverpassRoadworksConnector, "overpass_roadworks"),
    (OsmBuildingsConnector, "osm_buildings"),
    (CyclingInfraConnector, "cycling"),
]


@pytest.mark.parametrize("cls,module", CONNECTORS, ids=[m for _, m in CONNECTORS])
async def test_connectors_call_shared_helper(cls: type, module: str, aalen_town: Town) -> None:
    config = ConnectorConfig(
        connector_class=cls.__name__,
        poll_interval_seconds=3600,
        config={"overpass_urls": [MIRROR_A, MIRROR_B]},
    )
    connector = cls(config, aalen_town)
    helper = AsyncMock(return_value={"elements": []})

    with patch(f"app.connectors.{module}.overpass_query", helper):
        await connector.fetch()

    helper.assert_awaited_once()
    args, kwargs = helper.await_args
    assert kwargs["urls"] == [MIRROR_A, MIRROR_B]
    query = args[0]
    bbox = aalen_town.bbox
    if module == "osm_buildings":
        # Buildings use a tighter box around the town centre (unchanged behaviour).
        center_lat = (bbox.lat_min + bbox.lat_max) / 2
        center_lon = (bbox.lon_min + bbox.lon_max) / 2
        assert f"{center_lat - 0.02},{center_lon - 0.03}" in query
    else:
        assert f"{bbox.lat_min},{bbox.lon_min},{bbox.lat_max},{bbox.lon_max}" in query


# ---------------------------------------------------------------------------
# Tracer: OverpassCommunityConnector.run() end to end over a mock transport
# ---------------------------------------------------------------------------


def _community_connector(aalen_town: Town) -> OverpassCommunityConnector:
    config = ConnectorConfig(
        connector_class="OverpassCommunityConnector",
        poll_interval_seconds=3600,
        config={"overpass_urls": [MIRROR_A, MIRROR_B]},
    )
    return OverpassCommunityConnector(config, aalen_town)


async def test_tracer_run_falls_through_and_upserts(aalen_town: Town) -> None:
    school = {
        "elements": [
            {
                "type": "node",
                "id": 4711,
                "lat": 48.84,
                "lon": 10.09,
                "tags": {"amenity": "school", "name": "Testschule"},
            }
        ]
    }
    seen: list[httpx.Request] = []
    transport = _transport(
        {"mirror-a.example": (406, "not acceptable"), "mirror-b.example": (200, school)}, seen
    )
    connector = _community_connector(aalen_town)
    real = functools.partial(overpass_query, transport=transport)

    with (
        patch("app.connectors.overpass_community.overpass_query", real),
        patch.object(connector, "upsert_feature", new_callable=AsyncMock) as upsert,
        patch.object(connector, "_update_staleness", new_callable=AsyncMock) as staleness,
    ):
        await connector.run()

    assert [r.url.host for r in seen] == ["mirror-a.example", "mirror-b.example"]
    upsert.assert_awaited_once()
    assert upsert.await_args.kwargs["source_id"] == "osm:node:4711"
    assert upsert.await_args.kwargs["domain"] == "community"
    staleness.assert_awaited_once()


async def test_tracer_run_all_mirrors_fail_keeps_staleness_untouched(aalen_town: Town) -> None:
    seen: list[httpx.Request] = []
    transport = _transport(
        {"mirror-a.example": (502, "bad gateway"), "mirror-b.example": (502, "bad gateway")}, seen
    )
    connector = _community_connector(aalen_town)
    real = functools.partial(overpass_query, transport=transport)

    with (
        patch("app.connectors.overpass_community.overpass_query", real),
        patch.object(connector, "upsert_feature", new_callable=AsyncMock) as upsert,
        patch.object(connector, "_update_staleness", new_callable=AsyncMock) as staleness,
    ):
        with pytest.raises(httpx.HTTPStatusError):
            await connector.run()

    upsert.assert_not_awaited()
    staleness.assert_not_awaited()
