"""Test stubs for BastConnector — Wave 0 RED state (Phase 7, Plan 02).

BASt (Bundesanstalt fuer Strassenwesen) publishes traffic count CSV data.
These stubs define the expected behavior before implementation.
"""
from __future__ import annotations

import pytest


def test_bast_csv_parse_returns_observations() -> None:
    """BASt CSV parsing produces Observation objects with traffic domain.

    BASt publishes hourly vehicle counts per station as CSV.
    Parser must produce one Observation per row with feature_id mapped
    to the BASt station ID and domain set to 'traffic'.
    """
    pytest.skip("RED: BASt connector not implemented")


def test_bast_normalize_computes_congestion_level() -> None:
    """Congestion level is derived from flow-to-capacity ratio.

    When flow exceeds 80% of road capacity: 'congested'.
    When flow is between 50% and 80%: 'moderate'.
    Below 50%: 'free'.
    """
    pytest.skip("RED: BASt connector not implemented")


def test_bast_feature_upsert_source_id_format() -> None:
    """source_id for BASt features follows the format 'bast:{station_id}'.

    Example: BASt station 9440 -> source_id = 'bast:9440'.
    This ensures uniqueness within the features table across connectors.
    """
    pytest.skip("RED: BASt connector not implemented")
