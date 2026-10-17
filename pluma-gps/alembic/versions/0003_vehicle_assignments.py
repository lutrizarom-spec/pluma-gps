"""Add vehicle_assignments table

Revision ID: 0003_vehicle_assignments
Revises: 0002_alerts
Create Date: 2026-10-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_vehicle_assignments"
down_revision = "0002_alerts"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "vehicle_assignments",
        sa.Column("assignment_id", sa.String(36), primary_key=True),
        sa.Column("vehicle_id", sa.String(36),
                  sa.ForeignKey("vehicles.vehicle_id"), nullable=False),
        sa.Column("user_id", sa.String(36),
                  sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("start_time", sa.String(40), nullable=False),
        sa.Column("end_time", sa.String(40)),
        sa.Column("is_replacement", sa.Integer, server_default="0", nullable=False),
        sa.Column("authorized_by", sa.String(36),
                  sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
    )
    op.create_index("ix_assignments_vehicle_start", "vehicle_assignments",
                    ["vehicle_id", "start_time"])


def downgrade():
    op.drop_index("ix_assignments_vehicle_start", table_name="vehicle_assignments")
    op.drop_table("vehicle_assignments")
