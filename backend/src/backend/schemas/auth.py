"""Schemas de inicio de sesión y usuario autenticado.

El rol se restringe al valor que admite la interfaz actual
(``Session['role']``). El token y el ciclo de sesión los emitirá el servicio
de autenticación en una etapa posterior; aquí solo se define su forma.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BeforeValidator
from pydantic_core import PydanticCustomError

from backend.schemas.common import ApiInput, ApiResponse, Identifier, texto_obligatorio

# Misma expresión que usa el validador `email` de Angular 22, para no aceptar
# direcciones que el propio formulario rechazaría.
_EMAIL_PATTERN = re.compile(
    r"^(?=.{1,254}$)(?=.{1,64}@)"
    r"[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+)*"
    r"@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
)

MAX_PASSWORD_LENGTH = 200


def _validar_email(value: Any) -> str:
    if not isinstance(value, str):
        raise PydanticCustomError("email", "Escribe tu correo institucional.")

    correo = value.strip()
    if not correo:
        raise PydanticCustomError("email", "Escribe tu correo institucional.")
    if not _EMAIL_PATTERN.fullmatch(correo):
        raise PydanticCustomError(
            "email",
            "Ingresa un correo válido, por ejemplo: example@example.pe",
        )
    return correo


def _validar_password(value: Any) -> str:
    """Valida forma, no contenido: nunca se recorta ni se transforma."""
    if not isinstance(value, str):
        raise PydanticCustomError("password", "Escribe tu contraseña.")
    if not value.strip():
        raise PydanticCustomError(
            "password_blank",
            "La contraseña no puede contener solamente espacios.",
        )
    if len(value) > MAX_PASSWORD_LENGTH:
        raise PydanticCustomError(
            "password_length",
            f"La contraseña admite hasta {MAX_PASSWORD_LENGTH} caracteres.",
        )
    return value


EmailAddress = Annotated[str, BeforeValidator(_validar_email)]
Password = Annotated[str, BeforeValidator(_validar_password)]

AccessToken = texto_obligatorio(
    max_length=4096,
    mensaje_requerido="El token de acceso no puede estar vacío.",
    mensaje_longitud="El token de acceso no es válido.",
)


class UserRole(StrEnum):
    """Único perfil admitido por la interfaz actual."""

    RESPONSABLE_ALMACEN = "Responsable de almacén"


class LoginRequest(ApiInput):
    """Cuerpo de ``POST /auth/login`` (``LoginCredentials`` en Angular)."""

    email: EmailAddress
    password: Password


class AuthenticatedUser(ApiResponse):
    """Usuario devuelto dentro de ``AuthResponse``."""

    id: Identifier
    name: str
    email: str
    role: UserRole


class LoginResponse(ApiResponse):
    """Respuesta de ``POST /auth/login`` (``AuthResponse`` en Angular)."""

    access_token: AccessToken
    user: AuthenticatedUser


__all__ = [
    "AccessToken",
    "AuthenticatedUser",
    "EmailAddress",
    "LoginRequest",
    "LoginResponse",
    "Password",
    "UserRole",
]
