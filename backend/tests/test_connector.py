"""Tests for BaseConnector abstract class contract and StubConnector implementation."""
import pytest
from pathlib import Path
from app.config import load_town, ConnectorConfig
from app.connectors.base import BaseConnector, Observation
from app.connectors.stub import StubConnector

TOWNS_DIR = Path(__file__).parent.parent.parent / "towns"


@pytest.fixture
def aalen_town():
    return load_town("aalen", towns_dir=TOWNS_DIR)


@pytest.fixture
def stub_config():
    return ConnectorConfig(connector_class="StubConnector")


@pytest.fixture
def stub_connector(stub_config, aalen_town):
    return StubConnector(config=stub_config, town=aalen_town)


def test_stub_is_base_connector_subclass():
    assert issubclass(StubConnector, BaseConnector)


def test_stub_has_fetch(stub_connector):
    assert hasattr(stub_connector, "fetch")
    assert callable(stub_connector.fetch)


def test_stub_has_normalize(stub_connector):
    assert hasattr(stub_connector, "normalize")
    assert callable(stub_connector.normalize)


@pytest.mark.asyncio
async def test_stub_fetch_returns_dict(stub_connector):
    result = await stub_connector.fetch()
    assert isinstance(result, dict)
    assert result["status"] == "ok"
    assert result["town"] == "aalen"


def test_stub_normalize_returns_empty_list(stub_connector):
    result = stub_connector.normalize({"status": "ok", "town": "aalen"})
    assert result == []


@pytest.mark.asyncio
async def test_stub_run_completes(stub_connector):
    """run() must complete without raising any exception."""
    await stub_connector.run()  # should not raise


def test_abstract_cannot_instantiate(stub_config, aalen_town):
    """BaseConnector is abstract — instantiating it directly must raise TypeError."""
    with pytest.raises(TypeError):
        BaseConnector(config=stub_config, town=aalen_town)
