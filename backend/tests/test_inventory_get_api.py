"""Etapa 8: cinco GET con JWT, DI, errores HTTP y contrato Angular.

Toda la ejecución es local al ASGI TestClient: sin datos mock en producción,
sin abrir SQL Server y sin modificar frontend/.env.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from backend.apis.inventory_api import get_inventory_read_service
from backend.core.config import Settings, get_settings
from backend.core.exceptions import DatabaseConnectionError
from backend.core.security import create_access_token
from backend.main import create_app
from backend.services.inventory_read_service import InventoryReadService

SECRET = "solo-tests-inventario-" + "T" * 48
ROLE = "Responsable de almacén"


class FakeService:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def list_products(self):
        self.calls.append("products")
        return [{"id": "p-1", "code": "MED-001", "name": "Paracetamol",
                 "description": "Tabletas", "categoryId": "c-1", "unit": "Tableta",
                 "unitPrice": 0.5, "minStock": 5, "tracksExpiration": False,
                 "expirationDate": None, "active": False}]

    def list_categories(self):
        self.calls.append("categories")
        return [{"id": "c-1", "name": "Medicamentos", "description": "Fármacos", "active": True}]

    def list_lots(self):
        self.calls.append("lots")
        return [{"id": "l-1", "productId": "p-1", "number": "PAR-001",
                 "expirationDate": "2027-04-05", "stock": 10}]

    def list_areas(self):
        self.calls.append("areas")
        return [{"id": "a-1", "name": "Emergencia"}]

    def list_movements(self):
        self.calls.append("movements")
        return [{"id": "m-1", "type": "entry", "productId": "p-1", "quantity": 10,
                 "date": "2026-10-30", "reason": "Compra", "stockBefore": 0,
                 "stockAfter": 10, "lotId": "l-1", "lotNumber": "PAR-001",
                 "expirationDate": "2027-04-05", "areaId": None}]


ROUTES = {
    "/api/products": "products",
    "/api/categories": "categories",
    "/api/lots": "lots",
    "/api/areas": "areas",
    "/api/movements": "movements",
}


@pytest.fixture
def setup() -> Iterator[tuple[TestClient, FakeService]]:
    app = create_app()
    service = FakeService()
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, jwt_secret_key=SECRET)
    app.dependency_overrides[get_inventory_read_service] = lambda: service
    with TestClient(app) as client:
        yield client, service


def headers(*, role: str = ROLE, expired: bool = False) -> dict[str, str]:
    now = datetime.now(UTC) - timedelta(hours=2) if expired else None
    token = create_access_token(subject="user-1", role=role, secret_key=SECRET,
                                expires_minutes=30, now=now)
    return {"Authorization": "Bearer " + token}


@pytest.mark.parametrize("route,method", list(ROUTES.items()))
def test_cada_get_requiere_autenticacion(setup, route: str, method: str) -> None:
    client, service = setup
    response = client.get(route)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert isinstance(response.json()["detail"], str)
    assert service.calls == []


@pytest.mark.parametrize("route,method", list(ROUTES.items()))
def test_cada_get_rechaza_rol_insuficiente(setup, route: str, method: str) -> None:
    client, service = setup
    response = client.get(route, headers=headers(role="Visitante"))
    assert response.status_code == 403
    assert service.calls == []


@pytest.mark.parametrize("route,method", list(ROUTES.items()))
def test_cada_get_acepta_jwt_valido_y_respeta_respuesta_angular(setup, route: str, method: str) -> None:
    client, service = setup
    response = client.get(route, headers=headers())
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1
    assert service.calls == [method]
    if method == "products":
        p = response.json()[0]
        assert p["unitPrice"] == 0.5 and p["active"] is False
        assert "unit_price" not in p and p["expirationDate"] is None
    elif method == "movements":
        m = response.json()[0]
        assert m["stockBefore"] == 0 and m["stockAfter"] == 10
        assert m["date"] == "2026-10-30" and "stock_before" not in m
    elif method == "lots":
        assert response.json()[0]["expirationDate"] == "2027-04-05"


@pytest.mark.parametrize("route", ROUTES)
def test_token_alterado_ni_siquiera_llama_servicio(setup, route: str) -> None:
    client, service = setup
    assert client.get(route, headers={"Authorization": "Bearer invalido"}).status_code == 401
    assert service.calls == []


def test_token_expirado_rechazado_antes_de_servicio(setup) -> None:
    client, service = setup
    assert client.get("/api/products", headers=headers(expired=True)).status_code == 401
    assert service.calls == []


def test_endpoint_sin_token_no_requiere_configuracion_db(setup) -> None:
    client, service = setup
    assert client.get("/api/categories").status_code == 401
    assert service.calls == []


def test_dependencia_real_sin_db_configurada_devuelve_503_sin_detalles(setup) -> None:
    client, _ = setup
    client.app.dependency_overrides.pop(get_inventory_read_service)
    # Evita que las variables de entorno reales intervengan en el resultado.
    client.app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, jwt_secret_key=SECRET,
        db_server="", db_name="", db_user="", db_password="",
    )
    response = client.get("/api/products", headers=headers())
    assert response.status_code == 503
    assert response.json() == {"detail": "El servicio de inventario no está disponible en este momento."}


def test_error_conexion_sql_no_expone_credenciales(setup) -> None:
    client, _ = setup

    class Broken:
        def list_products(self):
            raise DatabaseConnectionError("PWD=secreto-local; error interno")

    client.app.dependency_overrides[get_inventory_read_service] = lambda: Broken()
    response = client.get("/api/products", headers=headers())
    assert response.status_code == 503
    assert "PWD=" not in response.text
    assert "secreto-local" not in response.text


def test_falta_de_clave_jwt_devuelve_500_antes_de_llegar_al_servicio(setup) -> None:
    client, service = setup
    client.app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, jwt_secret_key="",
    )
    response = client.get("/api/products", headers=headers())
    assert response.status_code == 500
    assert service.calls == []
    assert "jwt_secret_key" not in response.text.lower()


def test_health_es_publico_y_opera_sin_sql(setup) -> None:
    client, service = setup
    assert client.get("/health").status_code == 200
    assert service.calls == []


def test_cors_para_angular_y_autorizacion_bearer(setup) -> None:
    client, _ = setup
    response = client.options("/api/products", headers={
        "Origin": "http://localhost:4200",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization",
    })
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:4200"


def test_openapi_conserva_los_get_y_registra_escrituras_reales(setup) -> None:
    client, _ = setup
    doc = client.get("/openapi.json").json()
    for route in ROUTES:
        assert "get" in doc["paths"][route]
        if route in ("/api/products", "/api/categories", "/api/movements"):
            assert "post" in doc["paths"][route]
        else:
            assert "post" not in doc["paths"][route]
    assert "post" in doc["paths"]["/api/auth/login"]
    assert "BearerJWT" in doc["components"]["securitySchemes"]


def test_post_movimientos_ahora_exige_token_y_escrituras_exigen_token(setup) -> None:
    client, _ = setup
    assert client.post("/api/movements", json={}).status_code == 401
    for route in ("/api/products", "/api/categories"):
        assert client.post(route, json={}).status_code == 401
