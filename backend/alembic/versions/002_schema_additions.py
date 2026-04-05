"""Schema additions for Phase 2: weather hypertable, features unique constraint, sources staleness.

Revision ID: 002
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import geoalchemy2 as ga

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- weather_readings hypertable ---
    op.create_table(
        "weather_readings",
        sa.Column("time", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "feature_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("features.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("temperature", sa.Float, nullable=True),
        sa.Column("dew_point", sa.Float, nullable=True),
        sa.Column("pressure_msl", sa.Float, nullable=True),
        sa.Column("wind_speed", sa.Float, nullable=True),
        sa.Column("wind_direction", sa.Float, nullable=True),
        sa.Column("cloud_cover", sa.Float, nullable=True),
        sa.Column("condition", sa.String, nullable=True),
        sa.Column("icon", sa.String, nullable=True),
        sa.Column("precipitation_10", sa.Float, nullable=True),
        sa.Column("precipitation_30", sa.Float, nullable=True),
        sa.Column("precipitation_60", sa.Float, nullable=True),
        sa.Column(
            "observation_type",
            sa.String,
            nullable=True,
            comment="'current' or 'forecast' (MOSMIX)",
        ),
    )
    op.execute(
        "SELECT create_hypertable('weather_readings', 'time', "
        "chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE)"
    )
    op.execute(
        "SELECT add_retention_policy('weather_readings', "
        "drop_after => INTERVAL '1 year', if_not_exists => TRUE)"
    )

    # --- features unique constraint ---
    op.create_unique_constraint(
        "uq_features_town_domain_source",
        "features",
        ["town_id", "domain", "source_id"],
    )

    # --- sources staleness columns ---
    op.add_column(
        "sources",
        sa.Column("last_successful_fetch", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "sources",
        sa.Column("validation_error_count", sa.Integer, nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("sources", "validation_error_count")
    op.drop_column("sources", "last_successful_fetch")
    op.drop_constraint("uq_features_town_domain_source", "features")
    op.drop_table("weather_readings")
