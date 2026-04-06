"""TomTomConnector: fetches real-time traffic flow data from TomTom Flow Segment Data API.

Implements REQ-TRAFFIC-01/03/04: retrieves speed and congestion data for ~35 sample
points on Aalen arterial roads (B29, B19, Friedrichstr., Gmunder Str., etc.).

TomTom Flow Segment Data API:
    https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json
    ?point={lat},{lon}&key={api_key}&unit=KMPH

Returns currentSpeed, freeFlowSpeed, confidence, and road segment coordinates.
congestion_ratio = currentSpeed / freeFlowSpeed

Adaptive polling: 10min during rush hours (06-09, 16-19 Europe/Berlin), 30min off-peak.
The connector is scheduled at 600s (10min) intervals. During off-peak, it skips runs
if less than 1800s have elapsed since the last successful run.

License: TomTom Traffic Flow API (requires API key)
"""
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from app.connectors.base import BaseConnector, Observation
from app.config import ConnectorConfig, Town

logger = logging.getLogger(__name__)

BERLIN_TZ = ZoneInfo("Europe/Berlin")

# TomTom Flow Segment Data API base URL
TOMTOM_FLOW_URL = (
    "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
)


def _now_berlin() -> datetime:
    """Return current time in Europe/Berlin timezone. Extracted for testability."""
    return datetime.now(BERLIN_TZ)


# ---------------------------------------------------------------------------
# Aalen road segment sample points (~35 points on major arterials)
# TomTom Flow API takes a single point and returns the road segment it falls on.
# ---------------------------------------------------------------------------

AALEN_ROAD_SEGMENTS: list[dict[str, Any]] = [
    # B29 (east-west through Aalen): ~12 points from Essingen to Aalen-Ost
    {"id": "b29-east-01", "name": "B29", "lat": 48.8095, "lon": 10.0200},
    {"id": "b29-east-02", "name": "B29", "lat": 48.8120, "lon": 10.0320},
    {"id": "b29-east-03", "name": "B29", "lat": 48.8170, "lon": 10.0450},
    {"id": "b29-east-04", "name": "B29", "lat": 48.8220, "lon": 10.0570},
    {"id": "b29-east-05", "name": "B29", "lat": 48.8280, "lon": 10.0680},
    {"id": "b29-east-06", "name": "B29", "lat": 48.8350, "lon": 10.0790},
    {"id": "b29-east-07", "name": "B29", "lat": 48.8390, "lon": 10.0900},
    {"id": "b29-east-08", "name": "B29", "lat": 48.8420, "lon": 10.1010},
    {"id": "b29-east-09", "name": "B29", "lat": 48.8450, "lon": 10.1120},
    {"id": "b29-east-10", "name": "B29", "lat": 48.8480, "lon": 10.1230},
    {"id": "b29-east-11", "name": "B29", "lat": 48.8500, "lon": 10.1350},
    {"id": "b29-east-12", "name": "B29", "lat": 48.8520, "lon": 10.1480},
    # B19 (north-south): ~8 points from Aalen center north toward Oberkochen
    {"id": "b19-north-01", "name": "B19", "lat": 48.8380, "lon": 10.0930},
    {"id": "b19-north-02", "name": "B19", "lat": 48.8440, "lon": 10.0960},
    {"id": "b19-north-03", "name": "B19", "lat": 48.8510, "lon": 10.0990},
    {"id": "b19-north-04", "name": "B19", "lat": 48.8580, "lon": 10.1020},
    {"id": "b19-north-05", "name": "B19", "lat": 48.8650, "lon": 10.1050},
    {"id": "b19-north-06", "name": "B19", "lat": 48.8720, "lon": 10.1080},
    {"id": "b19-north-07", "name": "B19", "lat": 48.8790, "lon": 10.1100},
    {"id": "b19-north-08", "name": "B19", "lat": 48.8860, "lon": 10.1120},
    # Friedrichstr.: ~5 points through city center
    {"id": "friedrichstr-01", "name": "Friedrichstr.", "lat": 48.8340, "lon": 10.0870},
    {"id": "friedrichstr-02", "name": "Friedrichstr.", "lat": 48.8360, "lon": 10.0900},
    {"id": "friedrichstr-03", "name": "Friedrichstr.", "lat": 48.8380, "lon": 10.0920},
    {"id": "friedrichstr-04", "name": "Friedrichstr.", "lat": 48.8400, "lon": 10.0940},
    {"id": "friedrichstr-05", "name": "Friedrichstr.", "lat": 48.8420, "lon": 10.0960},
    # Gmunder Str.: ~5 points heading southwest
    {"id": "gmunderstr-01", "name": "Gmunder Str.", "lat": 48.8350, "lon": 10.0850},
    {"id": "gmunderstr-02", "name": "Gmunder Str.", "lat": 48.8320, "lon": 10.0810},
    {"id": "gmunderstr-03", "name": "Gmunder Str.", "lat": 48.8290, "lon": 10.0770},
    {"id": "gmunderstr-04", "name": "Gmunder Str.", "lat": 48.8260, "lon": 10.0730},
    {"id": "gmunderstr-05", "name": "Gmunder Str.", "lat": 48.8230, "lon": 10.0690},
    # Other arterials: Stuttgarter Str., Ulmer Str., Bahnhofstr.
    {"id": "stuttgarterstr-01", "name": "Stuttgarter Str.", "lat": 48.8310, "lon": 10.0830},
    {"id": "stuttgarterstr-02", "name": "Stuttgarter Str.", "lat": 48.8280, "lon": 10.0780},
    {"id": "ulmerstr-01", "name": "Ulmer Str.", "lat": 48.8400, "lon": 10.1000},
    {"id": "ulmerstr-02", "name": "Ulmer Str.", "lat": 48.8430, "lon": 10.1050},
    {"id": "bahnhofstr-01", "name": "Bahnhofstr.", "lat": 48.8370, "lon": 10.0890},
]


def _congestion_level(ratio: float) -> str:
    """Map congestion ratio to level string.

    Args:
        ratio: currentSpeed / freeFlowSpeed (0.0 to 1.0+)

    Returns:
        'free' if >= 0.75, 'moderate' if 0.50-0.75, 'congested' if < 0.50
    """
    if ratio >= 0.75:
        return "free"
    elif ratio >= 0.50:
        return "moderate"
    else:
        return "congested"


class TomTomConnector(BaseConnector):
    """Fetches real-time traffic flow data from TomTom for Aalen road segments.

    Config keys (from ConnectorConfig.config dict):
        api_key: TomTom API key (required).
        attribution: Attribution string (optional).
    """

    # Class-level last run time for adaptive polling skip logic
    _last_run_time: float = 0.0

    def __init__(self, config: ConnectorConfig, town: Town) -> None:
        super().__init__(config, town)
        # Maps segment_id -> features table UUID
        self._feature_ids: dict[str, str] = {}

    def _is_rush_hour(self) -> bool:
        """Check if current time in Europe/Berlin is during rush hours.

        Rush hours: 06:00-08:59 or 16:00-18:59.
        """
        now = _now_berlin()
        hour = now.hour
        return (6 <= hour <= 8) or (16 <= hour <= 18)

    def _get_poll_interval(self) -> int:
        """Return the effective poll interval in seconds.

        600s (10min) during rush hours, 1800s (30min) off-peak.
        """
        if self._is_rush_hour():
            return 600
        return 1800

    async def fetch(self) -> list[tuple[dict, dict]]:
        """Fetch flow segment data from TomTom for each sample point.

        Returns:
            List of (segment_def, api_response_dict) tuples.
            Segments with API errors are skipped (logged as warning).
        """
        api_key = self.config.config["api_key"]
        results: list[tuple[dict, dict]] = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            for segment in AALEN_ROAD_SEGMENTS:
                url = (
                    f"{TOMTOM_FLOW_URL}"
                    f"?point={segment['lat']},{segment['lon']}"
                    f"&key={api_key}&unit=KMPH"
                )
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    data = response.json()
                    results.append((segment, data))
                except Exception as exc:
                    logger.warning(
                        "TomTom API error for segment %s: %s",
                        segment["id"],
                        exc,
                    )
                    continue

        return results

    def normalize(self, raw: Any) -> list[Observation]:
        """Transform TomTom API responses into Observations.

        Args:
            raw: List of (segment_def, api_response_dict) tuples from fetch().

        Returns:
            List of Observation objects with domain='traffic'.
        """
        observations: list[Observation] = []

        for segment_def, response_data in raw:
            flow_data = response_data.get("flowSegmentData", {})
            current_speed = flow_data.get("currentSpeed", 0)
            freeflow_speed = flow_data.get("freeFlowSpeed", 0)

            # Guard against division by zero
            if freeflow_speed > 0:
                congestion_ratio = current_speed / freeflow_speed
            else:
                congestion_ratio = 1.0

            level = _congestion_level(congestion_ratio)

            feature_id = self._feature_ids.get(segment_def["id"], "")

            observations.append(
                Observation(
                    feature_id=feature_id,
                    domain="traffic",
                    values={
                        "vehicle_count_total": None,
                        "vehicle_count_hgv": None,
                        "speed_avg_kmh": current_speed,
                        "congestion_level": level,
                    },
                    source_id=f"tomtom:{segment_def['id']}",
                )
            )

        return observations

    async def run(self) -> None:
        """Full pipeline: fetch, upsert features, normalize, persist, update staleness.

        Overrides BaseConnector.run() to:
        1. Check adaptive polling — skip off-peak if not enough time elapsed
        2. Fetch flow data from TomTom API
        3. Upsert each road segment as a spatial feature with LineString geometry
        4. Normalize into Observations
        5. Persist to traffic_readings
        6. Update staleness timestamp
        """
        # Adaptive polling: skip off-peak runs if less than 1800s since last run
        now_epoch = time.time()
        if not self._is_rush_hour():
            elapsed = now_epoch - TomTomConnector._last_run_time
            if TomTomConnector._last_run_time > 0 and elapsed < 1800:
                logger.debug(
                    "TomTom off-peak skip: only %ds since last run (need 1800s)",
                    int(elapsed),
                )
                return

        attribution = self.config.config.get(
            "attribution", "TomTom Flow API"
        )

        # Step 1: fetch
        raw = await self.fetch()
        if not raw:
            logger.warning("TomTom: no segment data returned")
            return

        # Step 2: upsert features with LineString geometry
        for segment_def, response_data in raw:
            flow_data = response_data.get("flowSegmentData", {})
            coords = flow_data.get("coordinates", {}).get("coordinate", [])
            current_speed = flow_data.get("currentSpeed", 0)
            freeflow_speed = flow_data.get("freeFlowSpeed", 0)
            confidence = flow_data.get("confidence", 0)

            if freeflow_speed > 0:
                congestion_ratio = current_speed / freeflow_speed
            else:
                congestion_ratio = 1.0

            # Build WKT LINESTRING from coordinates
            if len(coords) >= 2:
                coord_pairs = [
                    f"{c['longitude']} {c['latitude']}" for c in coords
                ]
                geometry_wkt = f"LINESTRING({', '.join(coord_pairs)})"
            else:
                # Fallback to point if not enough coordinates
                geometry_wkt = f"POINT({segment_def['lon']} {segment_def['lat']})"

            feature_id = await self.upsert_feature(
                source_id=f"tomtom:{segment_def['id']}",
                domain="traffic",
                geometry_wkt=geometry_wkt,
                properties={
                    "road_name": segment_def["name"],
                    "segment_id": segment_def["id"],
                    "data_source": "TomTom",
                    "freeflow_kmh": freeflow_speed,
                    "congestion_ratio": round(congestion_ratio, 3),
                    "confidence": confidence,
                    "attribution": attribution,
                },
            )
            self._feature_ids[segment_def["id"]] = feature_id

        # Step 3-5: normalize -> persist -> update staleness
        observations = self.normalize(raw)
        await self.persist(observations)
        await self._update_staleness()

        # Record successful run time for adaptive polling
        TomTomConnector._last_run_time = time.time()
