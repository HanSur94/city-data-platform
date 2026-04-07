"""Add semantic_id column to features, create feature_observations VIEW.

Revision ID: 005
"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- semantic_id column (nullable) ---
    op.add_column(
        "features",
        sa.Column("semantic_id", sa.Text, nullable=True),
    )
    op.create_index(
        "idx_features_semantic_id",
        "features",
        ["semantic_id"],
        postgresql_where=sa.text("semantic_id IS NOT NULL"),
    )

    # --- Cross-domain observations VIEW ---
    op.execute("""
        CREATE OR REPLACE VIEW feature_observations AS
        SELECT feature_id, 'air_quality' AS domain, time AS timestamp,
               json_build_object('pm25', pm25, 'pm10', pm10, 'no2', no2, 'o3', o3, 'aqi', aqi) AS values
        FROM air_quality_readings
        UNION ALL
        SELECT feature_id, 'traffic' AS domain, time,
               json_build_object('vehicle_count_total', vehicle_count_total, 'speed_avg_kmh', speed_avg_kmh, 'congestion_level', congestion_level) AS values
        FROM traffic_readings
        UNION ALL
        SELECT feature_id, 'water' AS domain, time,
               json_build_object('level_cm', level_cm, 'flow_m3s', flow_m3s) AS values
        FROM water_readings
        UNION ALL
        SELECT feature_id, 'energy' AS domain, time,
               json_build_object('value_kw', value_kw, 'source_type', source_type::text) AS values
        FROM energy_readings
        UNION ALL
        SELECT feature_id, 'weather' AS domain, time,
               json_build_object('temperature', temperature, 'condition', condition, 'wind_speed', wind_speed) AS values
        FROM weather_readings
        UNION ALL
        SELECT feature_id, 'transit' AS domain, time,
               json_build_object('trip_id', trip_id, 'route_id', route_id, 'delay_seconds', delay_seconds) AS values
        FROM transit_positions
        UNION ALL
        SELECT feature_id, 'demographics' AS domain, time,
               values::json AS values
        FROM demographics_readings
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS feature_observations")
    op.drop_index("idx_features_semantic_id", table_name="features")
    op.drop_column("features", "semantic_id")
