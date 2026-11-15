"""Registry / town YAML / domain consistency regression tests (F3)."""
import importlib
import inspect
import pkgutil
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import app.connectors
from app.config import ConnectorConfig, Town, TownBbox
from app.connectors.base import BaseConnector
from app.routers.admin import STALENESS_THRESHOLDS
from app.scheduler import (
    CONNECTOR_DOMAINS,
    _CONNECTOR_MODULES,
    _resolve_connector,
    setup_scheduler,
)
from app.schemas.geojson import VALID_DOMAINS

TOWNS_DIR = Path(__file__).parent.parent.parent / "towns"

DEMOGRAPHICS = [
    "WegweiserKommuneConnector",
    "StatistikBWConnector",
    "ZensusConnector",
    "BundesagenturConnector",
]


def _yaml_connector_classes() -> set[str]:
    names: set[str] = set()
    for path in sorted(TOWNS_DIR.glob("*.yaml")):
        names.update(
            re.findall(
                r"^\s*-?\s*connector_class:\s*[\"']?([A-Za-z0-9_]+)",
                path.read_text(),
                flags=re.MULTILINE,
            )
        )
    return names


def test_town_yaml_connector_classes_resolve():
    names = _yaml_connector_classes()
    assert "GTFSConnector" in names
    assert "ZensusConnector" in names
    for name in sorted(names):
        cls = _resolve_connector(name)
        assert issubclass(cls, BaseConnector)
        assert cls.__name__ == name


def test_all_concrete_connectors_registered():
    found: dict[str, str] = {}
    for mod_info in pkgutil.iter_modules(app.connectors.__path__):
        module_path = f"app.connectors.{mod_info.name}"
        module = importlib.import_module(module_path)
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, BaseConnector)
                and obj is not BaseConnector
                and obj.__module__ == module_path
                and not inspect.isabstract(obj)
            ):
                found[name] = module_path
    assert found == _CONNECTOR_MODULES


def test_connector_domains_consistent():
    assert set(CONNECTOR_DOMAINS) == set(_CONNECTOR_MODULES) - {"StubConnector"}
    for name, domain in CONNECTOR_DOMAINS.items():
        assert domain in VALID_DOMAINS, f"{name}: {domain} not in VALID_DOMAINS"
        assert domain in STALENESS_THRESHOLDS, f"{name}: {domain} has no staleness thresholds"


def test_demographics_connectors_scheduled():
    town = Town(
        id="aalen",
        display_name="Aalen",
        country="DE",
        bbox=TownBbox(lon_min=9.9, lat_min=48.7, lon_max=10.2, lat_max=48.9),
        connectors=[ConnectorConfig(connector_class=n) for n in DEMOGRAPHICS],
    )
    mock_scheduler = MagicMock()
    with patch("app.scheduler.scheduler", mock_scheduler):
        setup_scheduler(town)
    assert mock_scheduler.add_job.call_count == 4
    ids = {c.kwargs["id"] for c in mock_scheduler.add_job.call_args_list}
    assert ids == {f"aalen_{n}" for n in DEMOGRAPHICS}
