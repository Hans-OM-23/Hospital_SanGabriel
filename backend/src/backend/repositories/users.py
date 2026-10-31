"""Acceso a usuarios de la aplicación únicamente por procedimientos almacenados.

``SqlServerUserRepository`` consulta ``dbo.Users`` a través de los procedimientos
``usp_ObtenerUsuarioPorCorreo`` y ``usp_ObtenerUsuarioPorId``. No realiza
consultas SQL directas ni conserva contraseñas en texto plano.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import UUID

import pyodbc

from backend.core.exceptions import DatabaseConnectionError

if TYPE_CHECKING:
    from backend.core.database import Database


@dataclass(frozen=True, slots=True)
class UserRecord:
    """Datos internos de autenticación; el hash no aparece en ``repr``."""

    id: str
    name: str
    email: str
    role: str
    active: bool
    password_hash: str = field(repr=False)


class UserRepository(ABC):
    """Contrato que permite sustituir SQL Server en pruebas unitarias."""

    @abstractmethod
    def find_by_email(self, email: str) -> UserRecord | None:
        """Busca una cuenta por correo, aunque esté desactivada."""

    @abstractmethod
    def find_by_id(self, user_id: str) -> UserRecord | None:
        """Busca una cuenta por identificador."""


class SqlServerUserRepository(UserRepository):
    """Repositorio real de usuarios con parámetros ODBC y cierre automático."""

    _BY_EMAIL = "EXEC dbo.usp_ObtenerUsuarioPorCorreo @email=?"
    _BY_ID = "EXEC dbo.usp_ObtenerUsuarioPorId @user_id=?"
    _COLUMNS = frozenset({"id", "name", "email", "role", "active", "password_hash"})

    def __init__(self, database: Database) -> None:
        self._database = database

    def _find(self, statement: str, parameter: str) -> UserRecord | None:
        try:
            with self._database.connection() as cursor:
                cursor.execute(statement, parameter)
                if cursor.description is None:
                    raise DatabaseConnectionError(
                        "El procedimiento de usuarios no devolvió el formato esperado."
                    )

                columns = [str(column[0]) for column in cursor.description]
                if len(columns) != len(set(columns)) or not self._COLUMNS.issubset(columns):
                    raise DatabaseConnectionError(
                        "El procedimiento de usuarios no devolvió el formato esperado."
                    )

                record = cursor.fetchone()
                if record is None:
                    return None
                if len(record) != len(columns):
                    raise DatabaseConnectionError(
                        "El procedimiento de usuarios devolvió datos incompletos."
                    )

                data = dict(zip(columns, record, strict=True))
                if any(data[column] is None for column in self._COLUMNS):
                    raise DatabaseConnectionError(
                        "El procedimiento de usuarios devolvió datos incompletos."
                    )
                return UserRecord(
                    id=str(data["id"]),
                    name=str(data["name"]),
                    email=str(data["email"]),
                    role=str(data["role"]),
                    active=bool(data["active"]),
                    password_hash=str(data["password_hash"]),
                )
        except pyodbc.Error:
            # Nunca devolver el mensaje bruto del controlador ni la consulta.
            raise DatabaseConnectionError(
                "No se pudo consultar la cuenta de usuario."
            ) from None

    def find_by_email(self, email: str) -> UserRecord | None:
        return self._find(self._BY_EMAIL, email.strip().lower())

    def find_by_id(self, user_id: str) -> UserRecord | None:
        try:
            identifier = str(UUID(user_id))
        except (ValueError, TypeError, AttributeError):
            return None
        return self._find(self._BY_ID, identifier)


__all__ = ["SqlServerUserRepository", "UserRecord", "UserRepository"]
