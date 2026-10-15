"""Configuración de pytest para la suite PLUMA GPS.

Aísla la base de datos entre tests cuando se ejecuta contra PostgreSQL
(el motor persistentes). En SQLite cada test usa su propio archivo temporal,
por lo que no se requiere limpieza adicional.
"""
import pytest

from tests.db_utils import reset_database


@pytest.fixture(autouse=True)
def _aislar_postgres():
    from conectar import is_postgres
    if is_postgres():
        from conectar import crear_conexion
        conn = crear_conexion()
        reset_database(conn)
        conn.close()
    yield
