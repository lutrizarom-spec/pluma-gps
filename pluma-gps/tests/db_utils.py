"""Utilidades de test agnósticas al motor (SQLite / PostgreSQL)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from conectar import is_postgres  # noqa: E402
from dao.dao import Dao  # noqa: E402

TABLES = ["alerts", "cut_engine_commands", "vehicle_assignments",
          "telemetry_logs", "geofences", "gps_devices", "vehicles", "users"]


def list_tables(conn) -> list:
    """Lista las tablas de usuario del esquema, en cualquier motor."""
    cur = conn.cursor()
    if is_postgres():
        cur.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    else:
        cur.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    return [r[0] for r in cur.fetchall()]


def reset_database(conn):
    """Deja la BD limpia y con todas las tablas creadas.

    SQLite ya usa un archivo temporal por test, así que no hace nada.
    PostgreSQL es persistente: elimina las tablas y las recrea.
    """
    if not is_postgres():
        return
    cur = conn.cursor()
    cur.execute(
        "DROP TABLE IF EXISTS " + ", ".join(TABLES) + " CASCADE")
    conn.commit()
    Dao(conn).crear_todas_las_tablas()
