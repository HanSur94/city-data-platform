"""Traffic readings hypertable for Phase 7.

Revision ID: 003
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- traffic_readings hypertable ---
    op.create_table(
        "traffic_readings",
        sa.Column("time", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "feature_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("features.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("vehicle_count_total", sa.Integer, nullable=True,
                  comment="Total vehicles per hour (Kfz/h)"),
        sa.Column("vehicle_count_hgv", sa.Integer, nullable=True,
                  comment="Heavy goods vehicles per hour (SV/h)"),
        sa.Column("speed_avg_kmh", sa.Float, nullable=True,
                  comment="Average speed in km/h"),
        sa.Column("congestion_level", sa.String, nullable=True,
                  comment="'free' | 'moderate' | 'congested'"),
    )
    op.execute(
        "SELECT create_hypertable('traffic_readings', by_range('time'), if_not_exists => TRUE)"
    )
    op.execute(
        "SELECT add_retention_policy('traffic_readings', "
        "drop_after => INTERVAL '2 years', if_not_exists => true)"
    )


def downgrade() -> None:
    op.drop_table("traffic_readings")
