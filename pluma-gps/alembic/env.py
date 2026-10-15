"""Alembic environment for PLUMA GPS."""
import os
import sys
from logging.config import fileConfig

from sqlalchemy import URL, create_engine, pool
from alembic import context

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def get_url() -> URL:
    """URL segura construida desde env vars (driver psycopg2 explícito)."""
    return URL.create(
        drivername="postgresql+psycopg2",
        username=os.environ.get("DB_USER", "pluma"),
        password=os.environ.get("DB_PASSWORD", "pluma"),
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", "5432")),
        database=os.environ.get("DB_NAME", "pluma_gps"),
    )


config.set_main_option("sqlalchemy.url", get_url().render_as_string(hide_password=False))

target_metadata = None


def run_migrations_offline():
    context.configure(
        url=get_url().render_as_string(hide_password=False),
        literal_binds=True,
        dialect_name="postgresql",
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = create_engine(get_url(), poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
