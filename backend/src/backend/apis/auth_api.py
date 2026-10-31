"""Inicio de sesión real: POST /api/auth/login.

No usa cuentas locales simuladas. ``AuthService`` verifica credenciales contra
``SqlServerUserRepository`` y emite JWT; la API solo traduce errores HTTP.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from backend.core.config import Settings, get_settings
from backend.core.database import Database
from backend.core.exceptions import AuthConfigurationError, InvalidCredentialsError
from backend.repositories.users import SqlServerUserRepository
from backend.schemas.auth import LoginRequest, LoginResponse
from backend.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["autenticación"])


def get_auth_service(settings: Settings = Depends(get_settings)) -> AuthService:
    """Construye dependencias por solicitud; sin conectar al importar módulos."""
    return AuthService(SqlServerUserRepository(Database(settings)), settings)


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK,
             summary="Iniciar sesión")
def login(
    data: LoginRequest,
    response: Response,
    service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    """Devuelve ``accessToken`` y usuario si la cuenta está activa y la clave coincide."""
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    try:
        return service.authenticate(data)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El correo o la contraseña no son correctos.",
        ) from None
    except AuthConfigurationError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="La autenticación no está disponible en este momento.",
        ) from None


__all__ = ["router", "get_auth_service"]
