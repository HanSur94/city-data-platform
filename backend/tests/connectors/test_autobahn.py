"""Test stubs for AutobahnConnector — Wave 0 RED state (Phase 7, Plan 02).

Autobahn GmbH des Bundes provides roadworks and traffic data via REST API
at verkehr.autobahn.de.
These stubs define the expected behavior before implementation.
"""
from __future__ import annotations

import pytest


def test_autobahn_roadworks_parse() -> None:
    """Autobahn API roadworks JSON is parsed into Observation objects.

    The /roadworks endpoint returns a list of roadwork objects with
    coordinates and descriptions. Each roadwork becomes one Observation
    with domain='traffic' and congestion_level='congested'.
    """
    pytest.skip("RED: Autobahn connector not implemented")


def test_autobahn_filter_by_distance() -> None:
    """Only roadworks within 50km of the town center are returned.

    Aalen center: (10.09, 48.84). Roadworks further than 50km should
    be filtered out before normalization to keep data relevant.
    """
    pytest.skip("RED: Autobahn connector not implemented")
