"""Interfaz de consulta de usuarios para el servicio de autenticación.

Esta etapa define solo el contrato: no hay conexión, consultas ni
procedimientos almacenados. La implementación definitiva leerá ``dbo.Users``
mediante un procedimiento almacenado, de modo que el servicio de login pueda
probarse con un repositorio falso sin depender de SQL Server.

Columnas de ``dbo.Users`` que utiliza el contrato:

- ``user_id``       -> ``UserRecord.id``
- ``name``          -> ``UserRecord.name``
- ``email``         -> ``UserRecord.email``
- ``role``          -> ``UserRecord.role``
- ``active``        -> ``UserRecord.active``
- ``password_hash`` -> ``UserRecord.password_hash``
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class UserRecord:
    """Datos de un usuario necesarios para autenticarlo.

    ``password_hash`` nunca se registra ni se serializa en una respuesta:
    ``repr`` lo oculta para evitar que aparezca por accidente en logs.
    """

    id: str
    name: str
    email: str
    role: str
    active: bool
    password_hash: str = field(repr=False)


class UserRepository(ABC):
    """Consultas de usuarios que implementará la capa de repositorios."""

    @abstractmethod
    def find_by_email(self, email: str) -> UserRecord | None:
        """Devuelve el usuario con ese correo, activo o no, o ``None``.

        La comparación debe ser insensible a mayúsculas, coherente con la
        colación de SQL Server y con el correo normalizado que recibe el
        servicio.
        """

    @abstractmethod
    def find_by_id(self, user_id: str) -> UserRecord | None:
        """Devuelve el usuario con ese identificador, o ``None``."""


__all__ = ["UserRecord", "UserRepository"]
