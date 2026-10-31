"""Servicio de autenticación: credenciales, contraseña y emisión de JWT.

El servicio recibe un :class:`UserRepository` por inyección, de modo que la
lógica puede probarse sin SQL Server. El repositorio implementado consulta ``dbo.Users`` mediante procedimientos
almacenados y la API expone ``POST /api/auth/login``.

No hay usuarios, correos ni contraseñas fijas en este módulo. La contraseña
solo se compara mediante Argon2id; el token se emite con HS256 y una clave
configurada por el entorno.
"""

from __future__ import annotations

from backend.core.config import Settings
from backend.core.exceptions import InvalidCredentialsError
from backend.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    verify_password,
)
from backend.repositories.users import UserRepository
from backend.schemas.auth import AuthenticatedUser, LoginRequest, LoginResponse


class AuthService:
    """Verifica credenciales y construye la respuesta de inicio de sesión."""

    def __init__(self, users: UserRepository, settings: Settings) -> None:
        self._users = users
        self._settings = settings

    def authenticate(self, credentials: LoginRequest) -> LoginResponse:
        """Valida el correo y la contraseña, y emite un token si son correctos.

        Se usa el mismo error para un correo desconocido, una contraseña
        incorrecta y una cuenta inactiva, y se verifica un hash ficticio cuando
        el correo no existe para no revelar por tiempo de respuesta si la
        cuenta está registrada.
        """
        email = credentials.email.strip().lower()
        user = self._users.find_by_email(email)

        if user is None:
            verify_password(credentials.password, DUMMY_PASSWORD_HASH)
            raise InvalidCredentialsError()

        password_ok = verify_password(credentials.password, user.password_hash)
        if not password_ok or not user.active:
            raise InvalidCredentialsError()

        token = create_access_token(
            subject=user.id,
            role=user.role,
            secret_key=self._settings.require_jwt_secret(),
            expires_minutes=self._settings.jwt_access_token_expire_minutes,
        )

        return LoginResponse(
            access_token=token,
            user=AuthenticatedUser(
                id=user.id,
                name=user.name,
                email=user.email,
                role=user.role,
            ),
        )


__all__ = ["AuthService"]
