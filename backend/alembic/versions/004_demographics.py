"""Demographics readings hypertable for Phase 10.

Revision ID: 004
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- demographics_readings hypertable ---
    # Stores slow-moving demographic data (daily refresh).
    # values JSONB holds flexible indicator sets per connector:
    #   WegweiserKommune: population, age_under_18_pct, age_over_65_pct, etc.
    #   StatistikBW:      population, population_male, population_female
    #   Zensus:           population, households, wms_url
    #   Bundesagentur:    unemployment_rate, total_employed, open_positions
    op.create_table(
        "demographics_readings",
        sa.Column("time", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "feature_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("features.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "values",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Flexible JSONB store for demographic indicator values",
        ),
    )
    op.execute(
        "SELECT create_hypertable('demographics_readings', by_range('time'), if_not_exists => TRUE)"
    )
    op.execute(
        "SELECT add_retention_policy('demographics_readings', "
        "drop_after => INTERVAL '10 years', if_not_exists => true)"
    )


def downgrade() -> None:
    op.drop_table("demographics_readings")
