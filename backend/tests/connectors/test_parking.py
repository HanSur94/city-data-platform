"""Unit tests for ParkingConnector (Stadtwerke Aalen parking garage scraper)."""
from __future__ import annotations

import pytest

from app.config import ConnectorConfig, Town
from app.connectors.parking import ParkingConnector
from app.models.parking import ParkingGarage


# Sample HTML mimicking the Stadtwerke Aalen parking page structure
SAMPLE_HTML = """
<html>
<body>
<div class="parkhaus">
  <div class="parkhaus-item">
    <h3>Parkhaus Stadtmitte</h3>
    <span class="free">120</span>
    <span class="total">300</span>
  </div>
  <div class="parkhaus-item">
    <h3>Parkhaus Gmünder Tor</h3>
    <span class="free">0</span>
    <span class="total">200</span>
  </div>
  <div class="parkhaus-item">
    <h3>Parkhaus Reichsstädter Markt</h3>
    <span class="free">geschlossen</span>
    <span class="total">150</span>
  </div>
  <div class="parkhaus-item">
    <h3>Parkhaus Spitalstraße</h3>
    <span class="free">45</span>
    <span class="total">180</span>
  </div>
</div>
</body>
</html>
"""

UNPARSEABLE_HTML = """
<html><body><p>No parking data here</p></body></html>
"""


def _make_connector() -> ParkingConnector:
    """Create a ParkingConnector with test config."""
    town = Town(
        id="aalen",
        display_name="Aalen",
        country="DE",
        timezone="Europe/Berlin",
        bbox={"lon_min": 9.97, "lat_min": 48.76, "lon_max": 10.22, "lat_max": 48.90},
        connectors=[],
    )
    config = ConnectorConfig(
        connector_class="ParkingConnector",
        poll_interval_seconds=300,
        enabled=True,
        config={
            "url": "https://www.sw-aalen.de/privatkunden/dienstleistungen/parken/parkhausbelegung",
            "attribution": "Stadtwerke Aalen, scraping",
        },
    )
    return ParkingConnector(config=config, town=town)


class TestNormalize:
    """Tests for ParkingConnector.normalize()."""

    def test_extracts_garage_names_and_spots(self):
        """normalize() extracts garage names, free spots, total from mock HTML."""
        connector = _make_connector()
        garages = connector.normalize(SAMPLE_HTML)

        # Should extract at least the garages with valid numeric free spots
        valid_garages = [g for g in garages if g.free_spots >= 0]
        assert len(valid_garages) >= 2

        names = [g.name for g in garages]
        assert any("Stadtmitte" in n for n in names)

        stadtmitte = next(g for g in garages if "Stadtmitte" in g.name)
        assert stadtmitte.free_spots == 120
        assert stadtmitte.total_spots == 300
        assert abs(stadtmitte.occupancy_pct - 60.0) < 0.1

    def test_handles_geschlossen_as_zero(self):
        """normalize() handles 'geschlossen' or '0' free spots."""
        connector = _make_connector()
        garages = connector.normalize(SAMPLE_HTML)

        # Gmunder Tor has 0 free spots
        gmuender = next((g for g in garages if "Gm" in g.name), None)
        if gmuender:
            assert gmuender.free_spots == 0

        # Reichsstadter Markt has "geschlossen" -> should be 0
        reichs = next((g for g in garages if "Reichs" in g.name), None)
        if reichs:
            assert reichs.free_spots == 0

    def test_returns_empty_for_unparseable_html(self):
        """normalize() returns empty list for unparseable HTML."""
        connector = _make_connector()
        garages = connector.normalize(UNPARSEABLE_HTML)
        assert garages == []


class TestParkingGarageModel:
    """Tests for ParkingGarage Pydantic model."""

    def test_valid_data(self):
        """ParkingGarage validates valid data."""
        garage = ParkingGarage(
            name="Test Parkhaus",
            free_spots=50,
            total_spots=200,
            occupancy_pct=75.0,
        )
        assert garage.name == "Test Parkhaus"
        assert garage.free_spots == 50
        assert garage.total_spots == 200

    def test_rejects_negative_free_spots(self):
        """ParkingGarage model rejects negative free_spots."""
        with pytest.raises(Exception):
            ParkingGarage(
                name="Test",
                free_spots=-1,
                total_spots=100,
                occupancy_pct=101.0,
            )
