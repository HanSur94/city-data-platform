"""One-shot BKG VG250 administrative boundary import.

Downloads the VG250 GeoPackage from BKG open data, filters to the
specified municipality by AGS (Amtlicher Gemeindeschlüssel), reprojects
to WGS84 (EPSG:4326), and inserts into the PostGIS `features` table.

Usage:
    # Default: load Aalen (AGS=08136088)
    cd backend
    DATABASE_URL="postgresql://citydata:citydata@localhost:5432/citydata" \\
        uv run python scripts/load_vg250.py

    # Custom town
    DATABASE_URL="..." uv run python scripts/load_vg250.py ulm 08421000

Requires:
    - Database running with migrations applied (alembic upgrade head)
    - Town row inserted in towns table (or will fail FK constraint)
    - geopandas, geoalchemy2, httpx installed (part of uv dependencies)
"""
import os
import sys
import zipfile
from pathlib import Path

import httpx
import geopandas as gpd
from sqlalchemy import create_engine, text
from sqlalchemy.dialects.postgresql import JSONB

# GeoPackage format: preferred over Shapefile (fewer encoding issues)
VG250_GPKG_URL = (
    "https://daten.gdz.bkg.bund.de/produkte/vg/vg250_ebenen_0101/aktuell/"
    "vg250_01-01.utm32s.gpkg.ebenen.zip"
)

TMP_DIR = Path("/tmp/vg250")


def _download_vg250() -> Path:
    """Download VG250 GeoPackage zip, extract .gpkg file. Cached in /tmp/vg250."""
    TMP_DIR.mkdir(exist_ok=True)
    zip_path = TMP_DIR / "vg250.zip"
    gpkg_path = TMP_DIR / "vg250.gpkg"

    if not zip_path.exists():
        print(f"Downloading VG250 GeoPackage from BKG (~200MB)...")
        with httpx.Client(timeout=300) as client:
            r = client.get(VG250_GPKG_URL, follow_redirects=True)
            r.raise_for_status()
            zip_path.write_bytes(r.content)
        print(f"Downloaded to {zip_path}")

    if not gpkg_path.exists():
        print("Extracting GeoPackage...")
        with zipfile.ZipFile(zip_path) as zf:
            for name in zf.namelist():
                if name.endswith(".gpkg"):
                    gpkg_path.write_bytes(zf.read(name))
                    print(f"Extracted {name} -> {gpkg_path}")
                    break
            else:
                raise ValueError(f"No .gpkg file found in {zip_path}")

    return gpkg_path


def load_town_boundary(town_id: str, ags: str, db_url: str) -> None:
    """Download VG250, filter to AGS, insert into features table.

    Args:
        town_id: Town identifier (must match existing row in towns table).
        ags: 8-digit Amtlicher Gemeindeschlüssel (e.g. "08136088" for Aalen).
             MUST be a string — leading zero is significant.
        db_url: PostgreSQL connection URL (sync, no +asyncpg).
    """
    gpkg_path = _download_vg250()

    # Load VG250_GEM layer (Gemeinden = municipalities)
    print(f"Loading VG250_GEM layer, filtering AGS='{ags}'...")
    gdf = gpd.read_file(gpkg_path, layer="VG250_GEM")

    # AGS is a STRING in VG250 — must match as string, not integer
    town_gdf = gdf[gdf["AGS"] == ags].copy()

    if town_gdf.empty:
        available = gdf[gdf["AGS"].str.startswith(ags[:5])]["GEN"].tolist()[:5]
        raise ValueError(
            f"No municipality found for AGS='{ags}'. "
            f"Nearby municipalities: {available}"
        )

    print(f"Found {len(town_gdf)} feature(s) for AGS={ags}: {town_gdf['GEN'].tolist()}")

    # Reproject from UTM32s (EPSG:25832) to WGS84 (EPSG:4326)
    # MapLibre and PostGIS default to WGS84 — never store in national CRS
    print(f"Reprojecting from {town_gdf.crs} to EPSG:4326...")
    town_gdf = town_gdf.to_crs(epsg=4326)

    # Prepare columns for the features table
    import uuid
    town_gdf["id"] = [str(uuid.uuid4()) for _ in range(len(town_gdf))]
    town_gdf["town_id"] = town_id
    town_gdf["domain"] = "administrative"
    town_gdf["source_id"] = "bkg_vg250"
    town_gdf["properties"] = town_gdf.apply(
        lambda r: {"gen": r["GEN"], "ags": r["AGS"], "bez": r.get("BEZ", "")},
        axis=1,
    )

    insert_gdf = town_gdf[["id", "town_id", "domain", "source_id", "geometry", "properties"]]

    # Use SYNC engine — geopandas.to_postgis() does NOT support async engines
    sync_url = db_url.replace("+asyncpg", "")
    engine = create_engine(sync_url)

    # Ensure the town row exists before inserting features (FK constraint)
    with engine.connect() as conn:
        existing = conn.execute(
            text("SELECT id FROM towns WHERE id = :town_id"),
            {"town_id": town_id},
        ).fetchone()
        if existing is None:
            print(f"Inserting town row for '{town_id}'...")
            conn.execute(
                text(
                    "INSERT INTO towns (id, display_name, country) "
                    "VALUES (:id, :display_name, :country) "
                    "ON CONFLICT (id) DO NOTHING"
                ),
                {"id": town_id, "display_name": town_id.capitalize(), "country": "DE"},
            )
            conn.commit()

    print(f"Writing {len(insert_gdf)} boundary feature(s) to PostGIS features table...")
    insert_gdf.to_postgis(
        name="features",
        con=engine,
        if_exists="append",
        index=False,
        dtype={"properties": JSONB},
    )
    engine.dispose()
    print(f"Done. Loaded {len(insert_gdf)} boundary feature(s) for town_id='{town_id}'.")


if __name__ == "__main__":
    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://citydata:citydata@localhost:5432/citydata",
    )
    town_id = sys.argv[1] if len(sys.argv) > 1 else "aalen"
    ags = sys.argv[2] if len(sys.argv) > 2 else "08136088"

    print(f"Loading boundary for town='{town_id}' AGS='{ags}'")
    load_town_boundary(town_id=town_id, ags=ags, db_url=db_url)
