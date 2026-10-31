"""Hash de contraseñas y tokens de acceso de la API.

Responsabilidades de infraestructura de seguridad:

- **Contraseñas**: hash y verificación con Argon2id mediante ``argon2-cffi``,
  una implementación mantenida y compatible con Python 3.12. Nunca se guarda,
  registra ni compara una contraseña en texto plano.
- **Tokens**: emisión y validación de JWT firmados con HS256 mediante ``PyJWT``.
  Se valida la firma, el algoritmo permitido, ``exp``, ``iat`` y la estructura
  de los claims requeridos. No se implementa criptografía manual.

Este módulo no conoce FastAPI, la base de datos ni los schemas HTTP: recibe y
devuelve valores simples para poder probarse de forma aislada.

Los mensajes de error son genéricos y nunca incluyen la contraseña, el hash,
la clave de firma ni el token recibido.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from argon2.low_level import Type

from backend.core.exceptions import AccessTokenError, AuthConfigurationError

# Algoritmo simétrico permitido. El decodificador rechaza cualquier otro.
JWT_ALGORITHM = "HS256"

# Claims que todo token emitido y consumido por la API debe incluir.
JWT_REQUIRED_CLAIMS = ("sub", "role", "iat", "exp")

# RFC 7518: una clave HS256 debe tener al menos 256 bits (32 bytes).
MIN_JWT_SECRET_LENGTH = 32

# Valores de ejemplo o de relleno que nunca deben usarse para firmar tokens.
_PLACEHOLDER_SECRET_PREFIXES = (
    "cambia",
    "reemplaza",
    "ejemplo",
    "example",
    "changeme",
    "change-me",
    "change_me",
    "your-secret",
    "placeholder",
)

MIN_TOKEN_EXPIRE_MINUTES = 1
MAX_TOKEN_EXPIRE_MINUTES = 10_080  # Una semana
MAX_TOKEN_LENGTH = 4_096
MAX_SUBJECT_LENGTH = 100
MAX_ROLE_LENGTH = 50

# Parámetros recomendados por la biblioteca para Argon2id: 3 pasadas,
# 64 MiB de memoria y 4 hilos. El tipo explícito evita depender del valor
# predeterminado de la biblioteca.
_HASHER = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)

# Hash de una contraseña aleatoria que no corresponde a ningún usuario.
# El servicio de login lo verifica cuando el correo no existe, de modo que el
# tiempo de respuesta no revele si la cuenta está registrada.
DUMMY_PASSWORD_HASH = _HASHER.hash(secrets.token_urlsafe(32))


@dataclass(frozen=True, slots=True)
class TokenClaims:
    """Claims ya validados de un token de acceso."""

    subject: str
    role: str
    issued_at: datetime
    expires_at: datetime


def jwt_secret_is_usable(secret_key: str) -> bool:
    """Indica si una clave puede firmar tokens de forma segura.

    Debe ser texto de al menos 32 caracteres y no un valor de ejemplo.
    """
    if not isinstance(secret_key, str):
        return False

    clave = secret_key.strip()
    if len(clave) < MIN_JWT_SECRET_LENGTH:
        return False
    return not clave.lower().startswith(_PLACEHOLDER_SECRET_PREFIXES)


def _require_usable_secret(secret_key: str) -> None:
    """Rechaza la emisión o validación de tokens sin una clave segura."""
    if not jwt_secret_is_usable(secret_key):
        raise AuthConfigurationError(
            "JWT_SECRET_KEY no está configurada o no es segura. "
            "Genera una clave propia de al menos 32 caracteres."
        )


def hash_password(password: str) -> str:
    """Devuelve el hash Argon2id de una contraseña.

    Cada llamada usa una sal aleatoria distinta, por lo que dos hashes de la
    misma contraseña no coinciden.
    """
    if not isinstance(password, str) or not password:
        raise ValueError("La contraseña no puede estar vacía.")

    return _HASHER.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Comprueba una contraseña contra un hash Argon2id.

    Devuelve ``False`` ante una contraseña incorrecta, un hash mal formado o
    parámetros no reconocidos. No lanza errores que puedan revelar el motivo.
    """
    if not isinstance(password, str) or not isinstance(password_hash, str):
        return False
    if not password_hash.strip():
        return False

    try:
        return _HASHER.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    """Indica si un hash usa parámetros distintos a los actuales.

    Un hash ilegible se considera obsoleto. La actualización definitiva se
    hará cuando el repositorio de usuarios permita guardar el nuevo hash.
    """
    try:
        return _HASHER.check_needs_rehash(password_hash)
    except (InvalidHashError, TypeError):
        return True


def create_access_token(
    *,
    subject: str,
    role: str,
    secret_key: str,
    expires_minutes: int,
    now: datetime | None = None,
) -> str:
    """Firma un JWT HS256 con los claims ``sub``, ``role``, ``iat`` y ``exp``.

    ``now`` solo se usa en pruebas para simular la hora de emisión. Sin una
    clave segura se lanza :class:`AuthConfigurationError` y no se emite token.
    """
    _require_usable_secret(secret_key)

    sujeto = subject.strip() if isinstance(subject, str) else ""
    if not sujeto:
        raise ValueError("El sujeto del token no puede estar vacío.")
    if len(sujeto) > MAX_SUBJECT_LENGTH:
        raise ValueError("El sujeto del token no es válido.")

    perfil = role.strip() if isinstance(role, str) else ""
    if not perfil:
        raise ValueError("El rol del token no puede estar vacío.")
    if len(perfil) > MAX_ROLE_LENGTH:
        raise ValueError("El rol del token no es válido.")

    if isinstance(expires_minutes, bool) or not isinstance(expires_minutes, int):
        raise ValueError("La vigencia del token debe expresarse en minutos enteros.")
    if not MIN_TOKEN_EXPIRE_MINUTES <= expires_minutes <= MAX_TOKEN_EXPIRE_MINUTES:
        raise ValueError("La vigencia del token está fuera del rango permitido.")

    emitido = now if now is not None else datetime.now(UTC)
    if emitido.tzinfo is None or emitido.utcoffset() is None:
        raise ValueError("La hora de emisión debe incluir zona horaria.")

    vence = emitido + timedelta(minutes=expires_minutes)
    payload = {
        "sub": sujeto,
        "role": perfil,
        "iat": int(emitido.timestamp()),
        "exp": int(vence.timestamp()),
    }

    return jwt.encode(payload, secret_key, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str, *, secret_key: str) -> TokenClaims:
    """Valida un JWT HS256 y devuelve sus claims.

    Rechaza tokens vacíos, mal formados, con otra firma, con otro algoritmo,
    caducados, emitidos en el futuro o sin alguno de los claims obligatorios.
    """
    _require_usable_secret(secret_key)

    if not isinstance(token, str):
        raise AccessTokenError()

    limpio = token.strip()
    if not limpio or len(limpio) > MAX_TOKEN_LENGTH:
        raise AccessTokenError()

    try:
        payload = jwt.decode(
            limpio,
            secret_key,
            algorithms=[JWT_ALGORITHM],
            leeway=0,
            options={
                "require": list(JWT_REQUIRED_CLAIMS),
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_sub": True,
                "enforce_minimum_key_length": True,
            },
        )
    except jwt.PyJWTError:
        # No se encadena la excepción original: su detalle no debe exponerse.
        raise AccessTokenError() from None

    return _claims_from_payload(payload)


def _claims_from_payload(payload: dict[str, Any]) -> TokenClaims:
    """Comprueba tipos y coherencia de los claims ya verificados."""
    sujeto = payload.get("sub")
    perfil = payload.get("role")
    emitido = payload.get("iat")
    vence = payload.get("exp")

    if not isinstance(sujeto, str):
        raise AccessTokenError()
    sujeto = sujeto.strip()
    if not sujeto or len(sujeto) > MAX_SUBJECT_LENGTH:
        raise AccessTokenError()

    if not isinstance(perfil, str):
        raise AccessTokenError()
    perfil = perfil.strip()
    if not perfil or len(perfil) > MAX_ROLE_LENGTH:
        raise AccessTokenError()

    if isinstance(emitido, bool) or not isinstance(emitido, int):
        raise AccessTokenError()
    if isinstance(vence, bool) or not isinstance(vence, int):
        raise AccessTokenError()
    if vence <= emitido:
        raise AccessTokenError()

    try:
        fecha_emision = datetime.fromtimestamp(emitido, UTC)
        fecha_vencimiento = datetime.fromtimestamp(vence, UTC)
    except (OverflowError, OSError, ValueError):
        raise AccessTokenError() from None

    return TokenClaims(
        subject=sujeto,
        role=perfil,
        issued_at=fecha_emision,
        expires_at=fecha_vencimiento,
    )


__all__ = [
    "DUMMY_PASSWORD_HASH",
    "JWT_ALGORITHM",
    "JWT_REQUIRED_CLAIMS",
    "MAX_TOKEN_EXPIRE_MINUTES",
    "MIN_JWT_SECRET_LENGTH",
    "MIN_TOKEN_EXPIRE_MINUTES",
    "TokenClaims",
    "create_access_token",
    "decode_access_token",
    "hash_password",
    "jwt_secret_is_usable",
    "password_needs_rehash",
    "verify_password",
]
