"""Prueba de integración opcional contra SQL Server real.

Solo se ejecuta cuando existe backend/.env con credenciales SQL válidas y la
variable RUN_DB_TESTS=1. No crea tablas ni procedimientos almacenados.
"""

import os

import pytest

from backend.core.config import get_settings

settings = get_settings()

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_DB_TESTS") != "1" or not settings.database_configured,
        reason="Requiere backend/.env con credenciales SQL y RUN_DB_TESTS=1",
    ),
]


def test_conexion_real_con_sql_server() -> None:
    from backend.core.database import Database

    info = Database(settings).test_connection()

    assert info["connected"] is True
    assert info["database"]


def test_transaccion_real_commit_y_rollback() -> None:
    from backend.core.database import Database

    db = Database(settings)

    with db.transaction() as cursor:
        cursor.execute("SELECT 1")

    with pytest.raises(RuntimeError, match="rollback simulado"):
        with db.transaction() as cursor:
            cursor.execute("SELECT 1")
            raise RuntimeError("rollback simulado")
