"""Initial schema: config tables, spatial features table, domain hypertables.

Revision ID: 001
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import geoalchemy2 as ga

# revision identifiers — do not modify
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # Extensions (must come first — geometry type needs PostGIS)          #
    # ------------------------------------------------------------------ #
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")

    # ------------------------------------------------------------------ #
    # Config tables (standard relational — no hypertable)                 #
    # ------------------------------------------------------------------ #
    op.create_table(
        "towns",
        sa.Column("id", sa.String, primary_key=True),  # e.g. "aalen"
        sa.Column("display_name", sa.String, nullable=False),
        sa.Column("country", sa.String, nullable=False, server_default="DE"),
        sa.Column(
            "bbox",
            postgresql.JSONB,
            nullable=True,
            comment="[lon_min, lat_min, lon_max, lat_max]",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "sources",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column(
            "town_id",
            sa.String,
            sa.ForeignKey("towns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "domain",
            sa.String,
            nullable=False,
            comment="transit, air_quality, water, energy, etc.",
        ),
        sa.Column("connector_class", sa.String, nullable=False),
        sa.Column("config", postgresql.JSONB, nullable=True),
        sa.Column("poll_interval_seconds", sa.Integer, server_default="300"),
        sa.Column("enabled", sa.Boolean, server_default="true"),
    )

    # ------------------------------------------------------------------ #
    # Spatial features table (PostGIS geometry column)                    #
    # ------------------------------------------------------------------ #
    op.create_table(
        "features",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "town_id",
            sa.String,
            sa.ForeignKey("towns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("domain", sa.String, nullable=False),
        sa.Column("source_id", sa.String, nullable=True),
        sa.Column(
            "geometry",
            ga.Geometry("GEOMETRY", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("properties", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_features_town_domain",
        "features",
        ["town_id", "domain"],
    )
    op.create_index(
        "idx_features_geometry",
        "features",
        ["geometry"],
        postgresql_using="gist",
    )

    # ------------------------------------------------------------------ #
    # Domain hypertables                                                  #
    # ------------------------------------------------------------------ #

    # Air quality readings — UBA + Sensor.community
    op.create_table(
        "air_quality_readings",
        sa.Column("time", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "feature_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("features.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("pm25", sa.Float, nullable=True),
        sa.Column("pm10", sa.Float, nullable=True),
        sa.Column("no2", sa.Float, nullable=True),
        sa.Column("o3", sa.Float, nullable=True),
        sa.Column("aqi", sa.Float, nullable=True),
    )
    op.execute(
        "SELECT create_hypertable('air_quality_readings', 'time', "
        "chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE)"
    )
    op.execute(
        "SELECT add_retention_policy('air_quality_readings', "
        "drop_after => INTERVAL '2 years', if_not_exists => TRUE)"
    )

    # Transit vehicle positions — GTFS-RT
    op.create_table(
        "transit_positions",
        sa.Column("time", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "feature_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("features.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("trip_id", sa.String, nullable=True),
        sa.Column("route_id", sa.String, nullable=True),
        sa.Column("delay_seconds", sa.Integer, nullable=True),
        sa.Column(
            "geometry",
            ga.Geometry("POINT", srid=4326, spatial_index=False),
            nullable=True,
        ),
    )
    op.execute(
        "SELECT create_hypertable('transit_positions', 'time', "
        "chunk_time_interval => INTERVAL '1 hour', if_not_exists => TRUE)"
    )
    op.execute(
        "SELECT add_retention_policy('transit_positions', "
        "drop_after => INTERVAL '90 days', if_not_exists => TRUE)"
    )

    # Water level readings — PEGELONLINE + HVZ BW
    op.create_table(
        "water_readings",
        sa.Column("time", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "feature_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("features.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("level_cm", sa.Float, nullable=True),
        sa.Column("flow_m3s", sa.Float, nullable=True),
    )
    op.execute(
        "SELECT create_hypertable('water_readings', 'time', "
        "chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE)"
    )
    op.execute(
        "SELECT add_retention_policy('water_readings', "
        "drop_after => INTERVAL '5 years', if_not_exists => TRUE)"
    )

    # Energy readings — SMARD + MaStR
    op.create_table(
        "energy_readings",
        sa.Column("time", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "feature_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("features.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("value_kw", sa.Float, nullable=True),
        sa.Column(
            "source_type",
            sa.String,
            nullable=True,
            comment="solar, wind, grid, battery",
        ),
    )
    op.execute(
        "SELECT create_hypertable('energy_readings', 'time', "
        "chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE)"
    )
    op.execute(
        "SELECT add_retention_policy('energy_readings', "
        "drop_after => INTERVAL '5 years', if_not_exists => TRUE)"
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    for table in [
        "energy_readings",
        "water_readings",
        "transit_positions",
        "air_quality_readings",
        "features",
        "sources",
        "towns",
    ]:
        op.drop_table(table)
    op.execute("DROP EXTENSION IF EXISTS timescaledb")
    op.execute("DROP EXTENSION IF EXISTS postgis")
