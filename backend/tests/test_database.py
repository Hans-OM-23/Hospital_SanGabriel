"""Pruebas unitarias de la capa de datos con conexiones simuladas.

Estas pruebas NO demuestran una conexión real a SQL Server: comprueban el
contrato de `Database` (commit, rollback, cierre de recursos y manejo seguro
de errores). La conexión real se valida en `test_database_integration.py`.
"""

import logging

import pyodbc
import pytest

from backend.core.config import Settings
from backend.core.database import Database
from backend.core.exceptions import DatabaseConfigurationError, DatabaseConnectionError

CLAVE_DE_PRUEBA = "clave-de-prueba-no-real"


class FakeCursor:
    def __init__(self) -> None:
        self.sentencias: list[tuple[str, tuple]] = []
        self.closed = False
        self.fila = (1, "HospitalSanGabriel", "usuario_sql")

    def execute(self, sql: str, *params: object) -> "FakeCursor":
        self.sentencias.append((sql, params))
        return self

    def fetchone(self) -> tuple:
        return self.fila

    def close(self) -> None:
        self.closed = True


class FakeConnection:
    def __init__(self) -> None:
        self.cursor_instance = FakeCursor()
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self) -> FakeCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def settings() -> Settings:
    return Settings(
        db_server="localhost",
        db_name="HospitalSanGabriel",
        db_user="usuario_sql",
        db_password=CLAVE_DE_PRUEBA,
        db_driver="ODBC Driver 18 for SQL Server",
    )


@pytest.fixture
def fake_connection(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> FakeConnection:
    fake = FakeConnection()
    monkeypatch.setattr("backend.core.database.pyodbc.connect", lambda *a, **k: fake)
    monkeypatch.setattr("backend.core.database.pyodbc.drivers", lambda: [settings.db_driver])
    return fake


def test_transaction_confirma_cambios_y_cierra_recursos(
    settings: Settings, fake_connection: FakeConnection
) -> None:
    db = Database(settings)

    with db.transaction() as cursor:
        cursor.execute("INSERT INTO prueba VALUES (?)", 1)

    assert fake_connection.committed is True
    assert fake_connection.rolled_back is False
    assert fake_connection.closed is True
    assert fake_connection.cursor_instance.closed is True


def test_transaction_revierte_ante_error(
    settings: Settings, fake_connection: FakeConnection
) -> None:
    db = Database(settings)

    with pytest.raises(RuntimeError, match="fallo simulado"):
        with db.transaction() as cursor:
            cursor.execute("INSERT INTO prueba VALUES (?)", 1)
            raise RuntimeError("fallo simulado")

    assert fake_connection.rolled_back is True
    assert fake_connection.committed is False
    assert fake_connection.closed is True
    assert fake_connection.cursor_instance.closed is True


def test_connection_solo_lee_y_cierra_recursos(
    settings: Settings, fake_connection: FakeConnection
) -> None:
    db = Database(settings)

    with db.connection() as cursor:
        cursor.execute("SELECT 1")

    assert fake_connection.committed is False
    assert fake_connection.rolled_back is False
    assert fake_connection.closed is True
    assert fake_connection.cursor_instance.closed is True


def test_connection_cierra_ante_error_en_el_bloque(
    settings: Settings, fake_connection: FakeConnection
) -> None:
    db = Database(settings)

    with pytest.raises(ValueError):
        with db.connection() as cursor:
            cursor.execute("SELECT 1")
            raise ValueError("error de lectura")

    assert fake_connection.closed is True
    assert fake_connection.cursor_instance.closed is True


def test_configuracion_incompleta_no_intenta_conectar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def no_debe_conectar(*args: object, **kwargs: object) -> None:
        raise AssertionError("No debe intentar conectarse sin configuración")

    monkeypatch.setattr("backend.core.database.pyodbc.connect", no_debe_conectar)
    incompleta = Settings(db_server="", db_name="", db_user="", db_password="")

    with pytest.raises(DatabaseConfigurationError) as excinfo:
        Database(incompleta)

    mensaje = str(excinfo.value)
    assert "DB_SERVER" in mensaje
    assert "DB_PASSWORD" in mensaje
    assert "clave" not in mensaje.lower()


def test_error_de_conexion_no_expone_credenciales_ni_mensaje_odbc(
    settings: Settings, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    mensaje_bruto = f"Login failed for user 'usuario_sql'; PWD={{{CLAVE_DE_PRUEBA}}};"

    def conexion_fallida(*args: object, **kwargs: object) -> None:
        raise pyodbc.InterfaceError("28000", mensaje_bruto)

    monkeypatch.setattr("backend.core.database.pyodbc.connect", conexion_fallida)
    monkeypatch.setattr("backend.core.database.pyodbc.drivers", lambda: [settings.db_driver])

    with caplog.at_level(logging.ERROR):
        with pytest.raises(DatabaseConnectionError) as excinfo:
            Database(settings).connect()

    error = excinfo.value
    assert error.__suppress_context__ is True
    assert CLAVE_DE_PRUEBA not in str(error)
    assert "PWD" not in str(error)
    assert "Login failed" not in str(error)

    assert CLAVE_DE_PRUEBA not in caplog.text
    assert "Login failed" not in caplog.text
    assert "SQLSTATE=28000" in caplog.text


def test_driver_ausente_produce_error_de_configuracion(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("backend.core.database.pyodbc.drivers", lambda: ["SQL Server"])

    with pytest.raises(DatabaseConfigurationError) as excinfo:
        Database(settings).connect()

    assert "ODBC Driver 18 for SQL Server" in str(excinfo.value)
    assert "SQL Server" in str(excinfo.value)


def test_cadena_de_conexion_escapa_caracteres_especiales() -> None:
    settings = Settings(
        db_server="localhost",
        db_name="HospitalSanGabriel",
        db_user="usuario_sql",
        db_password="clave;con}corte",
        db_encrypt="yes",
        db_trust_server_certificate="no",
    )

    cadena = Database(settings)._connection_string()

    assert "PWD={clave;con}}corte}" in cadena
    assert "DRIVER={ODBC Driver 18 for SQL Server}" in cadena
    assert "Encrypt=yes" in cadena
    assert "TrustServerCertificate=no" in cadena


def test_connect_desactiva_autocommit(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    capturado: dict[str, object] = {}
    fake = FakeConnection()

    def conexion_capturada(cadena: str, **kwargs: object) -> FakeConnection:
        capturado["cadena"] = cadena
        capturado["kwargs"] = kwargs
        return fake

    monkeypatch.setattr("backend.core.database.pyodbc.connect", conexion_capturada)
    monkeypatch.setattr("backend.core.database.pyodbc.drivers", lambda: [settings.db_driver])

    Database(settings).connect()

    assert capturado["kwargs"] == {"autocommit": False, "timeout": 5}


def test_test_connection_devuelve_datos_sin_credenciales(
    settings: Settings, fake_connection: FakeConnection
) -> None:
    info = Database(settings).test_connection()

    assert info == {
        "connected": True,
        "server": "localhost",
        "database": "HospitalSanGabriel",
        "login": "usuario_sql",
    }
    assert CLAVE_DE_PRUEBA not in str(info)
