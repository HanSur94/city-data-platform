"""UBAConnector: fetches official air quality data from Umweltbundesamt (UBA).

Implements WAIR-03: retrieves PM10, NO2, O3 (and PM2.5 if available) for
a configured UBA station and writes non-null readings to air_quality_readings.

UBA API endpoint:
    GET https://luftdaten.umweltbundesamt.de/api-proxy/airquality/json
      ?station=238&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD
      &time_from=1&time_to=24&lang=de

Component IDs (from UBA meta):
    1=PM10, 2=SO2, 3=O3, 4=CO, 5=NO2, 9=PM2.5
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

import httpx

from app.connectors.base import BaseConnector, Observation
from app.config import ConnectorConfig, Town
from app.models.uba import UBAMeasurement


# Mapping from UBA component_id to Observation.values key
COMPONENT_MAP: dict[int, str] = {
    1: "pm10",
    2: "so2",
    3: "o3",
    4: "co",
    5: "no2",
    9: "pm25",
}

UBA_API_URL = "https://luftdaten.umweltbundesamt.de/api-proxy/airquality/json"


class UBAConnector(BaseConnector):
    """Fetches official air quality station data from the UBA REST API.

    Config keys (from ConnectorConfig.config dict):
        station_id: UBA station number (default 238 = Aalen DEBW029)
        lat: Station latitude (default 48.84)
        lon: Station longitude (default 10.09)
        attribution: Data attribution string (default "Umweltbundesamt (UBA)")
    """

    def __init__(self, config: ConnectorConfig, town: Town) -> None:
        super().__init__(config, town)
        self._feature_id: str | None = None

    async def fetch(self) -> dict:
        """Fetch today's air quality data for the configured station.

        Returns:
            Raw API response dict with 'data' key containing component readings.

        Raises:
            ValueError: If response 'data' is empty or missing.
            httpx.HTTPError: On network/HTTP failure.
        """
        station_id = self.config.config.get("station_id", 238)
        today = date.today().isoformat()

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                UBA_API_URL,
                params={
                    "station": station_id,
                    "date_from": today,
                    "date_to": today,
                    "time_from": 1,
                    "time_to": 24,
                    "lang": "de",
                },
            )
            response.raise_for_status()
            data = response.json()

        station_data = data.get("data", {})
        if not station_data:
            raise ValueError(
                f"UBA API returned empty data for station {station_id} on {today}"
            )
        return data

    def normalize(self, raw: dict) -> list[Observation]:
        """Transform UBA API response into Observations.

        Requires self._feature_id to be set by run() before this is called.

        The actual UBA API structure (verified against live API):
            data["238"] = {
                "<date_start>": [
                    <date_end>,        # str, ISO timestamp
                    <overall_index>,   # int
                    <status_flag>,     # int
                    [comp_id, value_raw_int, comp_index, value_str],  # component
                    [comp_id, ...],    # more components
                    ...
                ],
                ...
            }
        Each timestamp entry array starts with date_end (index 0), then an
        overall index (index 1), then a status flag (index 2), followed by
        zero or more component sub-arrays [comp_id, value_raw, comp_index, value_str].

        Args:
            raw: Dict returned by fetch() containing 'data' key.

        Returns:
            List of Observation objects, one per timestamp.
            Timestamps with all-None pollutant values are filtered out.
        """
        observations: list[Observation] = []
        station_id = self.config.config.get("station_id", 238)
        station_key = str(station_id)

        station_data = raw.get("data", {}).get(station_key, {})
        if not station_data:
            return observations

        feature_id = self._feature_id or ""

        # station_data: {date_start_str: [date_end_str, overall_idx, status, [comp], ...]}
        for date_start_str, time_entry in station_data.items():
            if not isinstance(time_entry, list) or len(time_entry) < 1:
                continue

            # First element is the date_end timestamp
            date_end_raw = time_entry[0]

            # Elements from index 3 onward are component sub-arrays
            # [comp_id, value_int_or_raw, comp_index, value_str]
            values: dict[str, float | None] = {}

            for item in time_entry[3:]:
                if not isinstance(item, list) or len(item) < 1:
                    continue
                try:
                    comp_id = int(item[0])
                except (TypeError, ValueError):
                    continue

                pollutant = COMPONENT_MAP.get(comp_id)
                if pollutant is None:
                    continue

                # Prefer the string value (index 3) for precision; fallback to index 1
                value_raw = item[3] if len(item) > 3 else (item[1] if len(item) > 1 else None)
                comp_index = item[2] if len(item) > 2 else None

                try:
                    meas = UBAMeasurement.model_validate({
                        "station_id": station_id,
                        "component_id": comp_id,
                        "date_end": date_end_raw,
                        "value": value_raw,
                        "index": comp_index,
                    })
                except Exception:
                    continue

                values[pollutant] = meas.value

            # Only emit observations with at least one non-None value
            if values and any(v is not None for v in values.values()):
                try:
                    from datetime import datetime
                    ts = datetime.fromisoformat(str(date_end_raw))
                except (ValueError, TypeError):
                    ts = None

                observations.append(
                    Observation(
                        feature_id=feature_id,
                        domain="air_quality",
                        values=values,
                        timestamp=ts,
                        source_id=f"uba:{station_id}",
                    )
                )

        return observations

    async def run(self) -> None:
        """Full pipeline with feature upsert before fetch/normalize/persist.

        Overrides BaseConnector.run() to:
        1. Upsert the station feature once and cache the UUID
        2. Fetch raw data
        3. Normalize into Observations (using cached feature_id)
        4. Persist to air_quality_readings
        5. Update staleness timestamp
        """
        lat = self.config.config.get("lat", 48.84)
        lon = self.config.config.get("lon", 10.09)
        station_id = self.config.config.get("station_id", 238)

        self._feature_id = await self.upsert_feature(
            source_id=f"uba:{station_id}",
            domain="air_quality",
            geometry_wkt=f"POINT({lon} {lat})",
            properties={
                "station_id": station_id,
                "attribution": self.config.config.get(
                    "attribution", "Umweltbundesamt (UBA)"
                ),
            },
        )
        raw = await self.fetch()
        observations = self.normalize(raw)
        await self.persist(observations)
        await self._update_staleness()
