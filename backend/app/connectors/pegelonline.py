"""PegelonlineConnector: fetches water level data from PEGELONLINE (WSV/BfG).

Implements WATR-01: retrieves current water levels for Neckar gauging stations
and writes readings to the water_readings hypertable.

PEGELONLINE API:
    GET https://www.pegelonline.wsv.de/webservices/rest-api/v2/stations.json
        ?waters=NECKAR&includeTimeseries=true&includeCurrentMeasurement=true

License: Datenlizenz Deutschland – Zero – Version 2.0
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.connectors.base import BaseConnector, Observation
from app.config import ConnectorConfig, Town
from app.models.pegelonline import PegelonlineStation


PEGELONLINE_API_URL = "https://www.pegelonline.wsv.de/webservices/rest-api/v2"


class PegelonlineConnector(BaseConnector):
    """Fetches Neckar water level data from the PEGELONLINE REST API.

    Config keys (from ConnectorConfig.config dict):
        station_uuids: list[str]  — If non-empty, only these UUIDs are fetched.
                                    Empty list means fetch ALL Neckar stations.
        attribution: str          — Attribution string for data provenance.
    """

    def __init__(self, config: ConnectorConfig, town: Town) -> None:
        super().__init__(config, town)
        # Maps PEGELONLINE station UUID -> features table UUID
        self._feature_ids: dict[str, str] = {}

    async def fetch(self) -> list[dict]:
        """Fetch current measurements for Neckar stations from PEGELONLINE API.

        If config key 'station_uuids' is a non-empty list, only those stations
        are returned. Empty list means return all Neckar stations.

        Returns:
            List of raw station dicts from the API.

        Raises:
            ValueError: If the (optionally filtered) result is empty.
            httpx.HTTPError: On network/HTTP failure.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{PEGELONLINE_API_URL}/stations.json",
                params={
                    "waters": "NECKAR",
                    "includeTimeseries": "true",
                    "includeCurrentMeasurement": "true",
                },
            )
            response.raise_for_status()
            stations: list[dict] = response.json()

        station_uuids: list[str] = self.config.config.get("station_uuids", [])
        if station_uuids:
            uuid_set = set(station_uuids)
            stations = [s for s in stations if s.get("uuid") in uuid_set]

        if not stations:
            raise ValueError(
                "PEGELONLINE returned no stations. "
                f"station_uuids filter: {station_uuids or 'none (all Neckar)'}"
            )

        return stations

    def normalize(self, raw: list[dict]) -> list[Observation]:
        """Transform raw station list into Observations.

        Requires self._feature_ids to be populated by run() before calling.
        Produces one Observation per station with domain="water".
        Stations with no current measurement produce Observation(level_cm=None).

        Args:
            raw: List of station dicts returned by fetch().

        Returns:
            List of Observation objects with domain="water".
        """
        observations: list[Observation] = []

        for station_dict in raw:
            try:
                station = PegelonlineStation.model_validate(station_dict)
            except Exception:
                continue

            feature_id = self._feature_ids.get(station.uuid, "")

            # Parse the ISO 8601 timestamp from the W timeseries
            ts_str = station.current_timestamp()
            ts: datetime | None = None
            if ts_str:
                try:
                    ts = datetime.fromisoformat(ts_str)
                except (ValueError, TypeError):
                    ts = None

            observations.append(
                Observation(
                    feature_id=feature_id,
                    domain="water",
                    values={
                        "level_cm": station.current_level_cm(),
                        "flow_m3s": None,
                    },
                    timestamp=ts,
                    source_id=f"pegelonline:{station.uuid}",
                )
            )

        return observations

    async def run(self) -> None:
        """Full pipeline with per-station feature upsert before fetch/normalize/persist.

        Overrides BaseConnector.run() to:
        1. Fetch raw station list first (to discover stations when station_uuids=[])
        2. Upsert each station as a spatial feature in the features table
        3. Normalize into Observations (using cached _feature_ids)
        4. Persist to water_readings
        5. Update staleness timestamp
        """
        attribution = self.config.config.get(
            "attribution",
            "PEGELONLINE (WSV / BfG), Datenlizenz Deutschland – Zero – Version 2.0",
        )

        # Step 1: fetch raw station list
        raw = await self.fetch()

        # Step 2: parse stations and upsert features
        for station_dict in raw:
            try:
                station = PegelonlineStation.model_validate(station_dict)
            except Exception:
                continue

            feature_id = await self.upsert_feature(
                source_id=f"pegelonline:{station.uuid}",
                domain="water",
                geometry_wkt=f"POINT({station.longitude} {station.latitude})",
                properties={
                    "station_name": station.shortname,
                    "river": station.water.longname,
                    "attribution": attribution,
                },
            )
            self._feature_ids[station.uuid] = feature_id

        # Step 3-5: normalize → persist → update staleness
        observations = self.normalize(raw)
        await self.persist(observations)
        await self._update_staleness()
