"""WeatherConnector: fetches current conditions and MOSMIX forecast from Bright Sky / DWD.

Data source: https://brightsky.dev — free, no API key required.
Attribution: Deutscher Wetterdienst (DWD) via Bright Sky, CC BY 4.0.

Implements WAIR-01 (current weather) and WAIR-02 (48-hour MOSMIX forecast).
Writes to the weather_readings hypertable via BaseConnector.persist().
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx

from app.connectors.base import BaseConnector, Observation
from app.models.weather import BrightSkyForecastEntry, BrightSkyWeather


class WeatherConnector(BaseConnector):
    """Fetches current weather and 48-hour MOSMIX forecast from Bright Sky API.

    Configuration keys (in ConnectorConfig.config):
        lat (float): Latitude of the measurement point. Default 48.84 (Aalen).
        lon (float): Longitude of the measurement point. Default 10.09 (Aalen).
        attribution (str): Override the DWD/Bright Sky attribution string.

    lat/lon are read from config — not hardcoded — so the connector works
    for any German town covered by DWD.
    """

    async def run(self) -> None:
        """Override: upsert feature once, then fetch/normalize/persist/staleness."""
        lat = self.config.config.get("lat", 48.84)
        lon = self.config.config.get("lon", 10.09)
        self._feature_id = await self.upsert_feature(
            source_id=f"weather:{self.town.id}",
            domain="weather",
            geometry_wkt=f"POINT({lon} {lat})",
            properties={
                "attribution": self.config.config.get(
                    "attribution",
                    "Deutscher Wetterdienst (DWD) via Bright Sky, CC BY 4.0",
                ),
            },
        )
        raw = await self.fetch()
        observations = self.normalize(raw)
        await self.persist(observations)
        await self._update_staleness()

    async def fetch(self) -> dict:
        """Fetch current weather and 48-hour MOSMIX forecast from Bright Sky.

        Returns:
            dict with keys:
                "current": dict — current weather data (single observation)
                "forecast": list[dict] — forecast entries (may include non-MOSMIX)
                "sources": list[dict] — source metadata for filtering

        Raises:
            httpx.HTTPStatusError: On non-2xx response.
            ValueError: If the current_weather response contains no weather data.
        """
        lat = self.config.config.get("lat", 48.84)
        lon = self.config.config.get("lon", 10.09)

        async with httpx.AsyncClient(timeout=15.0) as client:
            # Current weather
            r1 = await client.get(
                "https://api.brightsky.dev/current_weather",
                params={"lat": lat, "lon": lon, "tz": "Europe/Berlin"},
            )
            r1.raise_for_status()
            current_data = r1.json()
            if not current_data.get("weather"):
                raise ValueError(
                    "Empty current weather from Bright Sky (HTTP 200 no data)"
                )

            # 48-hour MOSMIX forecast
            today = date.today().isoformat()
            last_date = (date.today() + timedelta(days=2)).isoformat()
            r2 = await client.get(
                "https://api.brightsky.dev/weather",
                params={
                    "lat": lat,
                    "lon": lon,
                    "date": today,
                    "last_date": last_date,
                    "tz": "Europe/Berlin",
                },
            )
            r2.raise_for_status()
            forecast_data = r2.json()

        return {
            "current": current_data["weather"],
            "forecast": forecast_data.get("weather", []),
            "sources": forecast_data.get("sources", []),
        }

    def normalize(self, raw: Any) -> list[Observation]:
        """Transform raw Bright Sky data into Observations.

        Produces:
            - One Observation with observation_type="current" from current data.
            - One Observation per MOSMIX forecast entry (source.observation_type=="forecast")
              with observation_type="forecast".

        Args:
            raw: dict returned by fetch() with "current", "forecast", "sources" keys.
                 self._feature_id must be set before calling (done by run()).

        Returns:
            List of Observation objects ready for persist().
        """
        observations: list[Observation] = []

        # Build source_id -> observation_type lookup from sources list
        source_id_to_type: dict[int, str] = {
            s["id"]: s.get("observation_type", "")
            for s in raw.get("sources", [])
        }

        # Normalize current observation
        current_raw = raw.get("current", {})
        if current_raw:
            current = BrightSkyWeather.model_validate(current_raw)
            observations.append(
                Observation(
                    feature_id=self._feature_id,
                    domain="weather",
                    values=self._weather_values(current, "current"),
                    timestamp=current.timestamp,
                )
            )

        # Normalize forecast observations (MOSMIX only — filter out "observation" type)
        for entry_raw in raw.get("forecast", []):
            sid = entry_raw.get("source_id")
            if source_id_to_type.get(sid) != "forecast":
                continue
            entry = BrightSkyForecastEntry.model_validate(entry_raw)
            observations.append(
                Observation(
                    feature_id=self._feature_id,
                    domain="weather",
                    values=self._weather_values(entry, "forecast"),
                    timestamp=entry.timestamp,
                )
            )

        return observations

    @staticmethod
    def _weather_values(
        model: BrightSkyWeather | BrightSkyForecastEntry,
        observation_type: str,
    ) -> dict:
        """Build the values dict from a Bright Sky weather model.

        All numeric fields are float | None — Pydantic coerces int fields
        (like wind_direction) to float via the model definition.
        """
        return {
            "observation_type": observation_type,
            "temperature": model.temperature,
            "dew_point": model.dew_point,
            "pressure_msl": model.pressure_msl,
            "wind_speed": model.wind_speed,
            "wind_direction": model.wind_direction,
            "cloud_cover": model.cloud_cover,
            "condition": model.condition,
            "icon": model.icon,
            "precipitation_10": model.precipitation_10,
            "precipitation_30": model.precipitation_30,
            "precipitation_60": model.precipitation_60,
        }
