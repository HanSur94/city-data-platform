"""Tests for SolarProductionConnector pure functions.

Tests irradiance factor computation and solar output calculation.
No database required — tests pure functions only.
"""
import pytest


def test_compute_irradiance_factor_clear_sky():
    """cloud_cover=0 returns ~1.0 (clear sky)."""
    from app.connectors.solar_production import compute_irradiance_factor

    factor = compute_irradiance_factor(cloud_cover=0.0, solar_j_cm2=None)
    assert factor == pytest.approx(1.0, abs=0.01)


def test_compute_irradiance_factor_overcast():
    """cloud_cover=100 returns ~0.1 (overcast floor for diffuse radiation)."""
    from app.connectors.solar_production import compute_irradiance_factor

    factor = compute_irradiance_factor(cloud_cover=100.0, solar_j_cm2=None)
    assert factor == pytest.approx(0.1, abs=0.01)


def test_compute_irradiance_factor_half_cloudy():
    """cloud_cover=50 returns ~0.55 (linear interpolation)."""
    from app.connectors.solar_production import compute_irradiance_factor

    factor = compute_irradiance_factor(cloud_cover=50.0, solar_j_cm2=None)
    assert factor == pytest.approx(0.55, abs=0.01)


def test_compute_irradiance_factor_solar_field():
    """solar_j_cm2 available uses direct irradiance ratio (solar/30)."""
    from app.connectors.solar_production import compute_irradiance_factor

    # 15 J/cm2 -> 15/30 = 0.5
    factor = compute_irradiance_factor(cloud_cover=0.0, solar_j_cm2=15.0)
    assert factor == pytest.approx(0.5, abs=0.01)

    # 30 J/cm2 -> 30/30 = 1.0 (capped)
    factor = compute_irradiance_factor(cloud_cover=0.0, solar_j_cm2=30.0)
    assert factor == pytest.approx(1.0, abs=0.01)

    # 45 J/cm2 -> min(45/30, 1.0) = 1.0 (capped at 1.0)
    factor = compute_irradiance_factor(cloud_cover=0.0, solar_j_cm2=45.0)
    assert factor == pytest.approx(1.0, abs=0.01)


def test_compute_irradiance_factor_fallback():
    """Both None -> returns 0.5 fallback."""
    from app.connectors.solar_production import compute_irradiance_factor

    factor = compute_irradiance_factor(cloud_cover=None, solar_j_cm2=None)
    assert factor == pytest.approx(0.5, abs=0.01)


def test_compute_solar_output_normal():
    """10 kW installed with factor 0.8 returns 8.0 kW."""
    from app.connectors.solar_production import compute_solar_output

    output = compute_solar_output(capacity_kw=10.0, irradiance_factor=0.8)
    assert output == pytest.approx(8.0, abs=0.01)


def test_compute_solar_output_zero_capacity():
    """0 capacity returns 0.0."""
    from app.connectors.solar_production import compute_solar_output

    output = compute_solar_output(capacity_kw=0.0, irradiance_factor=0.8)
    assert output == pytest.approx(0.0)


def test_compute_solar_output_night():
    """Night (factor 0.0) returns 0.0."""
    from app.connectors.solar_production import compute_solar_output

    output = compute_solar_output(capacity_kw=10.0, irradiance_factor=0.0)
    assert output == pytest.approx(0.0)
