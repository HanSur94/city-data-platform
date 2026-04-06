"""Test stubs for MastrConnector — Wave 0 RED state (Phase 7, Plan 02).

Marktstammdatenregister (BNetzA) provides a registry of all energy
production units in Germany. These stubs define the expected behavior
before implementation.
"""
from __future__ import annotations

import pytest


def test_mastr_landkreis_filter() -> None:
    """Only units within Ostalbkreis (Landkreis 08136) are returned.

    MaStR covers all of Germany. The connector must filter by
    Landkreis = 'Ostalbkreis' or equivalent administrative code
    to keep results relevant for Aalen.
    """
    pytest.skip("RED: MaStR connector not implemented")


def test_mastr_lage_field_mapping() -> None:
    """Lage field is correctly mapped to installation type labels.

    'Aufdach' (rooftop) and 'Freiflaeche' (ground-mounted) are the
    two main categories for solar installations. The connector must
    map the MaStR Lage codes to these human-readable labels and
    include them in the Observation properties dict.
    """
    pytest.skip("RED: MaStR connector not implemented")
