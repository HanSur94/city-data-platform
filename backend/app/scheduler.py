"""APScheduler integration for periodic connector polling.

Uses APScheduler 3.x AsyncIOScheduler (NOT 4.x — different API).
Runs within the same asyncio event loop as FastAPI.

Usage in main.py lifespan:
    from app.scheduler import scheduler, setup_scheduler
    setup_scheduler(town)
    scheduler.start()
    yield
    scheduler.shutdown()
"""
from __future__ import annotations
import importlib
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import ConnectorConfig, Town

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

# Registry of known connector classes by name
_CONNECTOR_MODULES = {
    "StubConnector": "app.connectors.stub",
    "UBAConnector": "app.connectors.uba",
    "SensorCommunityConnector": "app.connectors.sensor_community",
    "WeatherConnector": "app.connectors.weather",
    "GTFSConnector": "app.connectors.gtfs",
    "GTFSRealtimeConnector": "app.connectors.gtfs_rt",
    "PegelonlineConnector": "app.connectors.pegelonline",
    "LubwWfsConnector": "app.connectors.lubw_wfs",
    # Phase 7: traffic + energy connectors
    "BastConnector": "app.connectors.bast",
    "AutobahnConnector": "app.connectors.autobahn",
    "MobiDataBWConnector": "app.connectors.mobidata_bw",
    "SmardConnector": "app.connectors.smard",
    "MastrConnector": "app.connectors.mastr",
    # Phase 8: community + infrastructure connectors
    "OverpassCommunityConnector": "app.connectors.overpass_community",
    "OverpassRoadworksConnector": "app.connectors.overpass_roadworks",
    "LadesaeulenConnector": "app.connectors.ladesaeulen",
    "SolarPotentialConnector": "app.connectors.solar_potential",
    # Phase 11: TomTom traffic flow
    "TomTomConnector": "app.connectors.tomtom",
    # Phase 12: LHP water level
    "LhpConnector": "app.connectors.lhp",
    # Phase 13: Parking occupancy
    "ParkingConnector": "app.connectors.parking",
    # Phase 14: Bus position interpolation
    "BusInterpolationConnector": "app.connectors.bus_interpolation",
    # Phase 15: Air quality grid interpolation
    "AirQualityGridConnector": "app.connectors.air_quality_grid",
    # Phase 16: Solar production + EV charging live status
    "SolarProductionConnector": "app.connectors.solar_production",
    "EvChargingConnector": "app.connectors.ev_charging",
    # Phase 17: Static layers
    "HeatDemandConnector": "app.connectors.heat_demand",
    "CyclingInfraConnector": "app.connectors.cycling",
    # Phase 19: OSM buildings with addresses
    "OsmBuildingsConnector": "app.connectors.osm_buildings",
    # Backlog 999.4: Police reports
    "PoliceConnector": "app.connectors.police",
}


def _resolve_connector(connector_class: str):
    """Resolve a connector class by its string name."""
    module_path = _CONNECTOR_MODULES.get(connector_class)
    if not module_path:
        raise ValueError(
            f"Unknown connector class: {connector_class!r}. "
            f"Known: {list(_CONNECTOR_MODULES.keys())}"
        )
    module = importlib.import_module(module_path)
    return getattr(module, connector_class)


async def _run_connector(
    connector_class,
    config: ConnectorConfig,
    town: Town,
) -> None:
    """Instantiate and run one connector. Fresh instance per job run."""
    try:
        connector = connector_class(config=config, town=town)
        await connector.run()
        logger.info("Connector %s completed successfully", config.connector_class)
    except Exception as exc:
        logger.error(
            "Connector %s failed: %s", config.connector_class, exc, exc_info=True
        )


def setup_scheduler(town: Town) -> None:
    """Register all enabled connector jobs for a town.

    Call this during FastAPI lifespan before scheduler.start().
    """
    for connector_cfg in town.connectors:
        if not connector_cfg.enabled:
            continue
        try:
            connector_class = _resolve_connector(connector_cfg.connector_class)
        except ValueError as exc:
            logger.warning("Skipping connector: %s", exc)
            continue

        trigger = IntervalTrigger(seconds=connector_cfg.poll_interval_seconds)
        # Fire immediately on startup for long-interval connectors (>= 1 hour)
        # so features populate right away instead of waiting the full interval.
        run_now = None
        if connector_cfg.poll_interval_seconds >= 3600:
            run_now = datetime.now(timezone.utc)

        scheduler.add_job(
            _run_connector,
            trigger=trigger,
            args=[connector_class, connector_cfg, town],
            max_instances=1,   # prevent overlapping runs
            coalesce=True,     # collapse missed runs into one
            id=f"{town.id}_{connector_cfg.connector_class}",
            replace_existing=True,
            next_run_time=run_now,  # fire immediately for long-interval connectors
        )
        logger.info(
            "Scheduled %s every %ds",
            connector_cfg.connector_class,
            connector_cfg.poll_interval_seconds,
        )
