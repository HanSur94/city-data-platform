"""Test stubs for MobiDataBWConnector — Wave 0 RED state (Phase 7, Plan 02).

MobiData BW provides traffic count data for Baden-Wuerttemberg roads.
These stubs define the expected behavior before implementation.
"""
from __future__ import annotations

import pytest


def test_mobidata_csv_parse() -> None:
    """MobiData BW CSV traffic data is parsed correctly.

    MobiData BW uses a CSV format similar to BASt but with BW-specific
    station IDs and column layout. Parser must handle BW encoding and
    produce Observation objects with domain='traffic'.
    """
    pytest.skip("RED: MobiData BW connector not implemented")


def test_mobidata_normalize_shares_bast_format() -> None:
    """MobiData BW normalize() output matches BASt output schema.

    Both connectors produce Observations with identical values keys:
    vehicle_count_total, vehicle_count_hgv, speed_avg_kmh, congestion_level.
    This ensures both sources feed the same traffic_readings hypertable.
    """
    pytest.skip("RED: MobiData BW connector not implemented")
