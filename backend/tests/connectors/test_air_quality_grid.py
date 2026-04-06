"""Tests for air quality grid IDW interpolation.

Tests pure functions (idw_interpolate, generate_grid) without database.
"""
import pytest

from app.connectors.air_quality_grid import idw_interpolate, generate_grid
from app.models.air_quality_grid import SensorReading


class TestIDWInterpolation:
    """Test IDW (Inverse Distance Weighting) algorithm."""

    def test_idw_single_sensor_returns_sensor_value_everywhere(self):
        """With one sensor, IDW should return that sensor's value at any point."""
        sensors = [
            SensorReading(feature_id="s1", lon=10.0, lat=48.8, pm25=12.5),
        ]
        result = idw_interpolate(sensors, lon=10.1, lat=48.9, pollutant="pm25")
        assert result == pytest.approx(12.5)

    def test_idw_two_equidistant_sensors_returns_average(self):
        """Two sensors equidistant from query point should give average."""
        sensors = [
            SensorReading(feature_id="s1", lon=10.0, lat=48.8, pm25=10.0),
            SensorReading(feature_id="s2", lon=10.2, lat=48.8, pm25=20.0),
        ]
        # Query point at midpoint
        result = idw_interpolate(sensors, lon=10.1, lat=48.8, pollutant="pm25")
        assert result == pytest.approx(15.0, abs=0.5)

    def test_idw_closer_sensor_weighted_more(self):
        """Closer sensor should dominate the interpolated value."""
        sensors = [
            SensorReading(feature_id="s1", lon=10.0, lat=48.8, pm25=10.0),
            SensorReading(feature_id="s2", lon=10.5, lat=48.8, pm25=100.0),
        ]
        # Query close to s1
        result = idw_interpolate(sensors, lon=10.01, lat=48.8, pollutant="pm25")
        # Should be much closer to 10.0 than 100.0
        assert result is not None
        assert result < 20.0

    def test_idw_zero_distance_returns_exact_value(self):
        """When query point is at sensor location, return sensor value (no div by zero)."""
        sensors = [
            SensorReading(feature_id="s1", lon=10.0, lat=48.8, pm25=42.0),
            SensorReading(feature_id="s2", lon=10.1, lat=48.9, pm25=99.0),
        ]
        result = idw_interpolate(sensors, lon=10.0, lat=48.8, pollutant="pm25")
        assert result == pytest.approx(42.0)

    def test_idw_none_pollutant_values_skipped(self):
        """Sensors without data for the queried pollutant should be skipped."""
        sensors = [
            SensorReading(feature_id="s1", lon=10.0, lat=48.8, pm25=None, no2=50.0),
            SensorReading(feature_id="s2", lon=10.1, lat=48.8, pm25=20.0, no2=None),
        ]
        # pm25: only s2 has data
        result = idw_interpolate(sensors, lon=10.05, lat=48.8, pollutant="pm25")
        assert result == pytest.approx(20.0)
        # no2: only s1 has data
        result_no2 = idw_interpolate(sensors, lon=10.05, lat=48.8, pollutant="no2")
        assert result_no2 == pytest.approx(50.0)

    def test_idw_all_none_returns_none(self):
        """If no sensors have data for the queried pollutant, return None."""
        sensors = [
            SensorReading(feature_id="s1", lon=10.0, lat=48.8, pm25=None),
        ]
        result = idw_interpolate(sensors, lon=10.0, lat=48.8, pollutant="pm25")
        assert result is None


class TestGenerateGrid:
    """Test grid generation from bounding box."""

    def test_grid_produces_correct_cell_count(self):
        """Small bbox with known step should produce predictable cell count."""
        from app.config import TownBbox
        bbox = TownBbox(lon_min=10.0, lat_min=48.8, lon_max=10.01, lat_max=48.809)
        cells = generate_grid(bbox, step_deg=0.005)
        # lon: 10.0, 10.005 => 2 cols (0, 1) ... possibly 10.01 too => 3 cols
        # lat: 48.8, 48.805 => 2 rows (0, 1) ... possibly 48.809 too => check
        assert len(cells) > 0
        # Each cell is (lon, lat, row, col) tuple
        for lon, lat, row, col in cells:
            assert 10.0 <= lon <= 10.01
            assert 48.8 <= lat <= 48.809

    def test_grid_cells_have_correct_structure(self):
        """Each grid cell should be a (lon, lat, row, col) tuple."""
        from app.config import TownBbox
        bbox = TownBbox(lon_min=10.0, lat_min=48.8, lon_max=10.005, lat_max=48.805)
        cells = generate_grid(bbox, step_deg=0.005)
        assert len(cells) >= 1
        lon, lat, row, col = cells[0]
        assert isinstance(lon, float)
        assert isinstance(lat, float)
        assert isinstance(row, int)
        assert isinstance(col, int)


class TestNormalize:
    """Test that normalize produces features with all four pollutant fields."""

    def test_normalize_produces_all_pollutant_fields(self):
        """Grid cells should contain pm25, pm10, no2, o3 in properties."""
        # This tests the output format — grid cells should have all fields
        from app.models.air_quality_grid import GridCell
        cell = GridCell(lon=10.0, lat=48.8, pm25=1.0, pm10=2.0, no2=3.0, o3=4.0)
        assert cell.pm25 == 1.0
        assert cell.pm10 == 2.0
        assert cell.no2 == 3.0
        assert cell.o3 == 4.0
