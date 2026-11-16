"""Shared Overpass API client for all OpenStreetMap connectors.

Every Overpass request of the community, roadworks, buildings and cycling
connectors goes through overpass_query():

- it identifies itself with a descriptive User-Agent (the public Overpass
  servers reject anonymous default client names with HTTP 406),
- it tries a list of public mirrors in order and moves on to the next mirror
  after a connection error, a timeout, HTTP 406, 429 or 5xx, or an answer
  that is not an Overpass JSON document,
- it raises the last error when every mirror failed,
- the mirror list comes from the connector config key ``overpass_urls`` when
  present, otherwise from DEFAULT_OVERPASS_URLS.

Two things keep a busy public server from meaning "no data until the next
daily poll":

- calls are serialised through one process-wide lock. Several connectors start
  together, and the public instances answer simultaneous requests from one
  address with HTTP 429;
- when every mirror failed, the whole list is tried again after a pause
  (OVERPASS_ROUNDS rounds, OVERPASS_ROUND_DELAY_S seconds apart). The pause is an
  ``asyncio.sleep``, so the event loop stays free.

License: OpenStreetMap data (c) OpenStreetMap contributors, ODbL 1.0
Attribution: https://www.openstreetmap.org/copyright
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping, Sequence
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Names the open-source project only — no person, e-mail or host data.
OVERPASS_USER_AGENT = "city-data-platform/0.1 (open-source city dashboard)"

# Public Overpass instances, tried in this order. Overridable per connector with
# the config key ``overpass_urls``.
DEFAULT_OVERPASS_URLS: tuple[str, ...] = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)

# Statuses that say "this mirror is busy / refuses this client", not "your query is wrong".
_MIRROR_PROBLEM_STATUSES = frozenset({406, 429})

# How often the whole mirror list is tried, and the pause between two rounds.
OVERPASS_ROUNDS = 3
OVERPASS_ROUND_DELAY_S = 60.0

# Fallback mirrors get a shorter time limit than the first endpoint. Observed on
# 2026-11-16: two public mirrors accepted the connection and then sent nothing, and
# with the full limit (up to 300 s for the buildings query) every round would hang
# for minutes while the process-wide lock is held.
OVERPASS_FALLBACK_TIMEOUT_S = 60.0

# One Overpass request at a time for the whole process (see module docstring).
_OVERPASS_LOCK = asyncio.Lock()


def overpass_urls_from_config(config: Mapping[str, Any]) -> list[str]:
    """Return the Overpass endpoint list for a connector config dict.

    Raises:
        ValueError: ``overpass_urls`` is present but not a non-empty list of
            non-empty strings.
    """
    value = config.get("overpass_urls")
    if value is None:
        return list(DEFAULT_OVERPASS_URLS)
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(item, str) and item.strip() for item in value)
    ):
        raise ValueError("config key overpass_urls must be a non-empty list of URL strings")
    return list(value)


def _status_error(url: str, response: httpx.Response) -> httpx.HTTPStatusError:
    return httpx.HTTPStatusError(
        f"Overpass mirror {url} answered HTTP {response.status_code}",
        request=response.request,
        response=response,
    )


async def overpass_query(
    query: str,
    *,
    urls: Sequence[str] | None = None,
    timeout: float = 90.0,
    transport: httpx.AsyncBaseTransport | None = None,
    rounds: int | None = None,
    round_delay: float | None = None,
) -> dict[str, Any]:
    """POST an Overpass QL query and return the parsed JSON document.

    Args:
        query: Overpass QL text.
        urls: Endpoints to try in order (default: DEFAULT_OVERPASS_URLS).
        timeout: Per-request timeout in seconds.
        transport: Optional httpx transport (tests inject a MockTransport).
        rounds: How often the whole endpoint list is tried (default: OVERPASS_ROUNDS).
        round_delay: Seconds to wait between two rounds (default: OVERPASS_ROUND_DELAY_S).

    Returns:
        Parsed response dict containing an ``elements`` key.

    Raises:
        ValueError: Empty endpoint list, or the last mirror answered with something
            that is not an Overpass JSON document.
        httpx.HTTPStatusError: A mirror rejected the query (4xx other than 406/429),
            or the last mirror answered 406, 429 or 5xx.
        httpx.TransportError: The last mirror could not be reached.
    """
    endpoints = list(urls) if urls is not None else list(DEFAULT_OVERPASS_URLS)
    if not endpoints:
        raise ValueError("No Overpass endpoints configured")

    n_rounds = max(1, OVERPASS_ROUNDS if rounds is None else rounds)
    delay = OVERPASS_ROUND_DELAY_S if round_delay is None else round_delay

    async with _OVERPASS_LOCK:
        last_error: Exception | None = None
        for round_no in range(1, n_rounds + 1):
            try:
                return await _query_mirrors_once(query, endpoints, timeout, transport)
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status not in _MIRROR_PROBLEM_STATUSES and status < 500:
                    raise  # the query itself was rejected; retrying cannot help
                last_error = exc
            except (httpx.TransportError, ValueError) as exc:
                last_error = exc
            if round_no < n_rounds:
                logger.warning(
                    "All Overpass mirrors failed (round %d of %d); retrying in %.0f s",
                    round_no, n_rounds, delay,
                )
                await asyncio.sleep(delay)

    assert last_error is not None  # n_rounds >= 1, so at least one round ran
    raise last_error


async def _query_mirrors_once(
    query: str,
    endpoints: Sequence[str],
    timeout: float,
    transport: httpx.AsyncBaseTransport | None,
) -> dict[str, Any]:
    """Try every endpoint once, in order. Raises the last error when all failed."""
    last_error: Exception | None = None
    async with httpx.AsyncClient(
        timeout=timeout,
        headers={"User-Agent": OVERPASS_USER_AGENT},
        transport=transport,
    ) as client:
        for index, url in enumerate(endpoints):
            limit = timeout if index == 0 else min(timeout, OVERPASS_FALLBACK_TIMEOUT_S)
            try:
                response = await client.post(url, data={"data": query}, timeout=limit)
            except httpx.TransportError as exc:
                logger.warning("Overpass mirror %s unreachable: %s", url, exc)
                last_error = exc
                continue

            status = response.status_code
            if status in _MIRROR_PROBLEM_STATUSES or status >= 500:
                logger.warning("Overpass mirror %s answered HTTP %d", url, status)
                last_error = _status_error(url, response)
                continue
            response.raise_for_status()

            try:
                data = response.json()
            except ValueError:
                logger.warning("Overpass mirror %s answered with a non-JSON body", url)
                last_error = ValueError(f"Overpass mirror {url} answered with a non-JSON body")
                continue
            if not isinstance(data, dict) or "elements" not in data:
                logger.warning("Overpass mirror %s answered without an 'elements' key", url)
                last_error = ValueError(
                    f"Overpass mirror {url} answered without an 'elements' key"
                )
                continue

            logger.info("Overpass mirror %s answered with %d elements", url, len(data["elements"]))
            return data

    assert last_error is not None  # endpoints is non-empty, so the loop ran at least once
    raise last_error
