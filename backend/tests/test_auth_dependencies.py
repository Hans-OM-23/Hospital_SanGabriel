"""Verifica Bearer, 401, 403 y autorización de rutas, sin base de datos."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from collections.abc import Iterator

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from backend.apis.dependencies import get_token_claims, require_responsable_almacen
from backend.core.config import Settings, get_settings
from backend.core.security import create_access_token

TEST_SECRET = "test-only-dependencies-" + "Q" * 48
USER_ROLE = "Responsable de almacén"


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = FastAPI()
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, jwt_secret_key=TEST_SECRET)

    @app.get("/identity")
    def identity(claims=Depends(get_token_claims)):
        return {"sub": claims.subject, "role": claims.role}

    @app.get("/protected")
    def protected(claims=Depends(require_responsable_almacen)):
        return {"sub": claims.subject}

    with TestClient(app) as test_client:
        yield test_client


def bearer(role: str = USER_ROLE, *, old: bool = False) -> dict[str, str]:
    now = datetime.now(UTC) - timedelta(hours=1) if old else None
    token = create_access_token(subject="usuario-test", role=role, secret_key=TEST_SECRET,
                                expires_minutes=1 if old else 30, now=now)
    return {"Authorization": f"Bearer {token}"}


def test_identidad_y_autorizacion_valida(client: TestClient) -> None:
    assert client.get("/identity", headers=bearer()).json() == {
        "sub": "usuario-test", "role": USER_ROLE,
    }
    response = client.get("/protected", headers=bearer())
    assert response.status_code == 200
    assert response.json() == {"sub": "usuario-test"}


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Basic abc"}, {"Authorization": "Bearer "},
                                      {"Authorization": "Bearer no-es-jwt"}])
def test_peticion_sin_bearer_valido_devuelve_401(client: TestClient, headers: dict[str, str]) -> None:
    response = client.get("/protected", headers=headers)
    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"
    assert isinstance(response.json()["detail"], str)


def test_token_caducado_devuelve_401(client: TestClient) -> None:
    assert client.get("/protected", headers=bearer(old=True)).status_code == 401


def test_rol_sin_permiso_devuelve_403(client: TestClient) -> None:
    response = client.get("/protected", headers=bearer(role="Visitante"))
    assert response.status_code == 403
    assert "permisos" in response.json()["detail"]


def test_falta_de_secret_devuelve_500_sin_exponer_clave(client: TestClient) -> None:
    from backend.apis.dependencies import get_settings as original_settings_dependency
    # El Depends está conectado a get_settings, que puede sobrescribirse por app.
    app = client.app
    app.dependency_overrides[original_settings_dependency] = lambda: Settings(_env_file=None, jwt_secret_key="")
    response = client.get("/protected", headers=bearer())
    assert response.status_code == 500
    assert "JWT_SECRET_KEY" not in str(response.json())
