"""Unit tests for ParkingConnector (Stadtwerke Aalen parking garage scraper)."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.config import ConnectorConfig, Town
from app.connectors.parking import GARAGES, ParkingConnector, _find_entry, _slugify
from app.models.parking import ParkingGarage


# Table rows cut verbatim from the current Stadtwerke Aalen page, plus the second table
# of the page (office opening hours) which must be ignored.
SAMPLE_HTML = """
<html>
<body>
<table class="table">
<thead>
<tr>
<th colspan="3" scope="col">Unsere Parkhäuser in Aalen</th>
</tr>
</thead>
<tbody>
<tr>
<th scope="row">P1 Rathaus</th>
<td>75 freie Plätze</td>
<td><span class="badge badge-success">geöffnet</span></td>
</tr>
<tr>
<th scope="row">P2 Reichsstädter Markt</th>
<td>116 freie Plätze</td>
<td><span class="badge badge-success">geöffnet</span></td>
</tr>
<tr>
<th scope="row">P3 Spritzenhausplatz</th>
<td>42 freie Plätze</td>
<td><span class="badge badge-success">geöffnet</span></td>
</tr>
<tr>
<th scope="row">P5 Spitalstraße</th>
<td>66 freie Plätze</td>
<td><span class="badge badge-success">geöffnet</span></td>
</tr>
<tr>
<th scope="row">P6 Bahnhof</th>
<td>81 freie Plätze</td>
<td><span class="badge badge-success">geöffnet</span></td>
</tr>
<tr>
<th scope="row">P1 Kubus</th>
<td>0 freie Plätze</td>
<td><span class="badge badge-warning">besetzt</span></td>
</tr>
</tbody>
</table>
<table class="table table-sm table-borderless font-weight-bold">
<tbody>
<tr><td>Mo:</td><td>08.00 - 13.00 Uhr</td></tr>
<tr><td>Di:</td><td>13.00 - 17.00 Uhr</td></tr>
</tbody>
</table>
</body>
</html>
"""

CLOSED_ROW_HTML = """
<table class="table"><tbody>
<tr>
<th scope="row">P4 Testgarage</th>
<td>geschlossen</td>
<td><span class="badge badge-danger">geschlossen</span></td>
</tr>
</tbody></table>
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

    def test_extracts_six_garages_in_page_order(self):
        garages = _make_connector().normalize(SAMPLE_HTML)

        assert [g.name for g in garages] == [
            "P1 Rathaus",
            "P2 Reichsstädter Markt",
            "P3 Spritzenhausplatz",
            "P5 Spitalstraße",
            "P6 Bahnhof",
            "P1 Kubus",
        ]
        assert [g.free_spots for g in garages] == [75, 116, 42, 66, 81, 0]

    def test_open_state_from_badge(self):
        garages = {g.name: g for g in _make_connector().normalize(SAMPLE_HTML)}

        assert garages["P1 Rathaus"].is_open is True
        assert garages["P1 Rathaus"].status_text == "geöffnet"
        assert garages["P1 Kubus"].free_spots == 0
        assert garages["P1 Kubus"].status_text == "besetzt"
        assert garages["P1 Kubus"].is_open is True

    def test_closed_garage_has_zero_free_and_is_not_open(self):
        garages = _make_connector().normalize(CLOSED_ROW_HTML)

        assert len(garages) == 1
        assert garages[0].free_spots == 0
        assert garages[0].is_open is False

    def test_opening_hours_table_is_ignored(self):
        names = [g.name for g in _make_connector().normalize(SAMPLE_HTML)]
        assert not any("Mo" == n.rstrip(":") for n in names)
        assert len(names) == 6

    def test_returns_empty_for_unparseable_html(self):
        """normalize() returns empty list for unparseable HTML."""
        assert _make_connector().normalize(UNPARSEABLE_HTML) == []

    def test_capacity_unknown_leaves_total_and_occupancy_empty(self):
        garages = _make_connector().normalize(SAMPLE_HTML)
        rathaus = next(g for g in garages if g.name == "P1 Rathaus")
        assert rathaus.total_spots is None
        assert rathaus.occupancy_pct is None

    def test_known_capacity_gives_total_and_occupancy(self):
        table = {"rathaus": {"lat": 48.8, "lon": 10.0, "capacity": 100}}
        with patch.dict("app.connectors.parking.GARAGES", table, clear=True):
            garages = _make_connector().normalize(SAMPLE_HTML)

        rathaus = next(g for g in garages if g.name == "P1 Rathaus")
        assert rathaus.total_spots == 100
        assert rathaus.occupancy_pct == pytest.approx(25.0)
        kubus = next(g for g in garages if g.name == "P1 Kubus")
        assert kubus.total_spots is None

    def test_free_spots_are_clamped_to_capacity(self):
        table = {"rathaus": {"lat": 48.8, "lon": 10.0, "capacity": 50}}
        with patch.dict("app.connectors.parking.GARAGES", table, clear=True):
            garages = _make_connector().normalize(SAMPLE_HTML)

        rathaus = next(g for g in garages if g.name == "P1 Rathaus")
        assert rathaus.free_spots == 50
        assert rathaus.occupancy_pct == 0.0


class TestMatching:
    """Garage names resolve to different slugs and the right static entries."""

    def test_two_p1_garages_have_different_slugs(self):
        assert _slugify("P1 Rathaus") != _slugify("P1 Kubus")
        assert _slugify("P2 Reichsstädter Markt") == "p2-reichsstaedter-markt"

    def test_umlaut_and_sharp_s_names_match_static_entries(self):
        assert _find_entry("P2 Reichsstädter Markt") is GARAGES["reichsstaedter"]
        assert _find_entry("P5 Spitalstraße") is GARAGES["spitalstr"]

    def test_unknown_garage_has_no_entry(self):
        assert _find_entry("P3 Spritzenhausplatz") is None
        assert _find_entry("P1 Kubus") is None


class TestRun:
    """run() writes properties incl. state, code and an approximate-location flag."""

    @pytest.mark.asyncio
    async def test_run_upserts_one_feature_per_garage(self):
        connector = _make_connector()
        connector.fetch = AsyncMock(return_value=SAMPLE_HTML)
        connector.upsert_feature = AsyncMock(return_value="uuid")
        connector._update_staleness = AsyncMock()

        await connector.run()

        calls = {c.kwargs["source_id"]: c.kwargs for c in connector.upsert_feature.await_args_list}
        assert set(calls) == {
            "parking:p1-rathaus",
            "parking:p2-reichsstaedter-markt",
            "parking:p3-spritzenhausplatz",
            "parking:p5-spitalstrasse",
            "parking:p6-bahnhof",
            "parking:p1-kubus",
        }
        rathaus = calls["parking:p1-rathaus"]["properties"]
        assert rathaus["garage_code"] == "P1"
        assert rathaus["free_spots"] == 75
        assert rathaus["is_open"] is True
        assert rathaus["status_text"] == "geöffnet"
        assert rathaus["location_approximate"] is True
        assert "total_spots" not in rathaus or rathaus["total_spots"] is None
        reichs = calls["parking:p2-reichsstaedter-markt"]["properties"]
        assert "location_approximate" not in reichs
        connector._update_staleness.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_run_without_garages_does_not_touch_staleness(self):
        connector = _make_connector()
        connector.fetch = AsyncMock(return_value=UNPARSEABLE_HTML)
        connector.upsert_feature = AsyncMock()
        connector._update_staleness = AsyncMock()

        await connector.run()

        connector.upsert_feature.assert_not_awaited()
        connector._update_staleness.assert_not_awaited()


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

    def test_capacity_and_percentage_are_optional(self):
        garage = ParkingGarage(name="P1 Rathaus", free_spots=75)
        assert garage.total_spots is None
        assert garage.occupancy_pct is None
        assert garage.is_open is None
        assert garage.status_text is None

    def test_rejects_zero_total_spots_when_given(self):
        with pytest.raises(Exception):
            ParkingGarage(name="Test", free_spots=0, total_spots=0)
