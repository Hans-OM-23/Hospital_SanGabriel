"""Etapa 9: contratos HTTP, JWT, validación y errores de negocio sin SQL."""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.apis.inventory_api import get_inventory_write_service
from backend.core.config import Settings, get_settings
from backend.core.exceptions import (
    DatabaseConnectionError,
    InventoryConflictError,
    InventoryInvalidReferenceError,
    InventoryNotFoundError,
)
from backend.core.security import create_access_token
from backend.main import create_app

SECRET = "clave-solo-para-tests-" + "9" * 64
CAT_ID = str(uuid4())
PRODUCT_ID = str(uuid4())


class FakeService:
    def __init__(self):
        self.calls: list[tuple[str, object]] = []
        self.error = None

    def maybe_raise(self):
        if self.error:
            raise self.error

    def create_category(self, data):
        self.calls.append(("create_category", data))
        self.maybe_raise()
        return {"id": CAT_ID, "name": data.name, "description": data.description, "active": True}

    def _product(self, data):
        return {**data.model_dump(mode="json"), "id": PRODUCT_ID, "active": True}

    def create_product(self, data):
        self.calls.append(("create_product", data))
        self.maybe_raise()
        return self._product(data)

    def update_product(self, product_id, data):
        self.calls.append(("update_product", product_id, data))
        self.maybe_raise()
        return self._product(data)

    def set_product_status(self, product_id, data):
        self.calls.append(("set_product_status", product_id, data))
        self.maybe_raise()


@pytest.fixture
def setup() -> Iterator[tuple[TestClient, FakeService]]:
    app = create_app()
    fake = FakeService()
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, jwt_secret_key=SECRET)
    app.dependency_overrides[get_inventory_write_service] = lambda: fake
    with TestClient(app) as client:
        yield client, fake


def token(*, role="Responsable de almacén") -> dict[str, str]:
    return {
        "Authorization": "Bearer " + create_access_token(
            subject="user-1", role=role, secret_key=SECRET, expires_minutes=30
        )
    }


def product_input(**changes):
    data = {
        "code": "med-001", "name": "Paracetamol", "description": "Tabletas",
        "categoryId": CAT_ID, "unit": "Tableta", "unitPrice": 0.5,
        "minStock": 5, "tracksExpiration": False, "expirationDate": None,
    }
    data.update(changes)
    return data


@pytest.mark.parametrize(
    "verb,path,payload",
    [
        ("post", "/api/categories", {"name": "Medicamentos", "description": "Tratamientos"}),
        ("post", "/api/products", product_input()),
        ("put", f"/api/products/{PRODUCT_ID}", product_input()),
        ("patch", f"/api/products/{PRODUCT_ID}/status", {"active": False}),
    ],
)
def test_cada_escritura_sin_token_401_y_con_rol_incorrecto_403(setup, verb, path, payload):
    client, service = setup
    assert getattr(client, verb)(path, json=payload).status_code == 401
    assert getattr(client, verb)(path, json=payload, headers=token(role="Visitante")).status_code == 403
    assert service.calls == []


def test_post_categoria_201_con_json_correcto(setup):
    client, service = setup
    res = client.post("/api/categories", headers=token(), json={
        "name": "  Medicamentos ", "description": "  Tratamientos ",
    })
    assert res.status_code == 201
    assert res.json() == {
        "id": CAT_ID, "name": "Medicamentos", "description": "Tratamientos", "active": True
    }
    assert service.calls[0][1].name == "Medicamentos"


def test_post_producto_201_normaliza_y_devuelve_camel_case(setup):
    client, service = setup
    res = client.post("/api/products", headers=token(), json=product_input())
    assert res.status_code == 201
    body = res.json()
    assert body["id"] == PRODUCT_ID and body["categoryId"] == CAT_ID
    assert body["code"] == "MED-001" and body["unitPrice"] == 0.5
    assert body["active"] is True and "unit_price" not in body
    assert service.calls[0][1].code == "MED-001"


def test_put_producto_200_y_patch_204_sin_cuerpo(setup):
    client, service = setup
    res = client.put(f"/api/products/{PRODUCT_ID}", headers=token(),
                     json=product_input(name="Paracetamol actualizado"))
    assert res.status_code == 200
    assert res.json()["name"] == "Paracetamol actualizado"
    assert service.calls[-1][1] == PRODUCT_ID
    patch = client.patch(f"/api/products/{PRODUCT_ID}/status", headers=token(),
                         json={"active": False})
    assert patch.status_code == 204 and patch.content == b""
    assert service.calls[-1][2].active is False


@pytest.mark.parametrize(
    "verb,path,payload,field",
    [
        ("post", "/api/categories", {"name": "", "description": ""}, "name"),
        ("post", "/api/products", product_input(unitPrice=-1), "unitPrice"),
        ("post", "/api/products", product_input(categoryId=""), "categoryId"),
        ("put", f"/api/products/{PRODUCT_ID}", product_input(tracksExpiration=True), "expirationDate"),
        ("patch", f"/api/products/{PRODUCT_ID}/status", {"active": "false"}, "active"),
    ],
)
def test_schemas_rechazan_input_invalido_sin_repositorio(setup, verb, path, payload, field):
    client, service = setup
    response = getattr(client, verb)(path, headers=token(), json=payload)
    assert response.status_code == 422
    assert any(err["loc"][-1] == field for err in response.json()["detail"])
    assert service.calls == []


@pytest.mark.parametrize(
    "error,status_code,body",
    [
        (InventoryConflictError("Código duplicado.", field="code"),
         409, {"detail": {"field": "code", "message": "Código duplicado."}}),
        (InventoryConflictError("Categoría duplicada.", field="name"),
         409, {"detail": {"field": "name", "message": "Categoría duplicada."}}),
        (InventoryInvalidReferenceError("Categoría inactiva.", field="categoryId"),
         422, {"detail": {"field": "categoryId", "message": "Categoría inactiva."}}),
        (InventoryNotFoundError("No existe."), 404, {"detail": "No existe."}),
    ],
)
def test_errores_dominio_se_traducen_al_contrato_angular(setup, error, status_code, body):
    client, service = setup
    service.error = error
    res = client.post("/api/products", headers=token(), json=product_input())
    assert res.status_code == status_code and res.json() == body


def test_error_odbc_no_expone_datos_del_servidor(setup):
    client, service = setup
    service.error = DatabaseConnectionError("PWD=secreto prueba @localhost")
    response = client.post("/api/categories", headers=token(), json={
        "name": "Nueva", "description": "Descripción"
    })
    assert response.status_code == 503
    assert "secreto" not in response.text
    assert response.json() == {"detail": "El servicio de inventario no está disponible en este momento."}


def test_openapi_incluye_cuatro_mutaciones_y_preserva_get(setup):
    client, _ = setup
    paths = client.get("/openapi.json").json()["paths"]
    assert "post" in paths["/api/products"]
    assert "post" in paths["/api/categories"]
    assert "get" in paths["/api/products"] and "get" in paths["/api/categories"]
    assert "put" in paths["/api/products/{product_id}"]
    assert "patch" in paths["/api/products/{product_id}/status"]
    assert "post" not in paths["/api/movements"]


def test_cors_permiso_para_metodos_angular(setup):
    client, _ = setup
    r = client.options("/api/products", headers={
        "Origin": "http://localhost:4200",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type",
    })
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:4200"


def test_dependencia_real_sin_sql_responde_503(setup):
    client, _ = setup
    client.app.dependency_overrides.pop(get_inventory_write_service)
    client.app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, jwt_secret_key=SECRET, db_server="", db_name="", db_user="", db_password="",
    )
    response = client.post("/api/categories", headers=token(), json={
        "name": "Nueva", "description": "Descripción"
    })
    assert response.status_code == 503
