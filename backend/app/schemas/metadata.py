# backend/app/schemas/metadata.py
"""Response schemas for layer metadata transparency endpoint."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

# ok            - connectors delivered data recently enough
# stale         - newest delivery is older than the layer's staleness threshold
# never_fetched - the layer has connectors but none has ever delivered data
# static        - the layer has no connector (static / bundled data)
LayerStatus = Literal["ok", "stale", "never_fetched", "static"]


class LayerMetadataItem(BaseModel):
    layer_key: str
    source_name: str
    source_url: str
    data_type: str  # LIVE | SCRAPED | INTERPOLATED | MODELED | STATIC
    update_interval_seconds: int | None
    license: str
    license_url: str
    last_updated: datetime | None
    status: LayerStatus


class LayerMetadataResponse(BaseModel):
    town: str
    layers: list[LayerMetadataItem]
