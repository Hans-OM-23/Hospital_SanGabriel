"""Verificación aislada de Argon2id y JWT (sin conexión a SQL Server)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from backend.core.exceptions import AccessTokenError, AuthConfigurationError
from backend.core.security import (
    JWT_ALGORITHM,
    create_access_token,
    decode_access_token,
    hash_password,
    jwt_secret_is_usable,
    password_needs_rehash,
    verify_password,
)

TEST_SECRET = "test-only-secret-" + "Z" * 48
SUBJECT = "11111111-1111-1111-1111-111111111111"
ROLE = "Responsable de almacén"


def test_argon2id_genera_salt_aleatoria_y_verifica_contrasena() -> None:
    primero = hash_password("Mi-clave-de-prueba")
    segundo = hash_password("Mi-clave-de-prueba")
    assert primero.startswith("$argon2id$")
    assert segundo != primero
    assert verify_password("Mi-clave-de-prueba", primero)
    assert not verify_password("clave-distinta", primero)
    assert not password_needs_rehash(primero)


@pytest.mark.parametrize("password, stored", [("clave", "hash-incorrecto"), ("clave", ""), ("", ""), (None, "abc")])
def test_verificacion_falla_de_forma_segura(password: object, stored: object) -> None:
    assert verify_password(password, stored) is False  # type: ignore[arg-type]


def test_hash_rechaza_contrasena_vacia() -> None:
    with pytest.raises(ValueError):
        hash_password("")


def test_hash_corrupto_requiere_actualizacion() -> None:
    assert password_needs_rehash("no-es-un-hash-argon2") is True


def test_jwt_hs256_roundtrip_preserva_usuario_rol_y_fechas() -> None:
    token = create_access_token(subject=SUBJECT, role=ROLE, secret_key=TEST_SECRET, expires_minutes=30)
    header = jwt.get_unverified_header(token)
    assert header["alg"] == JWT_ALGORITHM
    claims = decode_access_token(token, secret_key=TEST_SECRET)
    assert claims.subject == SUBJECT
    assert claims.role == ROLE
    assert claims.expires_at > claims.issued_at
    assert (claims.expires_at - claims.issued_at) == timedelta(minutes=30)


@pytest.mark.parametrize("secret", ["", "123", "ejemplo-publico-no-usar-en-produccion-0123456789", "cambia_esta_clave" + "x" * 40])
def test_no_se_aceptan_claves_jwt_ausentes_o_de_ejemplo(secret: str) -> None:
    assert not jwt_secret_is_usable(secret)
    with pytest.raises(AuthConfigurationError):
        create_access_token(subject=SUBJECT, role=ROLE, secret_key=secret, expires_minutes=30)


def test_token_con_firma_incorrecta_se_rechaza() -> None:
    token = create_access_token(subject=SUBJECT, role=ROLE, secret_key=TEST_SECRET, expires_minutes=30)
    with pytest.raises(AccessTokenError):
        decode_access_token(token, secret_key="otro-secreto-" + "B" * 48)


@pytest.mark.parametrize("algorithm", ["HS384", "HS512"])
def test_token_con_algoritmo_distinto_a_hs256_se_rechaza(algorithm: str) -> None:
    now = int(datetime.now(UTC).timestamp())
    token = jwt.encode({"sub": SUBJECT, "role": ROLE, "iat": now, "exp": now + 300}, TEST_SECRET, algorithm=algorithm)
    with pytest.raises(AccessTokenError):
        decode_access_token(token, secret_key=TEST_SECRET)


def test_token_expirado_se_rechaza() -> None:
    token = create_access_token(
        subject=SUBJECT, role=ROLE, secret_key=TEST_SECRET, expires_minutes=1,
        now=datetime.now(UTC) - timedelta(hours=1),
    )
    with pytest.raises(AccessTokenError):
        decode_access_token(token, secret_key=TEST_SECRET)


def test_token_emitido_en_el_futuro_se_rechaza() -> None:
    token = create_access_token(
        subject=SUBJECT, role=ROLE, secret_key=TEST_SECRET, expires_minutes=30,
        now=datetime.now(UTC) + timedelta(hours=1),
    )
    with pytest.raises(AccessTokenError):
        decode_access_token(token, secret_key=TEST_SECRET)


@pytest.mark.parametrize("missing", ["sub", "role", "iat", "exp"])
def test_token_sin_claim_obligatorio_se_rechaza(missing: str) -> None:
    now = int(datetime.now(UTC).timestamp())
    claims = {"sub": SUBJECT, "role": ROLE, "iat": now, "exp": now + 300}
    claims.pop(missing)
    token = jwt.encode(claims, TEST_SECRET, algorithm="HS256")
    with pytest.raises(AccessTokenError):
        decode_access_token(token, secret_key=TEST_SECRET)


@pytest.mark.parametrize("change", [
    {"sub": "  "},
    {"role": ""},
    {"iat": True},
    {"exp": True},
])
def test_jwt_con_claims_invalidos_se_rechaza(change: dict[str, object]) -> None:
    now = int(datetime.now(UTC).timestamp())
    payload = {"sub": SUBJECT, "role": ROLE, "iat": now, "exp": now + 300}
    payload.update(change)
    token = jwt.encode(payload, TEST_SECRET, algorithm="HS256")
    with pytest.raises(AccessTokenError):
        decode_access_token(token, secret_key=TEST_SECRET)


@pytest.mark.parametrize("minutes", [0, -1, 10081, 1.5, True])
def test_jwt_rechaza_duracion_invalida(minutes: object) -> None:
    with pytest.raises(ValueError):
        create_access_token(subject=SUBJECT, role=ROLE, secret_key=TEST_SECRET, expires_minutes=minutes)  # type: ignore[arg-type]


def test_jwt_rechaza_asunto_vacio_y_fecha_sin_zona() -> None:
    with pytest.raises(ValueError):
        create_access_token(subject=" ", role=ROLE, secret_key=TEST_SECRET, expires_minutes=10)
    with pytest.raises(ValueError):
        create_access_token(subject=SUBJECT, role=ROLE, secret_key=TEST_SECRET, expires_minutes=10,
                            now=datetime(2026, 11, 1))


def test_token_malformado_se_rechaza_sin_filtrar_credenciales() -> None:
    with pytest.raises(AccessTokenError) as info:
        decode_access_token("un-token-invalido", secret_key=TEST_SECRET)
    assert TEST_SECRET not in str(info.value)
    assert "un-token-invalido" not in str(info.value)
