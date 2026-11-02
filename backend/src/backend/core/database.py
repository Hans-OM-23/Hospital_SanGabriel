"""Conexión y transacciones con SQL Server mediante pyodbc, sin ORM.

Toda consulta al inventario se ejecutará posteriormente con procedimientos
almacenados parametrizados. Este módulo solo administra la conexión, el commit,
el rollback y el cierre de recursos.
"""

import logging
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from typing import Any

import pyodbc

from backend.core.config import Settings
from backend.core.exceptions import DatabaseConfigurationError, DatabaseConnectionError

logger = logging.getLogger(__name__)

_LOGIN_TIMEOUT_SECONDS = 5


def _odbc_value(value: str) -> str:
    """Escapa un valor para una cadena de conexión ODBC.

    ODBC permite encerrar valores entre llaves para admitir espacios y punto y
    coma; una llave de cierre literal se representa duplicándola.
    """
    return "{" + value.replace("}", "}}") + "}"


def _odbc_flag(value: str, default: str) -> str:
    """Normaliza Encrypt y TrustServerCertificate a yes/no."""
    normalizado = value.strip().lower()
    if normalizado in {"yes", "true", "1"}:
        return "yes"
    if normalizado in {"no", "false", "0"}:
        return "no"
    return default


def _safe_diagnostic(error: BaseException) -> str:
    """Resume un error de pyodbc sin exponer su mensaje bruto.

    Solo registra el tipo de excepción y el SQLSTATE cuando está disponible.
    Nunca incluye credenciales, cadenas de conexión ni texto del servidor.
    """
    args = getattr(error, "args", ()) or ()
    sqlstate = str(args[0]).strip()[:10] if args else ""
    nombre = type(error).__name__
    return f"{nombre} (SQLSTATE={sqlstate})" if sqlstate else nombre


def _close_quietly(resource: Any) -> None:
    """Cierra un recurso sin ocultar el error original del bloque."""
    with suppress(Exception):
        resource.close()


class Database:
    """Administra conexiones y transacciones de SQL Server."""

    def __init__(self, settings: Settings) -> None:
        faltantes = settings.missing_database_settings
        if faltantes:
            raise DatabaseConfigurationError(
                "Faltan variables de conexión en backend/.env: " + ", ".join(faltantes)
            )
        self._settings = settings

    @property
    def driver(self) -> str:
        return self._settings.db_driver

    def _ensure_driver_available(self) -> None:
        """Verifica que el controlador ODBC configurado exista en el sistema."""
        try:
            disponibles = list(pyodbc.drivers())
        except pyodbc.Error:  # pragma: no cover - el driver manager no responde
            disponibles = []

        if disponibles and self.driver not in disponibles:
            raise DatabaseConfigurationError(
                f"Controlador ODBC no instalado: {self.driver}. "
                f"Disponibles: {', '.join(disponibles)}"
            )

    def _connection_string(self) -> str:
        """Construye la cadena de conexión. Uso interno: nunca se registra."""
        s = self._settings
        return ";".join(
            (
                f"DRIVER={_odbc_value(s.db_driver)}",
                f"SERVER={_odbc_value(s.db_server)}",
                f"DATABASE={_odbc_value(s.db_name)}",
                f"UID={_odbc_value(s.db_user)}",
                f"PWD={_odbc_value(s.db_password.get_secret_value())}",
                f"Encrypt={_odbc_flag(s.db_encrypt, 'yes')}",
                f"TrustServerCertificate={_odbc_flag(s.db_trust_server_certificate, 'no')}",
            )
        ) + ";"

    def connect(self) -> pyodbc.Connection:
        """Abre una conexión con autocommit desactivado."""
        self._ensure_driver_available()
        logger.info(
            "Abriendo conexión a SQL Server en %s (base %s)",
            self._settings.db_server,
            self._settings.db_name,
        )
        try:
            return pyodbc.connect(
                self._connection_string(),
                autocommit=False,
                timeout=_LOGIN_TIMEOUT_SECONDS,
            )
        except pyodbc.Error as error:
            logger.error("Falló la conexión a SQL Server: %s", _safe_diagnostic(error))
            # from None evita que la traza muestre el error original del driver.
            raise DatabaseConnectionError(
                "No se pudo conectar a SQL Server. Verifica DB_SERVER, DB_NAME, "
                "el controlador ODBC y las credenciales de autenticación SQL."
            ) from None

    @contextmanager
    def connection(self) -> Iterator[pyodbc.Cursor]:
        """Entrega un cursor para lecturas y cierra los recursos al salir."""
        connection = self.connect()
        try:
            cursor = connection.cursor()
        except BaseException:
            _close_quietly(connection)
            raise

        try:
            yield cursor
        finally:
            _close_quietly(cursor)
            _close_quietly(connection)

    @contextmanager
    def transaction(self) -> Iterator[pyodbc.Cursor]:
        """Entrega un cursor para escrituras con commit o rollback garantizado.

        Confirma la transacción solo si el bloque termina sin excepciones.
        Ante cualquier error revierte los cambios y re-lanza la excepción.
        """
        connection = self.connect()
        try:
            cursor = connection.cursor()
        except BaseException:
            _close_quietly(connection)
            raise

        try:
            yield cursor
            connection.commit()
        except BaseException:
            try:
                connection.rollback()
            except Exception:
                logger.error("No se pudo revertir la transacción de SQL Server.")
            raise
        finally:
            _close_quietly(cursor)
            _close_quietly(connection)

    def test_connection(self) -> dict[str, Any]:
        """Comprueba la conexión con una consulta de solo lectura.

        Devuelve únicamente datos no sensibles del servidor y del inicio de
        sesión; no expone la contraseña ni la cadena de conexión.
        """
        try:
            with self.connection() as cursor:
                cursor.execute("SELECT 1, DB_NAME(), SUSER_SNAME()")
                row = cursor.fetchone()
        except pyodbc.Error as error:
            logger.error(
                "Falló la comprobación de conexión a SQL Server: %s",
                _safe_diagnostic(error),
            )
            raise DatabaseConnectionError(
                "La conexión se abrió, pero la comprobación con SQL Server falló."
            ) from None

        if row is None:
            raise DatabaseConnectionError(
                "SQL Server no devolvió datos en la comprobación de conexión."
            )

        return {
            "connected": True,
            "server": self._settings.db_server,
            "database": str(row[1]),
            "login": str(row[2]),
        }
