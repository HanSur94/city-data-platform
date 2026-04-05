# backend/app/schemas/geojson.py
"""Response schemas for GeoJSON layer endpoints.

Attribution must appear in every layer response per PLAT-04
(Datenlizenz Deutschland compliance).
"""
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


NGSI_CONTEXT = "https://uri.fiware.org/ns/data-models/context.jsonld"

# Static attribution lookup keyed by connector_class name.
# Maps connector class → DL-DE-BY-2.0 attribution metadata.
CONNECTOR_ATTRIBUTION: dict[str, dict[str, str]] = {
    "UBAConnector": {
        "source_name": "Umweltbundesamt (UBA)",
        "license": "Datenlizenz Deutschland – Namensnennung – Version 2.0",
        "license_url": "https://www.govdata.de/dl-de/by-2-0",
        "url": "https://www.umweltbundesamt.de/",
    },
    "SensorCommunityConnector": {
        "source_name": "Sensor.Community",
        "license": "Open Data Commons Open Database License (ODbL)",
        "license_url": "https://opendatacommons.org/licenses/odbl/",
        "url": "https://sensor.community/",
    },
    "GTFSConnector": {
        "source_name": "MobiData BW / NVBW GTFS",
        "license": "Datenlizenz Deutschland – Namensnennung – Version 2.0",
        "license_url": "https://www.govdata.de/dl-de/by-2-0",
        "url": "https://www.mobidata-bw.de/",
    },
    "GTFSRealtimeConnector": {
        "source_name": "MobiData BW / NVBW GTFS-RT",
        "license": "Datenlizenz Deutschland – Namensnennung – Version 2.0",
        "license_url": "https://www.govdata.de/dl-de/by-2-0",
        "url": "https://www.mobidata-bw.de/",
    },
    "WeatherConnector": {
        "source_name": "Deutscher Wetterdienst (DWD) via Bright Sky",
        "license": "Datenlizenz Deutschland – Zero – Version 2.0",
        "license_url": "https://www.govdata.de/dl-de/zero-2-0",
        "url": "https://brightsky.dev/",
    },
}

# Valid domain values for path parameter validation
VALID_DOMAINS: frozenset[str] = frozenset(
    {"air_quality", "transit", "weather", "water", "energy"}
)

# AQI health tier thresholds (WHO/UBA guidelines, based on max of PM2.5/PM10/NO2/O3)
# Returns (tier_label, hex_color)
AQI_TIERS: list[tuple[float, str, str]] = [
    (20.0,  "good",      "#00c853"),
    (40.0,  "moderate",  "#ffeb3b"),
    (60.0,  "poor",      "#ff9800"),
    (80.0,  "bad",       "#f44336"),
    (float("inf"), "very_bad", "#b71c1c"),
]


def aqi_tier(aqi_value: float | None) -> tuple[str, str]:
    """Return (tier_label, hex_color) for a given AQI float. Returns unknown for None."""
    if aqi_value is None:
        return ("unknown", "#9e9e9e")
    for threshold, label, color in AQI_TIERS:
        if aqi_value <= threshold:
            return (label, color)
    return ("very_bad", "#b71c1c")


class Attribution(BaseModel):
    source_name: str
    license: str
    license_url: str
    url: str | None = None


class LayerResponse(BaseModel):
    context: str = Field(default=NGSI_CONTEXT, alias="@context")
    type: str = "FeatureCollection"
    features: list[dict[str, Any]]
    attribution: list[Attribution]
    last_updated: datetime | None
    town: str
    domain: str

    model_config = {"populate_by_name": True}
