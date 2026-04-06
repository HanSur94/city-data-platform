"""Pydantic models for LUBW WFS GeoJSON responses.

Used by LubwWfsConnector to validate WFS feature collections from:
- Naturschutzgebiet (nature protection zones)
- Wasserschutzgebiet (water protection zones)

License: Datenlizenz Deutschland – Namensnennung – Version 2.0 (DL-DE-BY-2.0)
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class LubwWfsGeometry(BaseModel):
    type: str  # "Polygon", "MultiPolygon", etc.
    coordinates: list[Any]


class LubwWfsFeature(BaseModel):
    type: str = "Feature"
    id: str | None = None
    geometry: LubwWfsGeometry | None = None
    properties: dict[str, Any] = {}


class LubwWfsFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: list[LubwWfsFeature] = []
