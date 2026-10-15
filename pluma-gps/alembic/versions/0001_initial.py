"""Initial schema: users, vehicles, gps_devices, geofences, telemetry_logs, cut_engine_commands

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-01
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("user_id", sa.String(36), primary_key=True),
        sa.Column("rut", sa.String(12), nullable=False, unique=True),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("email", sa.String(150), nullable=False, unique=True),
        sa.Column("subscription_plan", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Integer, server_default="1"),
        sa.Column("password_hash", sa.Text),
    )

    op.create_table(
        "vehicles",
        sa.Column("vehicle_id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("license_plate", sa.String(10), nullable=False),
        sa.Column("brand", sa.String(100)),
        sa.Column("model", sa.String(100)),
        sa.Column("manufacture_year", sa.Integer),
        sa.Column("engine_type", sa.String(50)),
    )

    op.create_table(
        "gps_devices",
        sa.Column("device_id", sa.String(36), primary_key=True),
        sa.Column("vehicle_id", sa.String(36), sa.ForeignKey("vehicles.vehicle_id"), nullable=False, unique=True),
        sa.Column("imei", sa.String(20), nullable=False, unique=True),
        sa.Column("hardware_model", sa.String(100)),
        sa.Column("hardware_level", sa.String(20), nullable=False),
        sa.Column("is_online", sa.Integer, server_default="0"),
    )

    op.create_table(
        "geofences",
        sa.Column("geofence_id", sa.String(36), primary_key=True),
        sa.Column("vehicle_id", sa.String(36), sa.ForeignKey("vehicles.vehicle_id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("area_wkt", sa.Text, nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
    )

    op.create_table(
        "telemetry_logs",
        sa.Column("telemetry_id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("device_id", sa.String(36), sa.ForeignKey("gps_devices.device_id"), nullable=False),
        sa.Column("recorded_at", sa.String(40), nullable=False),
        sa.Column("point_wkt", sa.Text, nullable=False),
        sa.Column("speed_kmh", sa.Float, server_default="0"),
        sa.Column("heading", sa.Float, server_default="0"),
        sa.Column("acc_ignition", sa.Integer, server_default="0"),
        sa.Column("main_battery", sa.Float),
        sa.Column("backup_battery", sa.Float),
        sa.Column("fuel_level", sa.Float),
        sa.Column("odometer_km", sa.Float, server_default="0"),
        sa.Column("dashcam_recording", sa.Integer, server_default="0"),
    )
    op.create_index("ix_telemetry_device_recorded", "telemetry_logs",
                    ["device_id", sa.text("recorded_at DESC")])

    op.create_table(
        "cut_engine_commands",
        sa.Column("command_id", sa.String(36), primary_key=True),
        sa.Column("device_id", sa.String(36), sa.ForeignKey("gps_devices.device_id"), nullable=False),
        sa.Column("requested_at", sa.String(40), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("doors_locked", sa.Integer, server_default="0"),
        sa.Column("windows_closed", sa.Integer, server_default="0"),
        sa.Column("executed_at", sa.String(40)),
        sa.Column("speed_at_execution", sa.Float),
    )
    op.create_index("ix_commands_device_status", "cut_engine_commands",
                    ["device_id", "status"])


def downgrade():
    op.drop_index("ix_commands_device_status", table_name="cut_engine_commands")
    op.drop_table("cut_engine_commands")
    op.drop_index("ix_telemetry_device_recorded", table_name="telemetry_logs")
    op.drop_table("telemetry_logs")
    op.drop_table("geofences")
    op.drop_table("gps_devices")
    op.drop_table("vehicles")
    op.drop_table("users")
