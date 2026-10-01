"""Add alerts table

Revision ID: 0002_alerts
Revises: 0001_initial
Create Date: 2026-10-01
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_alerts"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "alerts",
        sa.Column("alert_id", sa.String(36), primary_key=True),
        sa.Column("device_id", sa.String(36), sa.ForeignKey("gps_devices.device_id"), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
    )
    op.create_index("ix_alerts_device_status", "alerts", ["device_id", "status"])


def downgrade():
    op.drop_index("ix_alerts_device_status", table_name="alerts")
    op.drop_table("alerts")
