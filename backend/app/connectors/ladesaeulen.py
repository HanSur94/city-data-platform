"""LadesaeulenConnector: fetches EV charging station data from BNetzA.

Implements INFR-02: downloads the Ladesäulenregister CSV from the
Bundesnetzagentur (BNetzA), parses German comma-decimal coordinates,
filters to Ostalbkreis (Aalen's district), and upserts each charging
station as an infrastructure spatial feature.

CSV format:
- Delimiter: semicolon (;)
- Encoding: UTF-8
- Decimal separator: comma (,) for Breitengrad, Laengengrad, power values

License: Bundesnetzagentur, CC BY 4.0
"""
from __future__ import annotations

import csv
import io
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from app.connectors.base import BaseConnector, Observation
from app.config import ConnectorConfig, Town

logger = logging.getLogger(__name__)

# 24 hour cache TTL in seconds
_CACHE_TTL_SECONDS = 86400

# Default BNetzA CSV download URL (update date as new versions are released)
_DEFAULT_CSV_URL = (
    "https://data.bundesnetzagentur.de/Bundesnetzagentur/DE/Fachthemen/"
    "ElektrizitaetundGas/E-Mobilitaet/Ladesaeulenregister_BNetzA_2026-03-25.csv"
)

# Default local cache path
_DEFAULT_CACHE_PATH = Path("/tmp/ladesaeulenregister.csv")


def _parse_german_float(val: str) -> float | None:
    """Parse a German-format decimal string to float.

    German CSVs use comma as the decimal separator (e.g. '48,8357').
    This helper replaces comma with dot and converts to float.

    Args:
        val: String value from CSV (may contain comma decimal, dot decimal, or be empty).

    Returns:
        float value, or None if val is empty or not parseable.
    """
    if not val or not val.strip():
        return None
    try:
        return float(val.strip().replace(",", "."))
    except ValueError:
        return None


class LadesaeulenConnector(BaseConnector):
    """Downloads and parses BNetzA EV charging station registry CSV.

    Filters to Ostalbkreis (configurable via kreis_filter config key) and
    upserts each valid station as an infrastructure/ev_charging feature.

    No time-series data is produced — this is a features-only connector.
    The BNetzA CSV is cached for 24 hours to avoid repeated large downloads.

    Config keys (from ConnectorConfig.config dict):
        kreis_filter: str — Filter value for 'Kreis/kreisfreie Stadt' column.
                            Defaults to "Ostalbkreis".
        attribution: str — Attribution string for data provenance.
    """

    def _get_cache_path(self) -> Path:
        """Return the local cache file path for the BNetzA CSV."""
        return _DEFAULT_CACHE_PATH

    def _is_cache_fresh(self) -> bool:
        """Check if cached CSV exists and is less than 24h old."""
        cache_path = self._get_cache_path()
        if not cache_path.exists():
            return False
        mtime = cache_path.stat().st_mtime
        age_seconds = datetime.now(timezone.utc).timestamp() - mtime
        return age_seconds < _CACHE_TTL_SECONDS

    async def fetch(self) -> bytes:
        """Download BNetzA CSV if stale, otherwise read from cache.

        Download strategy:
        1. If cached file is fresh (< 24h), read from cache.
        2. Otherwise, download from the known BNetzA URL.
        3. Cache the downloaded content to disk.

        Returns:
            CSV content as bytes (UTF-8).
        """
        cache_path = self._get_cache_path()

        if self._is_cache_fresh():
            logger.info("LadesaeulenConnector: cache fresh — reading from %s", cache_path)
            return cache_path.read_bytes()

        logger.info("LadesaeulenConnector: cache stale or missing — downloading BNetzA CSV")
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(_DEFAULT_CSV_URL)
            response.raise_for_status()
            content = response.content

        # Cache to disk
        try:
            cache_path.write_bytes(content)
        except OSError as exc:
            logger.warning("Could not write BNetzA CSV cache to %s: %s", cache_path, exc)

        return content

    def normalize(self, raw: Any) -> list[Observation]:
        """Return empty list — LadesaeulenConnector is features-only.

        Args:
            raw: Unused.

        Returns:
            Empty list.
        """
        return []

    async def run(self) -> None:
        """Full pipeline: download CSV, parse rows, filter by Kreis, upsert features.

        Overrides BaseConnector.run() to:
        1. Fetch (download if stale) the BNetzA EV charging CSV
        2. Parse with csv.DictReader (semicolon delimiter)
        3. Filter rows by 'Kreis/kreisfreie Stadt' == kreis_filter config
        4. For each valid row with coordinates, upsert a spatial feature
        5. Update staleness timestamp

        Rows missing coordinates or failing coordinate parsing are skipped.
        """
        kreis_filter = self.config.config.get("kreis_filter", "Ostalbkreis")

        raw = await self.fetch()

        # Parse CSV from bytes — BNetzA uses UTF-8 with BOM sometimes
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("latin-1")

        # BNetzA CSV has ~10 metadata lines before the actual column headers.
        # Skip lines until we find the real header row (contains "Ladeeinrichtungs-ID").
        lines = text.split("\n")
        header_idx = 0
        for i, line in enumerate(lines):
            if "Ladeeinrichtungs-ID" in line or (
                "Betreiber" in line and "Postleitzahl" in line
            ):
                header_idx = i
                break
        data_text = "\n".join(lines[header_idx:])

        reader = csv.DictReader(io.StringIO(data_text), delimiter=";")
        upserted = 0
        skipped_kreis = 0
        skipped_coords = 0

        for idx, row in enumerate(reader):
            # Filter by Kreis — BNetzA CSV uses "Landkreis Ostalbkreis" format;
            # use substring match to handle variations (e.g. "Ostalbkreis" vs
            # "Landkreis Ostalbkreis").
            kreis_cell = row.get("Kreis/kreisfreie Stadt", "").strip()
            if kreis_filter not in kreis_cell:
                skipped_kreis += 1
                continue

            # Parse coordinates — BNetzA CSV uses "Längengrad" (with umlaut),
            # not "Laengengrad". Also supports the umlaut-less fallback.
            lat = _parse_german_float(
                row.get("Breitengrad", "") or row.get("Breitengrad", "")
            )
            lon = _parse_german_float(
                row.get("Längengrad", "") or row.get("Laengengrad", "")
            )
            if lat is None or lon is None:
                skipped_coords += 1
                continue

            # Aggregate plug types (Steckertypen1..6), exclude empty strings
            plug_types = [
                t.strip()
                for key in (
                    "Steckertypen1", "Steckertypen2", "Steckertypen3",
                    "Steckertypen4", "Steckertypen5", "Steckertypen6",
                )
                if (t := row.get(key, "").strip())
            ]

            # Aggregate power values — BNetzA uses "Nennleistung Stecker1..6" columns,
            # not "P1..P4 [kW]". Take max of non-None values.
            power_values = []
            for key in (
                "Nennleistung Stecker1", "Nennleistung Stecker2",
                "Nennleistung Stecker3", "Nennleistung Stecker4",
                "Nennleistung Stecker5", "Nennleistung Stecker6",
            ):
                p = _parse_german_float(row.get(key, ""))
                if p is not None:
                    power_values.append(p)
            max_power_kw = max(power_values) if power_values else None

            # Build address string — BNetzA uses "Straße" (with ß), not "Strasse"
            strasse = (row.get("Straße", "") or row.get("Strasse", "")).strip()
            hausnummer = row.get("Hausnummer", "").strip()
            plz = row.get("Postleitzahl", "").strip()
            ort = row.get("Ort", "").strip()
            address = f"{strasse} {hausnummer}, {plz} {ort}".strip(", ")

            # source_id: combine PLZ + Strasse + Hausnummer for deduplication
            source_id = (
                f"bnetza:{plz}:{strasse}:{hausnummer}"
                if (plz or strasse or hausnummer)
                else f"bnetza:idx:{idx}"
            )

            # Num charging points
            num_charging_points_raw = row.get("Anzahl Ladepunkte", "")
            try:
                num_charging_points = int(num_charging_points_raw.strip())
            except (ValueError, AttributeError):
                num_charging_points = None

            properties = {
                "category": "ev_charging",
                "operator": row.get("Betreiber", "").strip(),
                "address": address,
                "plug_types": plug_types,
                "max_power_kw": max_power_kw,
                "num_charging_points": num_charging_points,
                "charging_type": row.get("Art der Ladeeinrichtung", "").strip(),
                "attribution": self.config.config.get("attribution", "Bundesnetzagentur, CC BY 4.0"),
            }

            try:
                await self.upsert_feature(
                    source_id=source_id,
                    domain="infrastructure",
                    geometry_wkt=f"POINT({lon} {lat})",
                    properties=properties,
                )
                upserted += 1
            except Exception as exc:
                logger.warning(
                    "LadesaeulenConnector: failed to upsert feature %s: %s", source_id, exc
                )

        logger.info(
            "LadesaeulenConnector: upserted=%d, skipped_kreis=%d, skipped_coords=%d",
            upserted,
            skipped_kreis,
            skipped_coords,
        )

        await self._update_staleness()
