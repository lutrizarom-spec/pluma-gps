import os
import sqlite3

DB_NAME = "pluma_gps.db"


def _get_postgres_dsn() -> str:
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    name = os.environ.get("DB_NAME", "pluma_gps")
    user = os.environ.get("DB_USER", "pluma")
    password = os.environ.get("DB_PASSWORD", "pluma")
    return f"host={host} port={port} dbname={name} user={user} password={password}"


def is_postgres() -> bool:
    return os.environ.get("DB_ENGINE", "sqlite").lower() == "postgres"


def crear_conexion(db_path: str = None):
    """Factory de conexión: PostgreSQL si DB_ENGINE=postgres, SQLite por defecto."""
    if is_postgres():
        import psycopg2
        conn = psycopg2.connect(_get_postgres_dsn())
        conn.set_client_encoding("UTF8")
        return conn
    path = db_path or os.path.join(os.path.dirname(__file__), DB_NAME)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
