"""Etapa 11: repositorio SQL de usuarios con cursores simulados."""

from __future__ import annotations

from contextlib import contextmanager
from uuid import uuid4

import pyodbc
import pytest

from backend.core.exceptions import DatabaseConnectionError
from backend.repositories.users import SqlServerUserRepository

USER_ID = str(uuid4())
COLUMNS = ["id", "name", "email", "role", "active", "password_hash"]
ROW = (USER_ID, "Persona hospital", "persona@sgabriel.pe", "Responsable de almacén", 1, "$argon2id$fake")


class FakeCursor:
    def __init__(self, rows=(), columns=COLUMNS, error=None):
        self.rows = list(rows)
        self.description = None if columns is None else [(c,) for c in columns]
        self.error = error
        self.commands = []

    def execute(self, statement, *args):
        self.commands.append((statement, args))
        if self.error:
            raise self.error

    def fetchone(self):
        return self.rows.pop(0) if self.rows else None


class FakeDatabase:
    def __init__(self, cursor):
        self.cursor = cursor
        self.opens = 0
        self.closes = 0

    @contextmanager
    def connection(self):
        self.opens += 1
        try:
            yield self.cursor
        finally:
            self.closes += 1


def repository(rows=(), columns=COLUMNS, error=None):
    cursor = FakeCursor(rows, columns, error)
    database = FakeDatabase(cursor)
    return SqlServerUserRepository(database), cursor, database


def test_busca_por_email_normalizado_y_parametrizado():
    repo, cursor, db = repository([ROW])
    user = repo.find_by_email("  PERSONA@SGABRIEL.PE ")
    assert user.id == USER_ID
    assert user.active is True
    assert user.email == "persona@sgabriel.pe"
    assert user.password_hash == "$argon2id$fake"
    assert user.password_hash not in repr(user)
    assert cursor.commands == [
        ("EXEC dbo.usp_ObtenerUsuarioPorCorreo @email=?", ("persona@sgabriel.pe",))
    ]
    assert db.opens == db.closes == 1


def test_no_existe_usuario_devuelve_none():
    repo, _, db = repository()
    assert repo.find_by_email("nadie@hospital.example") is None
    assert db.closes == 1


def test_cuenta_inactiva_no_se_oculta_en_repositorio():
    repo, _, _ = repository([(*ROW[:4], 0, ROW[5])])
    assert repo.find_by_email("persona@sgabriel.pe").active is False


def test_por_id_parametrizado_y_formato_uuid():
    repo, cursor, _ = repository([ROW])
    assert repo.find_by_id(USER_ID.upper()).id == USER_ID
    assert cursor.commands == [("EXEC dbo.usp_ObtenerUsuarioPorId @user_id=?", (USER_ID,))]


def test_identificador_invalido_no_ejecuta_consulta():
    repo, cursor, db = repository([ROW])
    assert repo.find_by_id("no-es-un-guid") is None
    assert cursor.commands == []
    assert db.opens == 0


@pytest.mark.parametrize("columns,rows", [
    (None, (ROW,)), (["id"], (ROW,)),
    (["id", "id", "name", "email", "role", "active", "password_hash"], (ROW,)),
    (COLUMNS, (ROW[:5] + (None,),)),
    (COLUMNS, (ROW[:-1],)),
])
def test_respuesta_sql_invalida_no_expone_informacion(columns, rows):
    repo, _, db = repository(rows, columns)
    with pytest.raises(DatabaseConnectionError):
        repo.find_by_email("persona@sgabriel.pe")
    assert db.closes == 1


def test_error_odbc_se_traduce_sin_exponer_password():
    repo, _, db = repository(error=pyodbc.Error("28000", "PWD=secreto de SQL Server"))
    with pytest.raises(DatabaseConnectionError) as exc:
        repo.find_by_email("persona@sgabriel.pe")
    assert "secreto" not in str(exc.value)
    assert db.closes == 1


def test_hash_es_solo_interno_y_no_lo_expone_dataclass_repr():
    repo, _, _ = repository([ROW])
    assert "$argon2id$fake" not in repr(repo.find_by_email("persona@sgabriel.pe"))
