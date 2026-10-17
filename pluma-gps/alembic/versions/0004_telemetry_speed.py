"""Add speed limit/zone columns to telemetry_logs

Revision ID: 0004_telemetry_speed
Revises: 0003_vehicle_assignments
Create Date: 2026-10-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_telemetry_speed"
down_revision = "0003_vehicle_assignments"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("telemetry_logs", sa.Column("vehicle_id", sa.String(36)))
    op.add_column("telemetry_logs", sa.Column("speed_limit", sa.Float))
    op.add_column("telemetry_logs", sa.Column("zone_type", sa.String(20)))
    op.create_index("ix_telemetry_vehicle_recorded", "telemetry_logs",
                    ["vehicle_id", "recorded_at"])


def downgrade():
    op.drop_index("ix_telemetry_vehicle_recorded", table_name="telemetry_logs")
    op.drop_column("telemetry_logs", "zone_type")
    op.drop_column("telemetry_logs", "speed_limit")
    op.drop_column("telemetry_logs", "vehicle_id")
