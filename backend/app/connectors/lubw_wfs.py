"""LubwWfsConnector: fetches environmental zone polygons from LUBW WFS.

Implements WATR-05: retrieves Naturschutzgebiet and Wasserschutzgebiet features
from the LUBW (Landesanstalt für Umwelt Baden-Württemberg) WFS endpoints and
stores them in the features table as water-domain features.

These are static/slow-changing features — polled once per day (86400s).

License: Datenlizenz Deutschland – Namensnennung – Version 2.0 (DL-DE-BY-2.0)
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.connectors.base import BaseConnector, Observation
from app.config import ConnectorConfig, Town
from app.models.lubw_wfs import LubwWfsFeatureCollection

logger = logging.getLogger(__name__)

# LUBW WFS endpoints keyed by feature type prefix
# Maps: prefix -> (base_url, WFS typeNames value)
LUBW_WFS_ENDPOINTS: dict[str, tuple[str, str]] = {
    "naturschutz": (
        "https://rips-gdi.lubw.baden-wuerttemberg.de/arcgis/services/wfs/Naturschutzgebiet/MapServer/WFSServer",
        "Naturschutzgebiet",
    ),
    "wasserschutz": (
        "https://rips-gdi.lubw.baden-wuerttemberg.de/arcgis/services/wfs/Wasserschutzgebiet/MapServer/WFSServer",
        "Wasserschutzgebiet",
    ),
}


def _compute_centroid_wkt(geometry: Any) -> str:
    """Compute centroid WKT from a polygon geometry.

    Tries shapely first (already a dependency via geopandas).
    Falls back to ring-average centroid if shapely is unavailable.

    Args:
        geometry: LubwWfsGeometry object with type and coordinates.

    Returns:
        WKT string like "POINT(lon lat)".
    """
    try:
        from shapely.geometry import shape
        from shapely.wkt import dumps as to_wkt

        geom_dict = {
            "type": geometry.type,
            "coordinates": geometry.coordinates,
        }
        shapely_geom = shape(geom_dict)
        centroid = shapely_geom.centroid
        return f"POINT({centroid.x} {centroid.y})"
    except ImportError:
        # Fallback: average of exterior ring coordinates
        coords = geometry.coordinates[0]  # outer ring of first polygon ring
        lon = sum(c[0] for c in coords) / len(coords)
        lat = sum(c[1] for c in coords) / len(coords)
        return f"POINT({lon} {lat})"
    except Exception as exc:
        logger.warning("Could not compute centroid for geometry %s: %s", geometry.type, exc)
        # Last resort: return a zero-coordinate point rather than crashing
        raise


class LubwWfsConnector(BaseConnector):
    """Fetches Naturschutzgebiet and Wasserschutzgebiet polygons from LUBW WFS.

    Overrides run() — does NOT use the fetch→normalize→persist pipeline.
    Instead: fetch → for each feature, upsert_feature() → update_staleness().

    Config keys (from ConnectorConfig.config dict):
        attribution: str  — Attribution string for data provenance (optional).
    """

    async def fetch(self) -> dict[str, dict]:
        """Fetch features from both LUBW WFS endpoints.

        Uses the town bbox (from self.town.bbox) to spatially filter features.
        BBOX format: "lat_min,lon_min,lat_max,lon_max,crs" per WFS 2.0 convention.

        Returns:
            Dict with keys "naturschutz" and "wasserschutz", each containing
            the full raw GeoJSON FeatureCollection dict from the WFS response.

        Raises:
            httpx.HTTPError: On network/HTTP failure.
        """
        bbox = self.town.bbox
        # WFS 2.0 BBOX: lat_min,lon_min,lat_max,lon_max,CRS
        bbox_param = (
            f"{bbox.lat_min},{bbox.lon_min},{bbox.lat_max},{bbox.lon_max},"
            "urn:ogc:def:crs:EPSG::4326"
        )

        results: dict[str, dict] = {}

        async with httpx.AsyncClient(timeout=60.0) as client:
            for ft_type, (url, type_name) in LUBW_WFS_ENDPOINTS.items():
                params = {
                    "service": "WFS",
                    "version": "2.0.0",
                    "request": "GetFeature",
                    "typeNames": type_name,
                    "outputFormat": "application/json",
                    "srsName": "urn:ogc:def:crs:EPSG::4326",
                    "BBOX": bbox_param,
                }
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                results[ft_type] = data
                logger.info(
                    "LUBW WFS %s: fetched %d features for %s",
                    ft_type,
                    len(data.get("features", [])),
                    self.town.id,
                )

        return results

    def normalize(self, raw: Any) -> list[Observation]:
        """Not used by run() — returns empty list.

        LubwWfsConnector stores features via upsert_feature(), not observations.
        This method exists to satisfy the BaseConnector ABC.
        """
        return []

    async def run(self) -> None:
        """Fetch WFS features and upsert each one into the features table.

        Overrides BaseConnector.run(). For each feature type and each feature:
        1. Validate via Pydantic models
        2. Compute centroid WKT from polygon geometry
        3. Call upsert_feature() with domain="water"
        4. Update staleness timestamp

        WFS returning 0 features (no zones in bbox) is valid — run() completes
        without error in that case.
        """
        raw = await self.fetch()

        for ft_type, fc_dict in raw.items():
            fc = LubwWfsFeatureCollection.model_validate(fc_dict)

            for feat in fc.features:
                if feat.geometry is None:
                    logger.debug(
                        "Skipping %s feature %s — no geometry", ft_type, feat.id
                    )
                    continue

                try:
                    wkt = _compute_centroid_wkt(feat.geometry)
                except Exception as exc:
                    logger.warning(
                        "Skipping %s feature %s — centroid error: %s",
                        ft_type, feat.id, exc,
                    )
                    continue

                # Build source_id: prefer feature .id, fall back to NSG_NR/WSG_NR or "?"
                feat_id = feat.id
                if not feat_id:
                    feat_id = feat.properties.get(
                        "NSG_NR", feat.properties.get("WSG_NR", "?")
                    )

                source_id = f"{ft_type}:{feat_id}"

                await self.upsert_feature(
                    source_id=source_id,
                    domain="water",
                    geometry_wkt=wkt,
                    properties=feat.properties,
                )

        await self._update_staleness()
