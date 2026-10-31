"""Autenticación con repositorio de prueba, sin SQL Server ni credenciales reales."""

from __future__ import annotations

import pytest

from backend.core.config import Settings
from backend.core.exceptions import AuthConfigurationError, InvalidCredentialsError
from backend.core.security import decode_access_token, hash_password
from backend.repositories.users import UserRecord, UserRepository
from backend.schemas.auth import LoginRequest
from backend.services.auth_service import AuthService

TEST_SECRET = "only-for-auth-service-tests-" + "X" * 40
TEST_PASSWORD = "contrasena-de-test"


class FakeUsers(UserRepository):
    def __init__(self, user: UserRecord | None):
        self.user = user
        self.last_email: str | None = None

    def find_by_email(self, email: str) -> UserRecord | None:
        self.last_email = email
        return self.user if self.user and self.user.email.lower() == email else None

    def find_by_id(self, user_id: str) -> UserRecord | None:
        return self.user if self.user and self.user.id == user_id else None


@pytest.fixture(scope="module")
def user() -> UserRecord:
    return UserRecord(
        id="22222222-2222-2222-2222-222222222222",
        name="Usuario de prueba",
        email="test@hospital.example",
        role="Responsable de almacén",
        active=True,
        password_hash=hash_password(TEST_PASSWORD),
    )


def make_settings(secret: str = TEST_SECRET) -> Settings:
    return Settings(_env_file=None, jwt_secret_key=secret)


def test_login_correcto_devuelve_contrato_y_jwt_valido(user: UserRecord) -> None:
    repo = FakeUsers(user)
    credentials = LoginRequest(email=" TEST@HOSPITAL.EXAMPLE ", password=TEST_PASSWORD)
    result = AuthService(repo, make_settings()).authenticate(credentials)
    assert repo.last_email == "test@hospital.example"
    assert result.user.id == user.id
    assert result.user.email == user.email
    assert result.user.role == user.role
    response = result.model_dump(mode="json")
    assert set(response) == {"accessToken", "user"}
    assert set(response["user"]) == {"id", "name", "email", "role"}
    assert "password_hash" not in str(response)
    claims = decode_access_token(result.access_token, secret_key=TEST_SECRET)
    assert claims.subject == user.id
    assert claims.role == user.role


@pytest.mark.parametrize("case", ["no-existe", "clave-incorrecta", "inactivo"])
def test_login_invalido_usa_mismo_error_sin_revelar_usuarios(user: UserRecord, case: str) -> None:
    if case == "no-existe":
        repo = FakeUsers(None)
        password = TEST_PASSWORD
    elif case == "clave-incorrecta":
        repo = FakeUsers(user)
        password = "no-es-la-clave"
    else:
        repo = FakeUsers(UserRecord(user.id, user.name, user.email, user.role, False, user.password_hash))
        password = TEST_PASSWORD

    with pytest.raises(InvalidCredentialsError) as info:
        AuthService(repo, make_settings()).authenticate(
            LoginRequest(email="test@hospital.example", password=password)
        )
    assert "correo o la contraseña" in str(info.value)
    assert TEST_PASSWORD not in str(info.value)
    assert user.password_hash not in str(info.value)


def test_auth_no_firma_token_si_no_hay_secret(user: UserRecord) -> None:
    with pytest.raises(AuthConfigurationError):
        AuthService(FakeUsers(user), make_settings("")).authenticate(
            LoginRequest(email=user.email, password=TEST_PASSWORD)
        )


def test_userrecord_no_imprime_hash_en_repr(user: UserRecord) -> None:
    assert user.password_hash not in repr(user)
