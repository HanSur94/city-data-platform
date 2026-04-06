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
        scheduler.add_job(
            _run_connector,
            trigger=trigger,
            args=[connector_class, connector_cfg, town],
            max_instances=1,   # prevent overlapping runs
            coalesce=True,     # collapse missed runs into one
            id=f"{town.id}_{connector_cfg.connector_class}",
            replace_existing=True,
        )
        logger.info(
            "Scheduled %s every %ds",
            connector_cfg.connector_class,
            connector_cfg.poll_interval_seconds,
        )
