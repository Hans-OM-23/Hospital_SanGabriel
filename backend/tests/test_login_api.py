"""Etapa 11: endpoint HTTP de login, sin SQL Server ni cuentas en producción."""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.apis.auth_api import get_auth_service
from backend.core.config import Settings, get_settings
from backend.core.exceptions import (
    AuthConfigurationError, DatabaseConnectionError, InvalidCredentialsError,
)
from backend.core.security import create_access_token, decode_access_token
from backend.main import create_app
from backend.schemas.auth import AuthenticatedUser, LoginResponse

SECRET = "solo-pruebas-etapa-11-" + "L" * 55
USER_ID = str(uuid4())


class FakeAuthService:
    def __init__(self) -> None:
        self.calls = []
        self.error = None

    def authenticate(self, credentials):
        self.calls.append(credentials)
        if self.error:
            raise self.error
        return LoginResponse(
            access_token=create_access_token(
                subject=USER_ID, role="Responsable de almacén",
                secret_key=SECRET, expires_minutes=30,
            ),
            user=AuthenticatedUser(
                id=USER_ID, name="Personal de prueba", email=credentials.email,
                role="Responsable de almacén",
            ),
        )


@pytest.fixture
def setup() -> Iterator[tuple[TestClient, FakeAuthService]]:
    app = create_app()
    fake = FakeAuthService()
    app.dependency_overrides[get_auth_service] = lambda: fake
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, jwt_secret_key=SECRET,
    )
    with TestClient(app) as client:
        yield client, fake


def credentials(**changes):
    data = {"email": "empleado@hospital.example", "password": "clave de test"}
    data.update(changes)
    return data


def test_login_publico_200_json_camel_case_jwt_valido(setup):
    client, fake = setup
    response = client.post("/api/auth/login", json=credentials())
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"accessToken", "user"}
    assert set(data["user"]) == {"id", "name", "email", "role"}
    assert data["user"]["id"] == USER_ID
    assert data["user"]["role"] == "Responsable de almacén"
    assert decode_access_token(data["accessToken"], secret_key=SECRET).subject == USER_ID
    assert fake.calls[0].password == "clave de test"
    assert "password" not in data and "password_hash" not in str(data)
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"


def test_login_no_pide_authorization_y_no_habilita_rutas_inventory(setup):
    client, _ = setup
    assert client.post("/api/auth/login", json=credentials()).status_code == 200
    assert client.get("/api/products").status_code == 401


def test_login_normaliza_email_sin_cambiar_password(setup):
    client, fake = setup
    response = client.post("/api/auth/login", json={
        "email": " EMPLEADO@HOSPITAL.EXAMPLE ", "password": " clave de test ",
    })
    assert response.status_code == 200
    assert fake.calls[0].email == "EMPLEADO@HOSPITAL.EXAMPLE"
    assert fake.calls[0].password == " clave de test "


@pytest.mark.parametrize("error", [
    InvalidCredentialsError(), InvalidCredentialsError("otra razón secreta"),
])
def test_credenciales_invalidas_devuelven_401_generico_sin_filtraciones(setup, error):
    client, fake = setup
    fake.error = error
    response = client.post("/api/auth/login", json=credentials())
    assert response.status_code == 401
    assert response.json() == {"detail": "El correo o la contraseña no son correctos."}
    assert "razón secreta" not in response.text


@pytest.mark.parametrize("data", [
    {}, {"password": "abc"}, {"email": "mal", "password": "abc"},
    {"email": "test@hospital.example", "password": "   "},
    {"email": "test@hospital.example", "password": "abc", "id": "prohibido"},
])
def test_validacion_422_antes_de_consultar_servicio(setup, data):
    client, fake = setup
    response = client.post("/api/auth/login", json=data)
    assert response.status_code == 422
    assert fake.calls == []


def test_error_interno_configuracion_no_expone_secret(setup):
    client, fake = setup
    fake.error = AuthConfigurationError("JWT_SECRET_KEY=myprivatekey")
    response = client.post("/api/auth/login", json=credentials())
    assert response.status_code == 500
    assert response.json() == {"detail": "La autenticación no está disponible en este momento."}
    assert "myprivatekey" not in response.text


def test_error_bd_devuelve_503_sin_filtrar_informacion(setup):
    client, fake = setup
    fake.error = DatabaseConnectionError("PWD=supersecreta;SERVER=localhost")
    response = client.post("/api/auth/login", json=credentials())
    assert response.status_code == 503
    assert response.json() == {
        "detail": "El servicio de inventario no está disponible en este momento."
    }
    assert "supersecreta" not in response.text


def test_dependencia_real_sin_configuracion_bd_devuelve_503(setup):
    client, _ = setup
    client.app.dependency_overrides.pop(get_auth_service)
    client.app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, jwt_secret_key=SECRET,
        db_server="", db_name="", db_user="", db_password="",
    )
    response = client.post("/api/auth/login", json=credentials())
    assert response.status_code == 503


def test_openapi_registra_login_publico_y_modelos(setup):
    client, _ = setup
    doc = client.get("/openapi.json").json()
    login = doc["paths"]["/api/auth/login"]["post"]
    assert not login.get("security")
    assert "200" in login["responses"]
    assert "422" in login["responses"]
    assert "get" in doc["paths"]["/api/products"]
    assert "post" in doc["paths"]["/api/movements"]


def test_cors_login_desde_angular(setup):
    client, _ = setup
    response = client.options("/api/auth/login", headers={
        "Origin": "http://localhost:4200",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    })
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:4200"
