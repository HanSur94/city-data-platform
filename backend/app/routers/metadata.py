# backend/app/routers/metadata.py
"""Layer metadata router: GET /api/metadata/layers

Returns per-layer transparency metadata (source, data_type, update_interval,
license, last_updated) for all layers in the current town.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db import get_db
from app.dependencies import get_current_town
from app.config import Town
from app.schemas.metadata import LayerMetadataItem, LayerMetadataResponse
from app.schemas.geojson import CONNECTOR_ATTRIBUTION

router = APIRouter(tags=["metadata"])


def _attr(connector_cls: str, field: str) -> str:
    """Look up a CONNECTOR_ATTRIBUTION field, return empty string if missing."""
    return CONNECTOR_ATTRIBUTION.get(connector_cls, {}).get(field, "")


# Static registry mapping frontend layer keys to metadata.
# connector_classes lists which connectors feed this layer (for last_updated lookup).
LAYER_METADATA_REGISTRY: dict[str, dict] = {
    "transit": {
        "connector_classes": ["GTFSConnector"],
        "source_name": _attr("GTFSConnector", "source_name"),
        "source_url": _attr("GTFSConnector", "url"),
        "data_type": "LIVE",
        "update_interval_seconds": 1800,
        "license": _attr("GTFSConnector", "license"),
        "license_url": _attr("GTFSConnector", "license_url"),
    },
    "busPosition": {
        "connector_classes": ["BusInterpolationConnector"],
        "source_name": _attr("BusInterpolationConnector", "source_name"),
        "source_url": _attr("BusInterpolationConnector", "url"),
        "data_type": "INTERPOLATED",
        "update_interval_seconds": 30,
        "license": _attr("BusInterpolationConnector", "license"),
        "license_url": _attr("BusInterpolationConnector", "license_url"),
    },
    "airQuality": {
        "connector_classes": ["UBAConnector", "SensorCommunityConnector"],
        "source_name": "UBA + Sensor.Community",
        "source_url": _attr("UBAConnector", "url"),
        "data_type": "LIVE",
        "update_interval_seconds": 300,
        "license": _attr("UBAConnector", "license"),
        "license_url": _attr("UBAConnector", "license_url"),
    },
    "airQualityGrid": {
        "connector_classes": ["AirQualityGridConnector"],
        "source_name": _attr("AirQualityGridConnector", "source_name"),
        "source_url": _attr("AirQualityGridConnector", "url"),
        "data_type": "INTERPOLATED",
        "update_interval_seconds": 300,
        "license": _attr("AirQualityGridConnector", "license"),
        "license_url": _attr("AirQualityGridConnector", "license_url"),
    },
    "water": {
        "connector_classes": ["PegelonlineConnector"],
        "source_name": _attr("PegelonlineConnector", "source_name"),
        "source_url": _attr("PegelonlineConnector", "url"),
        "data_type": "LIVE",
        "update_interval_seconds": 900,
        "license": _attr("PegelonlineConnector", "license"),
        "license_url": _attr("PegelonlineConnector", "license_url"),
    },
    "kocher": {
        "connector_classes": ["LhpConnector"],
        "source_name": "LHP Baden-Wuerttemberg",
        "source_url": "https://www.hvz.baden-wuerttemberg.de/",
        "data_type": "LIVE",
        "update_interval_seconds": 900,
        "license": "Datenlizenz Deutschland",
        "license_url": "https://www.govdata.de/dl-de/by-2-0",
    },
    "traffic": {
        "connector_classes": ["BastConnector"],
        "source_name": _attr("BastConnector", "source_name"),
        "source_url": _attr("BastConnector", "url"),
        "data_type": "LIVE",
        "update_interval_seconds": 3600,
        "license": _attr("BastConnector", "license"),
        "license_url": _attr("BastConnector", "license_url"),
    },
    "trafficFlow": {
        "connector_classes": ["TomTomConnector"],
        "source_name": "TomTom",
        "source_url": "https://developer.tomtom.com/",
        "data_type": "LIVE",
        "update_interval_seconds": 600,
        "license": "TomTom Developer License",
        "license_url": "https://developer.tomtom.com/",
    },
    "autobahn": {
        "connector_classes": ["AutobahnConnector"],
        "source_name": _attr("AutobahnConnector", "source_name"),
        "source_url": _attr("AutobahnConnector", "url"),
        "data_type": "LIVE",
        "update_interval_seconds": 300,
        "license": _attr("AutobahnConnector", "license"),
        "license_url": _attr("AutobahnConnector", "license_url"),
    },
    "energy": {
        "connector_classes": ["SmardConnector"],
        "source_name": _attr("SmardConnector", "source_name"),
        "source_url": _attr("SmardConnector", "url"),
        "data_type": "LIVE",
        "update_interval_seconds": 900,
        "license": _attr("SmardConnector", "license"),
        "license_url": _attr("SmardConnector", "license_url"),
    },
    "solarGlow": {
        "connector_classes": ["SolarProductionConnector"],
        "source_name": _attr("SolarProductionConnector", "source_name"),
        "source_url": _attr("SolarProductionConnector", "url"),
        "data_type": "MODELED",
        "update_interval_seconds": 900,
        "license": _attr("SolarProductionConnector", "license"),
        "license_url": _attr("SolarProductionConnector", "license_url"),
    },
    "evCharging": {
        "connector_classes": ["EvChargingConnector"],
        "source_name": _attr("EvChargingConnector", "source_name"),
        "source_url": _attr("EvChargingConnector", "url"),
        "data_type": "LIVE",
        "update_interval_seconds": 300,
        "license": _attr("EvChargingConnector", "license"),
        "license_url": _attr("EvChargingConnector", "license_url"),
    },
    "parking": {
        "connector_classes": ["ParkingConnector"],
        "source_name": _attr("ParkingConnector", "source_name"),
        "source_url": _attr("ParkingConnector", "url"),
        "data_type": "SCRAPED",
        "update_interval_seconds": 600,
        "license": _attr("ParkingConnector", "license"),
        "license_url": _attr("ParkingConnector", "license_url"),
    },
    "roadworks": {
        "connector_classes": ["OverpassRoadworksConnector"],
        "source_name": _attr("OverpassRoadworksConnector", "source_name"),
        "source_url": _attr("OverpassRoadworksConnector", "url"),
        "data_type": "LIVE",
        "update_interval_seconds": 3600,
        "license": _attr("OverpassRoadworksConnector", "license"),
        "license_url": _attr("OverpassRoadworksConnector", "license_url"),
    },
    "heatDemand": {
        "connector_classes": ["HeatDemandConnector"],
        "source_name": _attr("HeatDemandConnector", "source_name"),
        "source_url": _attr("HeatDemandConnector", "url"),
        "data_type": "MODELED",
        "update_interval_seconds": None,
        "license": _attr("HeatDemandConnector", "license"),
        "license_url": _attr("HeatDemandConnector", "license_url"),
    },
    "cycling": {
        "connector_classes": ["CyclingInfraConnector"],
        "source_name": _attr("CyclingInfraConnector", "source_name"),
        "source_url": _attr("CyclingInfraConnector", "url"),
        "data_type": "STATIC",
        "update_interval_seconds": None,
        "license": _attr("CyclingInfraConnector", "license"),
        "license_url": _attr("CyclingInfraConnector", "license_url"),
    },
    "demographics": {
        "connector_classes": ["ZensusConnector"],
        "source_name": _attr("ZensusConnector", "source_name"),
        "source_url": _attr("ZensusConnector", "url"),
        "data_type": "STATIC",
        "update_interval_seconds": None,
        "license": _attr("ZensusConnector", "license"),
        "license_url": _attr("ZensusConnector", "license_url"),
    },
    "roadNoise": {
        "connector_classes": ["LubwWfsConnector"],
        "source_name": "LUBW Baden-Wuerttemberg",
        "source_url": _attr("LubwWfsConnector", "url"),
        "data_type": "MODELED",
        "update_interval_seconds": None,
        "license": _attr("LubwWfsConnector", "license"),
        "license_url": _attr("LubwWfsConnector", "license_url"),
    },
    "fernwaerme": {
        "connector_classes": [],
        "source_name": "Stadtwerke Aalen",
        "source_url": "https://www.sw-aalen.de",
        "data_type": "STATIC",
        "update_interval_seconds": None,
        "license": "Proprietary",
        "license_url": "https://www.sw-aalen.de",
    },
    "schools": {
        "connector_classes": ["OverpassCommunityConnector"],
        "source_name": _attr("OverpassCommunityConnector", "source_name"),
        "source_url": _attr("OverpassCommunityConnector", "url"),
        "data_type": "LIVE",
        "update_interval_seconds": 86400,
        "license": _attr("OverpassCommunityConnector", "license"),
        "license_url": _attr("OverpassCommunityConnector", "license_url"),
    },
    "healthcare": {
        "connector_classes": ["OverpassCommunityConnector"],
        "source_name": _attr("OverpassCommunityConnector", "source_name"),
        "source_url": _attr("OverpassCommunityConnector", "url"),
        "data_type": "LIVE",
        "update_interval_seconds": 86400,
        "license": _attr("OverpassCommunityConnector", "license"),
        "license_url": _attr("OverpassCommunityConnector", "license_url"),
    },
    "parks": {
        "connector_classes": ["OverpassCommunityConnector"],
        "source_name": _attr("OverpassCommunityConnector", "source_name"),
        "source_url": _attr("OverpassCommunityConnector", "url"),
        "data_type": "LIVE",
        "update_interval_seconds": 86400,
        "license": _attr("OverpassCommunityConnector", "license"),
        "license_url": _attr("OverpassCommunityConnector", "license_url"),
    },
    "waste": {
        "connector_classes": ["OverpassCommunityConnector"],
        "source_name": _attr("OverpassCommunityConnector", "source_name"),
        "source_url": _attr("OverpassCommunityConnector", "url"),
        "data_type": "LIVE",
        "update_interval_seconds": 86400,
        "license": _attr("OverpassCommunityConnector", "license"),
        "license_url": _attr("OverpassCommunityConnector", "license_url"),
    },
    "mobiData": {
        "connector_classes": ["MobiDataBWConnector"],
        "source_name": _attr("MobiDataBWConnector", "source_name"),
        "source_url": _attr("MobiDataBWConnector", "url"),
        "data_type": "LIVE",
        "update_interval_seconds": 300,
        "license": _attr("MobiDataBWConnector", "license"),
        "license_url": _attr("MobiDataBWConnector", "license_url"),
    },
    "solarPotential": {
        "connector_classes": ["SolarPotentialConnector"],
        "source_name": _attr("SolarPotentialConnector", "source_name"),
        "source_url": _attr("SolarPotentialConnector", "url"),
        "data_type": "STATIC",
        "update_interval_seconds": None,
        "license": _attr("SolarPotentialConnector", "license"),
        "license_url": _attr("SolarPotentialConnector", "license_url"),
    },
}


@router.get("/metadata/layers", response_model=LayerMetadataResponse)
async def get_layer_metadata(
    town: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_town: Town = Depends(get_current_town),
) -> LayerMetadataResponse:
    """Return transparency metadata for all layers in this town."""
    if town != current_town.id:
        raise HTTPException(status_code=404, detail=f"Town not found: {town}")

    # Build a lookup of connector_class -> last_successful_fetch from the DB
    last_fetch_map: dict[str, datetime] = {}
    try:
        result = await db.execute(
            text("""
                SELECT connector_class, last_successful_fetch
                FROM sources
                WHERE town_id = :town_id
            """),
            {"town_id": current_town.id},
        )
        for row in result.mappings().all():
            fetch_time = row["last_successful_fetch"]
            if fetch_time is not None:
                if fetch_time.tzinfo is None:
                    fetch_time = fetch_time.replace(tzinfo=timezone.utc)
                cls_name = row["connector_class"]
                # Keep the most recent fetch across duplicate connector_class entries
                if cls_name not in last_fetch_map or fetch_time > last_fetch_map[cls_name]:
                    last_fetch_map[cls_name] = fetch_time
    except Exception:
        # Sources table may not exist in test environment
        pass

    layers: list[LayerMetadataItem] = []
    for layer_key, meta in LAYER_METADATA_REGISTRY.items():
        # Find the most recent last_updated across all connectors for this layer
        last_updated: datetime | None = None
        for cc in meta.get("connector_classes", []):
            fetch_time = last_fetch_map.get(cc)
            if fetch_time is not None:
                if last_updated is None or fetch_time > last_updated:
                    last_updated = fetch_time

        layers.append(LayerMetadataItem(
            layer_key=layer_key,
            source_name=meta["source_name"],
            source_url=meta["source_url"],
            data_type=meta["data_type"],
            update_interval_seconds=meta["update_interval_seconds"],
            license=meta["license"],
            license_url=meta["license_url"],
            last_updated=last_updated,
        ))

    return LayerMetadataResponse(town=current_town.id, layers=layers)
