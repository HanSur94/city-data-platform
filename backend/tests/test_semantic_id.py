"""Tests for compute_semantic_id function.

Covers all domain mappings and fallback behavior.
"""
import pytest
from app.connectors.base import compute_semantic_id


class TestComputeSemanticId:
    """Test semantic ID generation for each domain type."""

    def test_buildings(self):
        assert compute_semantic_id("buildings", "DEBWAL330000aBcD") == "bldg_DEBWAL330000aBcD"

    def test_traffic_flow(self):
        assert compute_semantic_id("traffic-flow", "seg_123") == "road_seg_123"

    def test_transit(self):
        assert compute_semantic_id("transit", "de:08136:7810") == "stop_de:08136:7810"

    def test_air_quality_sensor(self):
        assert compute_semantic_id("air_quality", "uba_238") == "sensor_air_quality_uba_238"

    def test_parking(self):
        assert compute_semantic_id("parking", "stadtmitte") == "parking_stadtmitte"

    def test_infrastructure_ev_charging(self):
        assert compute_semantic_id("infrastructure", "ocpdb_12345", source="ev-charging") == "evcharger_ocpdb_12345"

    def test_water(self):
        assert compute_semantic_id("water", "huettlingen") == "gauge_huettlingen"

    def test_air_quality_grid(self):
        assert compute_semantic_id("air_quality", "grid_48.83_10.09", feature_type="air_grid") == "grid_air_quality_48.83_10.09"

    def test_unknown_domain_fallback(self):
        assert compute_semantic_id("some_new_domain", "xyz_123") == "some_new_domain_xyz_123"

    def test_road_in_domain_name(self):
        """Domain containing 'road' should map to road_ prefix."""
        assert compute_semantic_id("road_sensors", "s42") == "road_s42"
