"""MastrConnector: fetches renewable energy installations from Marktstammdatenregister.

Implements ENRG-03: downloads bulk MaStR data via open-mastr, filters to
Ostalbkreis, and upserts each installation as a spatial feature.

MaStR via open-mastr:
    from open_mastr import Mastr
    db = Mastr()
    db.download(data=["solar_extended", "wind_extended", "storage_units"])

DataFrame columns of interest:
    - Breitengrad: latitude
    - Laengengrad: longitude
    - Nettonennleistung: net capacity in kW
    - Inbetriebnahmedatum: commissioning date
    - Landkreis: district name (filter: "Ostalbkreis")
    - Lage: mounting type ("Aufdach" = rooftop, "Freiflaeche" = ground)
    - EinheitMastrNummer: unique installation ID

License: Marktstammdatenregister (BNetzA), open data
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.connectors.base import BaseConnector, Observation
from app.config import ConnectorConfig, Town

logger = logging.getLogger(__name__)

LANDKREIS_FILTER = "Ostalbkreis"
TECHNOLOGY_TYPES = ["solar_extended", "wind_extended", "storage_units"]

# Cache TTL: 24 hours in seconds
_CACHE_TTL_SECONDS = 86400


def _classify_installation(row: dict[str, Any]) -> str:
    """Classify a MaStR installation row into a human-readable type label.

    Classification logic:
    - Solar + Lage contains "Bauliche Anlagen", "Aufdach", or "Hausdach" -> "solar_rooftop"
    - Solar + Lage contains "Freifläche" or "Freiflaeche" -> "solar_ground"
    - Wind technology -> "wind"
    - Storage technology -> "battery"
    - Fallback -> "unknown"

    Args:
        row: DataFrame row as dict.

    Returns:
        Installation type label string.
    """
    technology = str(row.get("Technologie", "")).lower()
    lage = str(row.get("Lage", ""))

    if "solar" in technology:
        lage_lower = lage.lower()
        # Rooftop first: Bauliche Anlagen, Aufdach, Hausdach
        # Note: "Bauliche Anlagen (Hausdach, Gebaeude und Freiflaechenanlagen)" contains
        # "freifl" too, so check rooftop indicators before ground-mounted.
        if any(keyword in lage_lower for keyword in ("bauliche", "aufdach", "hausdach")):
            return "solar_rooftop"
        # Ground-mounted: standalone Freiflaeche / Freifläche
        if "freifl" in lage_lower:
            return "solar_ground"
        # Default solar classification
        return "solar_rooftop"

    if "wind" in technology:
        return "wind"

    if "storage" in technology or "speicher" in technology:
        return "battery"

    return "unknown"


class MastrConnector(BaseConnector):
    """Downloads MaStR renewable installation data and upserts as spatial features.

    Filters bulk data to Ostalbkreis (Aalen's district) and upserts each
    valid installation (with lat/lon) into the features table.

    No time-series data is produced — this is a features-only connector.
    The open-mastr download is cached for 24 hours to avoid repeated large
    bulk downloads (Pitfall 4: open-mastr download takes several minutes).

    Config keys (from ConnectorConfig.config dict):
        cache_dir: str — Override default open-mastr cache directory.
    """

    def __init__(self, config: ConnectorConfig, town: Town) -> None:
        super().__init__(config, town)

    def _get_mastr_db_path(self) -> Path:
        """Return the path to the open-mastr SQLite database file."""
        # open-mastr stores its SQLite DB in ~/.open-MaStR/data/
        home = Path.home()
        return home / ".open-MaStR" / "data" / "model_data" / "open_mastr.db"

    def _is_cache_fresh(self) -> bool:
        """Check if the open-mastr SQLite database exists and is less than 24h old."""
        db_path = self._get_mastr_db_path()
        if not db_path.exists():
            return False
        mtime = db_path.stat().st_mtime
        age_seconds = datetime.now(timezone.utc).timestamp() - mtime
        return age_seconds < _CACHE_TTL_SECONDS

    def _filter_by_landkreis(self, raw: bytes) -> list[dict[str, Any]]:
        """Filter raw JSON records to only rows matching LANDKREIS_FILTER.

        Args:
            raw: JSON bytes of records (list of dicts from DataFrame).

        Returns:
            Filtered list of row dicts with Landkreis == LANDKREIS_FILTER.
        """
        records: list[dict[str, Any]] = json.loads(raw)
        return [r for r in records if r.get("Landkreis") == LANDKREIS_FILTER]

    async def fetch(self) -> bytes:
        """Download MaStR data via open-mastr, filter to Ostalbkreis, return JSON bytes.

        Skips download if local cache is fresh (< 24h old). Reads from
        open-mastr SQLite tables and returns filtered records as JSON bytes.

        Returns:
            JSON bytes: list of installation dicts filtered to Ostalbkreis.
        """
        import pandas as pd

        if not self._is_cache_fresh():
            logger.info("open-mastr cache stale or missing — downloading bulk data...")
            from open_mastr import Mastr  # type: ignore[import]
            db = Mastr()
            db.download(data=TECHNOLOGY_TYPES)
        else:
            logger.info("open-mastr cache is fresh — skipping download")

        # Read from open-mastr SQLite DB
        from open_mastr import Mastr  # type: ignore[import]
        import sqlite3

        db_path = self._get_mastr_db_path()
        if not db_path.exists():
            logger.warning("open-mastr DB not found at %s — returning empty", db_path)
            return b"[]"

        # Table names per open-mastr schema
        table_map = {
            "solar_extended": "solar_extended",
            "wind_extended": "wind_extended",
            "storage_units": "storage_units",
        }

        frames: list[pd.DataFrame] = []
        with sqlite3.connect(str(db_path)) as conn:
            for tech_type, table_name in table_map.items():
                try:
                    df = pd.read_sql_query(
                        f"SELECT * FROM {table_name} WHERE Landkreis = ?",
                        conn,
                        params=(LANDKREIS_FILTER,),
                    )
                    if not df.empty:
                        df["Technologie"] = tech_type.replace("_extended", "").replace("_units", "")
                        frames.append(df)
                except Exception as exc:
                    logger.warning("Could not read table %s: %s", table_name, exc)

        if not frames:
            return b"[]"

        import pandas as pd
        combined = pd.concat(frames, ignore_index=True)
        return combined.to_json(orient="records").encode()

    def normalize(self, raw: bytes, **kwargs: Any) -> list[Observation]:
        """Return empty list — MaStR is features-only, no time-series data.

        Args:
            raw: JSON bytes (unused).
            **kwargs: Ignored.

        Returns:
            Empty list.
        """
        return []

    async def run(self) -> None:
        """Full pipeline: download MaStR data, filter, upsert features.

        Overrides BaseConnector.run() to:
        1. Fetch (download if stale) and filter to Ostalbkreis
        2. For each valid installation with lat/lon, upsert a spatial feature
        3. No persist() call (features-only connector)
        4. Update staleness timestamp
        """
        import json as _json

        raw = await self.fetch()
        records: list[dict[str, Any]] = _json.loads(raw)

        logger.info(
            "MastrConnector: processing %d Ostalbkreis installations", len(records)
        )

        for row in records:
            lat = row.get("Breitengrad")
            lon = row.get("Laengengrad")

            # Skip records without valid coordinates
            if lat is None or lon is None:
                continue

            try:
                lat_f = float(lat)
                lon_f = float(lon)
            except (TypeError, ValueError):
                continue

            mastr_id = row.get("EinheitMastrNummer", "")
            if not mastr_id:
                continue

            installation_type = _classify_installation(row)
            capacity_raw = row.get("Nettonennleistung")
            capacity_kw: float | None = None
            if capacity_raw is not None:
                try:
                    capacity_kw = float(capacity_raw)
                except (TypeError, ValueError):
                    pass

            try:
                await self.upsert_feature(
                    source_id=f"mastr:{mastr_id}",
                    domain="energy",
                    geometry_wkt=f"POINT({lon_f} {lat_f})",
                    properties={
                        "installation_type": installation_type,
                        "capacity_kw": capacity_kw,
                        "commissioning_date": str(row.get("Inbetriebnahmedatum", "")),
                        "operator": row.get("AnlagenbetreiberMastrNummer", ""),
                        "municipality": row.get("Standort", ""),
                        "attribution": "Marktstammdatenregister (BNetzA)",
                    },
                )
            except Exception as exc:
                logger.warning(
                    "Failed to upsert MaStR feature %s: %s", mastr_id, exc
                )

        await self._update_staleness()
