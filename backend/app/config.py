"""Town configuration models and loader.

Each town is described by a YAML file in the `towns/` directory.
Loading a town produces a validated `Town` object — no code changes
required when switching between towns.

Usage:
    from app.config import load_town
    town = load_town("aalen")       # reads towns/aalen.yaml
    town = load_town("example")     # reads towns/example.yaml
"""
from pathlib import Path
from pydantic import BaseModel, field_validator
import yaml


class ConnectorConfig(BaseModel):
    """Configuration for a single data connector within a town."""
    connector_class: str
    poll_interval_seconds: int = 300
    enabled: bool = True
    config: dict = {}


class TownBbox(BaseModel):
    """Bounding box in WGS84 (EPSG:4326) coordinates."""
    lon_min: float
    lat_min: float
    lon_max: float
    lat_max: float


class Town(BaseModel):
    """Validated town configuration.

    The `id` field is the canonical town identifier used throughout the
    database and API. It must be a lowercase alphanumeric slug (hyphens
    and underscores allowed).
    """
    id: str
    display_name: str
    country: str = "DE"
    timezone: str = "Europe/Berlin"
    bbox: TownBbox
    connectors: list[ConnectorConfig] = []

    @field_validator("id")
    @classmethod
    def id_must_be_slug(cls, v: str) -> str:
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                f"Town id must be alphanumeric slug (got '{v}'). "
                "Use hyphens or underscores to separate words."
            )
        return v.lower()


def load_town(town_id: str, towns_dir: Path = Path("towns")) -> Town:
    """Load and validate a town config from YAML.

    Args:
        town_id: The town slug (e.g. "aalen"). Looks for {towns_dir}/{town_id}.yaml
        towns_dir: Directory containing town YAML files. Defaults to ./towns/

    Returns:
        Validated Town object.

    Raises:
        FileNotFoundError: If the YAML file does not exist.
        pydantic.ValidationError: If the YAML content fails validation.
    """
    yaml_path = towns_dir / f"{town_id}.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(
            f"Town config not found: {yaml_path}. "
            f"Available towns: {[p.stem for p in towns_dir.glob('*.yaml')]}"
        )
    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    return Town.model_validate(raw)
