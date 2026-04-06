"""Test stubs for SmardConnector — Wave 0 RED state (Phase 7, Plan 02).

SMARD (Bundesnetzagentur) provides electricity generation and price data
for Germany via a two-step fetch pattern (index + data).
These stubs define the expected behavior before implementation.
"""
from __future__ import annotations

import pytest


def test_smard_two_step_fetch() -> None:
    """SMARD fetch requires two API calls: index then data.

    Step 1: GET /chart_data/{filter}/{region}/index_{resolution}.json
    Step 2: GET /chart_data/{filter}/{region}/{resolution}_{timestamp}.json
    The connector must chain these calls and return the combined dataset.
    """
    pytest.skip("RED: SMARD connector not implemented")


def test_smard_null_filtering() -> None:
    """SMARD data points with null values are filtered before persisting.

    SMARD API returns null for missing data points. These must be dropped
    rather than stored as None to avoid polluting the energy time-series.
    """
    pytest.skip("RED: SMARD connector not implemented")


def test_smard_renewable_percent_calculation() -> None:
    """renewable_percent is correctly computed from generation mix.

    Renewables include: wind_offshore, wind_onshore, photovoltaic,
    biomass, hydropower, other_renewables.
    renewable_percent = sum(renewables) / sum(all_sources) * 100.
    Result must be between 0.0 and 100.0.
    """
    pytest.skip("RED: SMARD connector not implemented")
