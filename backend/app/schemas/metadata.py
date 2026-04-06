# backend/app/schemas/metadata.py
"""Response schemas for layer metadata transparency endpoint."""
from datetime import datetime

from pydantic import BaseModel


class LayerMetadataItem(BaseModel):
    layer_key: str
    source_name: str
    source_url: str
    data_type: str  # LIVE | SCRAPED | INTERPOLATED | MODELED | STATIC
    update_interval_seconds: int | None
    license: str
    license_url: str
    last_updated: datetime | None


class LayerMetadataResponse(BaseModel):
    town: str
    layers: list[LayerMetadataItem]
