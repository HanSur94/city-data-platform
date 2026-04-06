"""SmardConnector: fetches electricity generation mix and wholesale price from SMARD.

Implements ENRG-01, ENRG-02: retrieves national electricity generation data
(generation mix for 9 source types + day-ahead wholesale price) and writes
readings to the energy_readings hypertable.

SMARD API (Bundesnetzagentur):
    BASE = "https://www.smard.de/app/chart_data"
    Step 1: GET /{filter}/{region}/index_{resolution}.json
            -> {"timestamps": [...]}
    Step 2: GET /{filter}/{region}/{filter}_{region}_{resolution}_{timestamp}.json
            -> {"series": [[unix_ms, value_mw_or_null], ...]}

License: Data available free of charge from Bundesnetzagentur / SMARD.de
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import httpx

from app.connectors.base import BaseConnector, Observation
from app.config import ConnectorConfig, Town


SMARD_BASE = "https://www.smard.de/app/chart_data"

GENERATION_FILTERS: dict[str, int] = {
    "solar": 4068,
    "wind_onshore": 4067,
    "wind_offshore": 1225,
    "gas": 4071,
    "lignite": 1223,
    "hard_coal": 4069,
    "nuclear": 1224,
    "hydro": 1226,
    "biomass": 4066,
}

PRICE_FILTER = 4169  # EUR/MWh day-ahead wholesale price

RENEWABLE_SOURCES = {"solar", "wind_onshore", "wind_offshore", "hydro", "biomass"}


class SmardConnector(BaseConnector):
    """Fetches electricity generation mix and wholesale price from SMARD.

    Uses the two-step fetch pattern:
    1. GET index_quarterhour.json to discover available data chunks
    2. GET the latest data chunk to retrieve the series values

    National grid data has no geographic coordinates. A synthetic feature
    at the geographic center of Germany (POINT(10.45 51.16)) is used to
    satisfy the energy_readings foreign key constraint.
    """

    def __init__(self, config: ConnectorConfig, town: Town) -> None:
        super().__init__(config, town)
        self._national_feature_id: str = ""

    async def _fetch_latest(
        self,
        client: httpx.AsyncClient,
        filter_code: int,
        region: str = "DE",
        resolution: str = "quarterhour",
    ) -> list[tuple[int, float | None]]:
        """Two-step fetch for a single SMARD filter code.

        Step 1: Retrieve the index of available data timestamps.
        Step 2: Fetch the latest data chunk and return the series.

        Args:
            client: Active httpx.AsyncClient to reuse.
            filter_code: SMARD filter code (e.g. 4068 for solar).
            region: Market area code (default "DE").
            resolution: Time resolution (default "quarterhour").

        Returns:
            List of (unix_ms, value_mw_or_none) tuples from the latest chunk.
        """
        # Step 1: GET index to find available timestamps
        index_url = f"{SMARD_BASE}/{filter_code}/{region}/index_{resolution}.json"
        index_resp = await client.get(index_url)
        index_resp.raise_for_status()
        index_data = index_resp.json()

        timestamps: list[int] = index_data.get("timestamps", [])
        if not timestamps:
            return []

        # Use the last (most recent) timestamp chunk
        last_ts = timestamps[-1]

        # Step 2: GET the data chunk for that timestamp
        data_url = (
            f"{SMARD_BASE}/{filter_code}/{region}/"
            f"{filter_code}_{region}_{resolution}_{last_ts}.json"
        )
        data_resp = await client.get(data_url)
        data_resp.raise_for_status()
        data = data_resp.json()

        series: list[list] = data.get("series", [])
        return [(row[0], row[1]) for row in series if len(row) == 2]

    async def fetch(self) -> bytes:
        """Fetch all generation sources + wholesale price from SMARD.

        Calls _fetch_latest for each of the 9 generation filters and the
        price filter. Returns JSON-encoded dict mapping source name -> series.

        Returns:
            JSON bytes: {"solar": [[ts_ms, val], ...], ..., "price": [...]}
        """
        result: dict[str, list[tuple[int, float | None]]] = {}

        async with httpx.AsyncClient(timeout=30.0) as client:
            for source_name, filter_code in GENERATION_FILTERS.items():
                series = await self._fetch_latest(client, filter_code)
                result[source_name] = series

            price_series = await self._fetch_latest(client, PRICE_FILTER)
            result["price"] = price_series

        return json.dumps(result).encode()

    def normalize(self, raw: bytes, **kwargs: Any) -> list[Observation]:
        """Transform raw SMARD data into Observation objects.

        Filters out null values (Pitfall 1: SMARD uses null for missing data).
        Converts MW values to kW for the energy_readings schema.

        Args:
            raw: JSON bytes from fetch().
            **kwargs: Must include feature_ids={"national": <uuid>} when called
                      from run(). When called in tests, falls back to empty string.

        Returns:
            List of Observation objects with domain="energy".
        """
        feature_ids: dict[str, str] = kwargs.get("feature_ids", {})
        national_feature_id = feature_ids.get("national", self._national_feature_id)

        data: dict[str, list] = json.loads(raw)
        observations: list[Observation] = []

        for source_name, series in data.items():
            for row in series:
                ts_ms, value = row[0], row[1]

                # CRITICAL: filter None values (Pitfall 1)
                if value is not None:
                    observations.append(
                        Observation(
                            feature_id=national_feature_id,
                            domain="energy",
                            values={
                                "value_kw": float(value) * 1000.0,
                                "source_type": source_name,
                            },
                            timestamp=datetime.fromtimestamp(
                                ts_ms / 1000.0, tz=timezone.utc
                            ),
                            source_id="smard:national",
                        )
                    )

        return observations

    def compute_renewable_percent(
        self, generation: dict[str, float]
    ) -> float | None:
        """Calculate the percentage of generation from renewable sources.

        Args:
            generation: Dict mapping source name to MW generation value.

        Returns:
            Renewable percentage as float (0.0–100.0), or None if total is 0.
        """
        total = sum(generation.values())
        if total == 0:
            return None

        renewable = sum(
            v for k, v in generation.items() if k in RENEWABLE_SOURCES
        )
        return (renewable / total) * 100.0

    async def run(self) -> None:
        """Full pipeline: upsert synthetic national feature -> fetch -> normalize -> persist.

        Overrides BaseConnector.run() to:
        1. Upsert a synthetic national feature at center of Germany
        2. Fetch all generation + price data
        3. Normalize with the national feature_id
        4. Persist observations to energy_readings
        5. Update staleness timestamp
        """
        # Step 1: upsert synthetic national feature (center of Germany)
        feature_id = await self.upsert_feature(
            source_id="smard:national",
            domain="energy",
            geometry_wkt="POINT(10.45 51.16)",
            properties={
                "name": "Germany National Grid",
                "attribution": "SMARD (Bundesnetzagentur), smard.de",
                "source": "SMARD",
            },
        )
        self._national_feature_id = feature_id

        # Step 2: fetch all data
        raw = await self.fetch()

        # Step 3: normalize with feature_ids mapping
        observations = self.normalize(raw, feature_ids={"national": feature_id})

        # Step 4: persist to energy_readings
        await self.persist(observations)

        # Step 5: update staleness
        await self._update_staleness()
