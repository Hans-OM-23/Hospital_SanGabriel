"""Dependencias HTTP de autenticación y autorización.

- **Autenticación**: :func:`get_token_claims` extrae el token Bearer, valida su
  firma, algoritmo, caducidad y claims, y devuelve la identidad autenticada.
- **Autorización**: :func:`require_roles` comprueba que esa identidad tenga uno
  de los perfiles permitidos. Están separadas para que cada ruta decida qué
  permiso exige sin repetir la validación del token.

Los errores siguen el contrato: 401 para token ausente o inválido (con
``WWW-Authenticate: Bearer``), 403 para permisos insuficientes y 500 si la
firma no está configurada. Ningún detalle incluye el token ni la clave.
"""

from __future__ import annotations

from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.core.config import Settings, get_settings
from backend.core.exceptions import AccessTokenError, AuthConfigurationError
from backend.core.security import TokenClaims, decode_access_token
from backend.schemas.auth import UserRole

bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="BearerJWT",
    description="Token JWT obtenido en POST /api/auth/login.",
)

_TOKEN_ERROR_DETAIL = "El token de acceso no es válido o ha expirado."
_CONFIG_ERROR_DETAIL = "La autenticación no está disponible en este momento."
_FORBIDDEN_DETAIL = "No tienes permisos para realizar esta operación."


def _unauthorized() -> HTTPException:
    """Respuesta 401 uniforme, sin revelar el motivo exacto del rechazo."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=_TOKEN_ERROR_DETAIL,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_token_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> TokenClaims:
    """Valida el token Bearer y devuelve sus claims.

    Requiere el encabezado ``Authorization: Bearer <token>``. No consulta la
    base de datos: la identidad se deriva del token firmado.
    """
    if credentials is None or not credentials.credentials.strip():
        raise _unauthorized()

    try:
        secret_key = settings.require_jwt_secret()
    except AuthConfigurationError:
        # Error del servidor: falta configuración segura. No se expone el motivo.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_CONFIG_ERROR_DETAIL,
        ) from None

    try:
        return decode_access_token(credentials.credentials, secret_key=secret_key)
    except AccessTokenError:
        raise _unauthorized() from None


def require_roles(*roles: UserRole) -> Callable[..., TokenClaims]:
    """Crea una dependencia que exige uno de los roles indicados.

    Debe usarse después de :func:`get_token_claims`: si el token es válido
    pero el rol no está permitido, responde 403.
    """
    permitidos = {role.value for role in roles}

    def dependency(claims: TokenClaims = Depends(get_token_claims)) -> TokenClaims:
        if claims.role not in permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=_FORBIDDEN_DETAIL,
            )
        return claims

    return dependency


# Perfil exigido por las rutas de inventario según frontend/docs/API-CONTRACT.md.
require_responsable_almacen = require_roles(UserRole.RESPONSABLE_ALMACEN)


__all__ = [
    "bearer_scheme",
    "get_token_claims",
    "require_responsable_almacen",
    "require_roles",
]
