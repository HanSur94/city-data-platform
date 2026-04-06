"""Pydantic model for LHP (Landesuebergreifendes Hochwasserportal) gauge data.

Wraps the attributes from the lhpapi library's HochwasserPortalAPI for
validation before connector processing.

License: Datenlizenz Deutschland
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class LhpGaugeReading(BaseModel):
    """Validated gauge reading from LHP API."""

    name: str
    level: float | None = None
    flow: float | None = None
    stage: int | None = None
    last_update: datetime | None = None
    url: str | None = None
    hint: str | None = None
