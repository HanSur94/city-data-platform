"""GTFSConnector: downloads NVBW bwgesamt GTFS feed, bbox-filters stops and
route shapes to the configured town bounds, and upserts them as spatial
features into the features table.

Static topology only — does NOT call persist() / transit_positions.
GTFS-RT vehicle positions are handled by a separate connector.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import gtfs_kit
import httpx

from app.connectors.base import BaseConnector, Observation


class GTFSConnector(BaseConnector):
    """Downloads NVBW bwgesamt GTFS zip, filters to town bbox, upserts features.

    Config keys:
        gtfs_url (str): URL of the GTFS zip file to download.

    Upserts stop Points and route shape LineStrings into the `features` table.
    Does NOT write to `transit_positions` — that table is for live GTFS-RT data.
    """

    async def fetch(self) -> bytes:
        """Download the GTFS zip from gtfs_url.  Returns raw bytes.

        Uses a 120-second timeout — the bwgesamt zip is ~50 MB.

        Raises:
            ValueError: If the response is empty (len == 0).
            httpx.HTTPError: On network failure or non-2xx response.
        """
        import os
        url = self.config.config["gtfs_url"]
        cache_path = Path("/tmp/gtfs_cache.zip")

        # Use cached file if less than 24h old
        if cache_path.exists():
            age_hours = (Path(cache_path).stat().st_mtime - __import__('time').time()) / -3600
            if age_hours < 24:
                return cache_path.read_bytes()

        async with httpx.AsyncClient(
            timeout=600.0,
            follow_redirects=True,
            headers={"User-Agent": "CityDataPlatform/2.0"},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            raw = response.content
        if len(raw) == 0:
            raise ValueError(f"Empty response from GTFS URL: {url}")

        # Cache for other connectors (BusInterpolationConnector)
        cache_path.write_bytes(raw)
        return raw

    def normalize(self, raw: bytes) -> list[Observation]:
        """Parse GTFS bytes and return bbox-filtered stop + shape Observations.

        Stops outside the town bounding box are excluded immediately after
        parsing — this prevents loading all 55k+ stops from bwgesamt.

        Shapes are included if any shape point lies within the bbox.

        Args:
            raw: Raw bytes of a GTFS zip file.

        Returns:
            List of Observations with feature_id="PENDING".
            run() replaces PENDING with real UUIDs via upsert_feature().

        Raises:
            Exception: If raw bytes cannot be parsed as a GTFS feed (e.g. empty).
        """
        # gtfs-kit 12.x only accepts Path/str — write to a temp file in memory
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp.write(raw)
            tmp_path = Path(tmp.name)
        try:
            feed = gtfs_kit.read_feed(tmp_path, dist_units="km")
        finally:
            tmp_path.unlink(missing_ok=True)

        bbox = self.town.bbox
        observations: list[Observation] = []

        # --- Stops (Point features) ---
        if feed.stops is None or feed.stops.empty:
            stops = []
        else:
            stops = feed.stops[
                feed.stops.stop_lat.between(bbox.lat_min, bbox.lat_max)
                & feed.stops.stop_lon.between(bbox.lon_min, bbox.lon_max)
            ]

        for row in (stops.itertuples(index=False) if hasattr(stops, "itertuples") else []):
            observations.append(
                Observation(
                    feature_id="PENDING",
                    domain="transit",
                    source_id=f"stop:{row.stop_id}",
                    values={
                        "geometry_type": "Point",
                        "feature_type": "stop",
                        "stop_name": row.stop_name,
                        "lat": float(row.stop_lat),
                        "lon": float(row.stop_lon),
                    },
                )
            )

        # --- Shapes (LineString features) ---
        if hasattr(feed, "shapes") and feed.shapes is not None and not feed.shapes.empty:
            for shape_id, group in feed.shapes.groupby("shape_id"):
                pts = group.sort_values("shape_pt_sequence")
                # Include shape if any point is within the bbox
                in_bbox = (
                    pts.shape_pt_lat.between(bbox.lat_min, bbox.lat_max)
                    & pts.shape_pt_lon.between(bbox.lon_min, bbox.lon_max)
                ).any()
                if not in_bbox:
                    continue
                coords = " , ".join(
                    f"{row.shape_pt_lon} {row.shape_pt_lat}"
                    for row in pts.itertuples(index=False)
                )
                wkt = f"LINESTRING({coords})"
                observations.append(
                    Observation(
                        feature_id="PENDING",
                        domain="transit",
                        source_id=f"shape:{shape_id}",
                        values={
                            "geometry_type": "LineString",
                            "feature_type": "shape",
                            "linestring_wkt": wkt,
                        },
                    )
                )

        return observations

    async def run(self) -> None:
        """Fetch GTFS, bbox-filter, upsert all features, update staleness.

        Overrides BaseConnector.run() because transit stops/shapes go into the
        `features` table (static topology) — not into `transit_positions`.
        Does NOT call persist().
        """
        raw = await self.fetch()
        normalized = self.normalize(raw)

        for item in normalized:
            geom_type = item.values["geometry_type"]
            if geom_type == "Point":
                wkt = f"POINT({item.values['lon']} {item.values['lat']})"
            else:
                wkt = item.values["linestring_wkt"]

            properties = {k: v for k, v in item.values.items() if k != "linestring_wkt"}

            await self.upsert_feature(
                source_id=item.source_id,
                domain="transit",
                geometry_wkt=wkt,
                properties=properties,
            )

        await self._update_staleness()
