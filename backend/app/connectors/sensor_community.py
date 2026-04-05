"""SensorCommunityConnector: fetches citizen-science air quality sensor data.

Implements WAIR-04: retrieves SDS011/SPS30 sensors within 25km of the
configured town's bounding box center and writes PM10/PM2.5 readings
to air_quality_readings.

Sensor.community API:
    GET https://data.sensor.community/airrohr/v1/filter/?area=48.84,10.09,25
    Headers: User-Agent: city-data-platform/0.1 (open-source city dashboard)
    Response: [{sensor, location, sensordatavalues: [{value_type, value}]}]
    P1 = PM10, P2 = PM2.5
"""
from __future__ import annotations

from typing import Any

import httpx

from app.connectors.base import BaseConnector, Observation
from app.config import ConnectorConfig, Town
from app.models.sensor_community import SensorReading


SENSOR_COMMUNITY_URL = "https://data.sensor.community/airrohr/v1/filter/"
USER_AGENT = "city-data-platform/0.1 (open-source city dashboard)"
RADIUS_KM = 25
SUPPORTED_SENSOR_TYPES = {"SDS011", "SPS30"}


class SensorCommunityConnector(BaseConnector):
    """Fetches citizen-science PM10/PM2.5 data from Sensor.community.

    Queries sensors within 25km of the town's bounding box center.
    Only SDS011 and SPS30 sensor types are processed — other types are skipped.

    The User-Agent header is mandatory (Sensor.community policy) and identifies
    this as an open-source city dashboard.
    """

    def __init__(self, config: ConnectorConfig, town: Town) -> None:
        super().__init__(config, town)
        self._feature_ids: dict[int, str] = {}

    def _bbox_center(self) -> tuple[float, float]:
        """Compute the center of the town's bounding box.

        Returns:
            (lat, lon) tuple of the bounding box center.
        """
        bbox = self.town.bbox
        lat = (bbox.lat_min + bbox.lat_max) / 2
        lon = (bbox.lon_min + bbox.lon_max) / 2
        return lat, lon

    async def fetch(self) -> list[dict]:
        """Fetch sensor readings from Sensor.community within 25km of town center.

        Returns:
            List of raw sensor entry dicts from the API.

        Raises:
            ValueError: If response list is empty (no sensors found).
            httpx.HTTPError: On network/HTTP failure.
        """
        lat, lon = self._bbox_center()
        area_param = f"{lat},{lon},{RADIUS_KM}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                SENSOR_COMMUNITY_URL,
                params={"area": area_param},
                headers={"User-Agent": USER_AGENT},
            )
            response.raise_for_status()
            data = response.json()

        if not data:
            raise ValueError(
                f"Sensor.community returned empty list for area {area_param}"
            )
        return data

    def normalize(self, raw: list[dict]) -> list[Observation]:
        """Transform Sensor.community response into Observations.

        Requires self._feature_ids to be populated by run() before this is called.
        Filters to only SDS011 and SPS30 sensors. Missing P1/P2 values become None.

        Args:
            raw: List of sensor entry dicts from fetch().

        Returns:
            List of Observation objects with domain='air_quality'.
        """
        observations: list[Observation] = []

        for entry in raw:
            try:
                reading = SensorReading.model_validate(entry)
            except Exception:
                continue

            if reading.sensor_type not in SUPPORTED_SENSOR_TYPES:
                continue

            feature_id = self._feature_ids.get(reading.sensor_id)
            if feature_id is None:
                continue

            observations.append(
                Observation(
                    feature_id=feature_id,
                    domain="air_quality",
                    values={
                        "pm10": reading.pm10,
                        "pm25": reading.pm25,
                    },
                    timestamp=None,  # Use current time in persist()
                    source_id=str(reading.sensor_id),
                )
            )

        return observations

    async def run(self) -> None:
        """Full pipeline with per-sensor feature upsert before normalize/persist.

        Overrides BaseConnector.run() to:
        1. Fetch raw sensor list
        2. Upsert a feature for each SDS011/SPS30 sensor, cache UUIDs
        3. Normalize into Observations (using cached feature_ids)
        4. Persist to air_quality_readings
        5. Update staleness timestamp
        """
        raw = await self.fetch()

        # Upsert a feature for each supported sensor
        self._feature_ids = {}
        for entry in raw:
            sensor = entry.get("sensor", {})
            sensor_type_name = sensor.get("sensor_type", {}).get("name", "")
            if sensor_type_name not in SUPPORTED_SENSOR_TYPES:
                continue

            sensor_id = sensor.get("id")
            if sensor_id is None:
                continue

            location = entry.get("location", {})
            try:
                lat = float(location.get("latitude", 0))
                lon = float(location.get("longitude", 0))
            except (TypeError, ValueError):
                lat = 0.0
                lon = 0.0

            feature_id = await self.upsert_feature(
                source_id=str(sensor_id),
                domain="air_quality",
                geometry_wkt=f"POINT({lon} {lat})",
                properties={
                    "sensor_id": sensor_id,
                    "sensor_type": sensor_type_name,
                    "attribution": "Sensor.community (CC BY 4.0)",
                },
            )
            self._feature_ids[sensor_id] = feature_id

        observations = self.normalize(raw)
        await self.persist(observations)
        await self._update_staleness()
