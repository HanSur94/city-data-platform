"""BaseConnector: abstract base class for all data connectors.

All Phase 2+ connectors MUST inherit from BaseConnector and implement:
- fetch(): retrieve raw data from the external source
- normalize(): transform raw data into Observation objects

The persist() method is provided by the base class. Subclasses should
NOT override persist() — this ensures all data goes through the same
database write path.

Staleness tracking: run() calls _update_staleness() after a successful
persist(). Subclasses that override run() MUST call
`await self._update_staleness()` at the end of their implementation.

Usage example:
    class GTFSConnector(BaseConnector):
        async def fetch(self) -> bytes:
            async with httpx.AsyncClient() as client:
                r = await client.get(self.config.config["gtfs_url"])
                return r.content

        def normalize(self, raw: bytes) -> list[Observation]:
            # parse GTFS feed
            return [Observation(...)]
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.config import ConnectorConfig, Town


@dataclass
class Observation:
    """A normalized data observation ready to be persisted.

    Matches the schema expected by domain hypertables.
    `feature_id` must reference an existing row in the `features` table.
    """
    feature_id: str
    domain: str       # "air_quality", "transit", "water", "energy", "weather", "traffic"
    values: dict      # domain-specific key-value pairs (e.g. {"pm10": 12.5})
    timestamp: datetime | None = field(default=None)
    source_id: str | None = field(default=None)


class BaseConnector(ABC):
    """Abstract base class for all city data connectors.

    Constructor args:
        config: ConnectorConfig with connector_class, poll_interval, etc.
        town: Town object for the town this connector serves.

    Concrete subclasses must implement fetch() and normalize().

    Session management: do NOT hold a session at class level. Sessions are
    created fresh per job run inside persist(), upsert_feature(), and
    _update_staleness(). This prevents session lifetime issues across
    APScheduler job runs (Pitfall 8).
    """

    def __init__(self, config: ConnectorConfig, town: Town) -> None:
        self.config = config
        self.town = town

    @abstractmethod
    async def fetch(self) -> Any:
        """Fetch raw data from the external source.

        Returns:
            Raw payload — bytes, dict, str, or any format the connector
            receives from the upstream API. Not validated here.

        Raises:
            httpx.HTTPError: On network failure.
            ValueError: If the upstream returns an empty or malformed response.
        """
        ...

    @abstractmethod
    def normalize(self, raw: Any) -> list[Observation]:
        """Transform raw payload into a list of normalized Observations.

        Args:
            raw: The value returned by fetch().

        Returns:
            List of Observation objects ready for persist(). May be empty
            if raw data contained no valid readings.
        """
        ...

    async def run(self) -> None:
        """Full pipeline: fetch -> normalize -> persist -> update staleness.

        Subclasses that need to override run() (e.g. to upsert features first)
        MUST call `await self._update_staleness()` on successful completion.
        Alternatively, call `await super().run()` if the default pipeline is
        sufficient after custom setup.
        """
        raw = await self.fetch()
        observations = self.normalize(raw)
        await self.persist(observations)
        await self._update_staleness()

    async def persist(self, observations: list[Observation]) -> None:
        """Write observations to the correct domain hypertable.

        Opens a fresh AsyncSession per call — ensures session lifetime
        matches one scheduler job run. Do not hold sessions at class level.

        Subclasses should NOT override this method.
        """
        if not observations:
            return
        from app.db import AsyncSessionLocal
        from sqlalchemy import text

        async with AsyncSessionLocal() as session:
            for obs in observations:
                ts = obs.timestamp or __import__('datetime').datetime.now(__import__('datetime').timezone.utc)
                if obs.domain == "air_quality":
                    await session.execute(
                        text(
                            "INSERT INTO air_quality_readings "
                            "(time, feature_id, pm25, pm10, no2, o3, aqi) "
                            "VALUES (:time, :feature_id, :pm25, :pm10, :no2, :o3, :aqi)"
                        ),
                        {
                            "time": ts,
                            "feature_id": obs.feature_id,
                            "pm25": obs.values.get("pm25"),
                            "pm10": obs.values.get("pm10"),
                            "no2": obs.values.get("no2"),
                            "o3": obs.values.get("o3"),
                            "aqi": obs.values.get("aqi"),
                        },
                    )
                elif obs.domain == "weather":
                    await session.execute(
                        text(
                            "INSERT INTO weather_readings "
                            "(time, feature_id, temperature, dew_point, pressure_msl, "
                            "wind_speed, wind_direction, cloud_cover, condition, icon, "
                            "precipitation_10, precipitation_30, precipitation_60, observation_type) "
                            "VALUES (:time, :feature_id, :temperature, :dew_point, :pressure_msl, "
                            ":wind_speed, :wind_direction, :cloud_cover, :condition, :icon, "
                            ":precipitation_10, :precipitation_30, :precipitation_60, :observation_type)"
                        ),
                        {
                            "time": ts,
                            "feature_id": obs.feature_id,
                            "temperature": obs.values.get("temperature"),
                            "dew_point": obs.values.get("dew_point"),
                            "pressure_msl": obs.values.get("pressure_msl"),
                            "wind_speed": obs.values.get("wind_speed"),
                            "wind_direction": obs.values.get("wind_direction"),
                            "cloud_cover": obs.values.get("cloud_cover"),
                            "condition": obs.values.get("condition"),
                            "icon": obs.values.get("icon"),
                            "precipitation_10": obs.values.get("precipitation_10"),
                            "precipitation_30": obs.values.get("precipitation_30"),
                            "precipitation_60": obs.values.get("precipitation_60"),
                            "observation_type": obs.values.get("observation_type", "current"),
                        },
                    )
                elif obs.domain == "transit":
                    await session.execute(
                        text(
                            "INSERT INTO transit_positions "
                            "(time, feature_id, trip_id, route_id, delay_seconds) "
                            "VALUES (:time, :feature_id, :trip_id, :route_id, :delay_seconds)"
                        ),
                        {
                            "time": ts,
                            "feature_id": obs.feature_id,
                            "trip_id": obs.values.get("trip_id"),
                            "route_id": obs.values.get("route_id"),
                            "delay_seconds": obs.values.get("delay_seconds"),
                        },
                    )
                elif obs.domain == "water":
                    await session.execute(
                        text(
                            "INSERT INTO water_readings (time, feature_id, level_cm, flow_m3s) "
                            "VALUES (:time, :feature_id, :level_cm, :flow_m3s)"
                        ),
                        {
                            "time": ts,
                            "feature_id": obs.feature_id,
                            "level_cm": obs.values.get("level_cm"),
                            "flow_m3s": obs.values.get("flow_m3s"),
                        },
                    )
                elif obs.domain == "traffic":
                    await session.execute(
                        text(
                            "INSERT INTO traffic_readings "
                            "(time, feature_id, vehicle_count_total, vehicle_count_hgv, "
                            "speed_avg_kmh, congestion_level) "
                            "VALUES (:time, :feature_id, :vehicle_count_total, :vehicle_count_hgv, "
                            ":speed_avg_kmh, :congestion_level) "
                            "ON CONFLICT DO NOTHING"
                        ),
                        {
                            "time": ts,
                            "feature_id": obs.feature_id,
                            "vehicle_count_total": obs.values.get("vehicle_count_total"),
                            "vehicle_count_hgv": obs.values.get("vehicle_count_hgv"),
                            "speed_avg_kmh": obs.values.get("speed_avg_kmh"),
                            "congestion_level": obs.values.get("congestion_level"),
                        },
                    )
                elif obs.domain == "energy":
                    await session.execute(
                        text(
                            "INSERT INTO energy_readings "
                            "(time, feature_id, value_kw, source_type) "
                            "VALUES (:time, :feature_id, :value_kw, :source_type) "
                            "ON CONFLICT DO NOTHING"
                        ),
                        {
                            "time": ts,
                            "feature_id": obs.feature_id,
                            "value_kw": obs.values.get("value_kw"),
                            "source_type": obs.values.get("source_type"),
                        },
                    )
            await session.commit()

    async def upsert_feature(
        self,
        source_id: str,
        domain: str,
        geometry_wkt: str,
        properties: dict,
    ) -> str:
        """Upsert a spatial feature into the features table. Returns the UUID.

        Uses ON CONFLICT on (town_id, domain, source_id) unique constraint
        added in migration 002. geometry_wkt must be WKT with SRID 4326,
        e.g. 'POINT(10.09 48.84)'.
        """
        import json
        from app.db import AsyncSessionLocal
        from sqlalchemy import text

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text(
                    "INSERT INTO features (town_id, domain, source_id, geometry, properties) "
                    "VALUES (:town_id, :domain, :source_id, "
                    "ST_GeomFromText(:geom, 4326), :properties::jsonb) "
                    "ON CONFLICT (town_id, domain, source_id) "
                    "DO UPDATE SET geometry = EXCLUDED.geometry, "
                    "properties = EXCLUDED.properties "
                    "RETURNING id"
                ),
                {
                    "town_id": self.town.id,
                    "domain": domain,
                    "source_id": source_id,
                    "geom": geometry_wkt,
                    "properties": json.dumps(properties),
                },
            )
            await session.commit()
            row = result.fetchone()
            return str(row[0])

    async def _update_staleness(self) -> None:
        """Update sources.last_successful_fetch for this connector's source row.

        Called by run() on successful completion. Uses connector_class name +
        town_id to identify the source row. Safe to call even if no matching
        row exists in sources (UPDATE with no matching rows is a no-op).
        """
        from datetime import datetime, timezone
        from app.db import AsyncSessionLocal
        from sqlalchemy import text

        now = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as session:
            await session.execute(
                text(
                    "UPDATE sources SET last_successful_fetch = :now "
                    "WHERE town_id = :town_id AND connector_class = :connector_class"
                ),
                {
                    "now": now,
                    "town_id": self.town.id,
                    "connector_class": self.config.connector_class,
                },
            )
            await session.commit()
