"""BaseConnector: abstract base class for all data connectors.

All Phase 2+ connectors MUST inherit from BaseConnector and implement:
- fetch(): retrieve raw data from the external source
- normalize(): transform raw data into Observation objects

The persist() method is provided by the base class. Subclasses should
NOT override persist() — this ensures all data goes through the same
database write path.

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
    domain: str       # "air_quality", "transit", "water", "energy"
    values: dict      # domain-specific key-value pairs (e.g. {"pm10": 12.5})
    timestamp: datetime | None = field(default=None)
    source_id: str | None = field(default=None)


class BaseConnector(ABC):
    """Abstract base class for all city data connectors.

    Constructor args:
        config: ConnectorConfig with connector_class, poll_interval, etc.
        town: Town object for the town this connector serves.

    Concrete subclasses must implement fetch() and normalize().
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
        """Full pipeline: fetch -> normalize -> persist.

        Called by APScheduler on each poll interval. Subclasses should
        NOT override this method — override fetch() and normalize() instead.
        """
        raw = await self.fetch()
        observations = self.normalize(raw)
        await self.persist(observations)

    async def persist(self, observations: list[Observation]) -> None:
        """Write observations to the database.

        Phase 1 implementation: no-op (database wiring added in Phase 2).
        Subclasses should NOT override this method.
        """
        # Phase 2 will inject a SQLAlchemy session here via dependency injection
        pass
