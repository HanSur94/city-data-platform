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
    "PegelonlineConnector": {
        "source_name": "PEGELONLINE (WSV / BfG)",
        "license": "Datenlizenz Deutschland – Zero – Version 2.0",
        "license_url": "https://www.govdata.de/dl-de/zero-2-0",
        "url": "https://www.pegelonline.wsv.de/",
    },
    "LubwWfsConnector": {
        "source_name": "Landesanstalt für Umwelt Baden-Württemberg (LUBW)",
        "license": "Datenlizenz Deutschland – Namensnennung – Version 2.0",
        "license_url": "https://www.govdata.de/dl-de/by-2-0",
        "url": "https://www.lubw.baden-wuerttemberg.de/",
    },
    "BastConnector": {
        "source_name": "BASt (Bundesanstalt fuer Strassenwesen)",
        "license": "Datenlizenz Deutschland - Zero - Version 2.0",
        "license_url": "https://www.govdata.de/dl-de/zero-2-0",
        "url": "https://www.bast.de/",
    },
    "AutobahnConnector": {
        "source_name": "Autobahn GmbH des Bundes",
        "license": "Datenlizenz Deutschland - Zero - Version 2.0",
        "license_url": "https://www.govdata.de/dl-de/zero-2-0",
        "url": "https://verkehr.autobahn.de/",
    },
    "MobiDataBWConnector": {
        "source_name": "MobiData BW",
        "license": "Datenlizenz Deutschland - Namensnennung - Version 2.0",
        "license_url": "https://www.govdata.de/dl-de/by-2-0",
        "url": "https://www.mobidata-bw.de/",
    },
    "SmardConnector": {
        "source_name": "SMARD (Bundesnetzagentur)",
        "license": "Datenlizenz Deutschland - Zero - Version 2.0",
        "license_url": "https://www.govdata.de/dl-de/zero-2-0",
        "url": "https://www.smard.de/",
    },
    "MastrConnector": {
        "source_name": "Marktstammdatenregister (BNetzA)",
        "license": "Datenlizenz Deutschland - Zero - Version 2.0",
        "license_url": "https://www.govdata.de/dl-de/zero-2-0",
        "url": "https://www.marktstammdatenregister.de/",
    },
    "OverpassCommunityConnector": {
        "source_name": "OpenStreetMap contributors",
        "license": "ODbL 1.0",
        "license_url": "https://opendatacommons.org/licenses/odbl/",
        "url": "https://www.openstreetmap.org/copyright",
    },
    "OverpassRoadworksConnector": {
        "source_name": "OpenStreetMap contributors",
        "license": "ODbL 1.0",
        "license_url": "https://opendatacommons.org/licenses/odbl/",
        "url": "https://www.openstreetmap.org/copyright",
    },
    "LadesaeulenConnector": {
        "source_name": "Bundesnetzagentur",
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "url": "https://www.bundesnetzagentur.de",
    },
    "SolarPotentialConnector": {
        "source_name": "LUBW Baden-Wuerttemberg",
        "license": "UIS-Nutzungsvereinbarung",
        "license_url": "https://www.lubw.baden-wuerttemberg.de",
        "url": "https://www.lubw.baden-wuerttemberg.de",
    },
}

# Valid domain values for path parameter validation
VALID_DOMAINS: frozenset[str] = frozenset(
    {"air_quality", "transit", "weather", "water", "energy", "traffic", "community", "infrastructure"}
)

# EEA European Air Quality Index (EAQI) 6-tier per-pollutant thresholds
# Reference: https://airindex.eea.europa.eu (verified 2026-04-06)
EAQI_TIER_LABELS: list[str] = [
    "good", "fair", "moderate", "poor", "very_poor", "extremely_poor"
]
EAQI_TIER_COLORS: list[str] = [
    "#50F0E6", "#50CCAA", "#F0E641", "#FF5050", "#960032", "#7D2181"
]
EAQI_BREAKPOINTS: dict[str, list[float]] = {
    "pm25": [5,   15,   25,   50,  75,  float("inf")],
    "pm10": [10,  20,   50,  100, 150,  float("inf")],
    "no2":  [10,  20,   50,  100, 200,  float("inf")],
    "o3":   [50, 100,  130,  240, 380,  float("inf")],
}


def eaqi_from_readings(
    pm25: float | None,
    pm10: float | None,
    no2: float | None,
    o3: float | None,
) -> tuple[int, str, str]:
    """Return (tier_index 0-5, label, hex_color) using EEA EAQI methodology.

    Overall EAQI = max tier index across all pollutants with non-None values.
    Returns (0, "unknown", "#9e9e9e") when all inputs are None.
    """
    best_tier = -1
    for pollutant, value in [("pm25", pm25), ("pm10", pm10), ("no2", no2), ("o3", o3)]:
        if value is None:
            continue
        thresholds = EAQI_BREAKPOINTS[pollutant]
        for tier_idx, threshold in enumerate(thresholds):
            if value <= threshold:
                best_tier = max(best_tier, tier_idx)
                break
    if best_tier == -1:
        return (0, "unknown", "#9e9e9e")
    return (best_tier, EAQI_TIER_LABELS[best_tier], EAQI_TIER_COLORS[best_tier])


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
