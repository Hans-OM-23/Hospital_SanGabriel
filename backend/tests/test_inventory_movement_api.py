"""Endpoint POST /api/movements: contrato JSON y autorización JWT."""
from __future__ import annotations

from datetime import timedelta
from backend.schemas.movement import fecha_hoy_peru
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.apis.inventory_api import get_inventory_movement_service
from backend.core.config import Settings, get_settings
from backend.core.exceptions import (
    DatabaseConnectionError, InventoryConflictError, InventoryInvalidReferenceError,
)
from backend.core.security import create_access_token
from backend.main import create_app

SECRET = "clave-solo-tests-" + "7" * 64
PRODUCT = str(uuid4())
LOT = str(uuid4())
AREA = str(uuid4())
MOVEMENT = str(uuid4())


class FakeMovementService:
    def __init__(self):
        self.calls = []
        self.error = None

    def register_movement(self, data):
        self.calls.append(data)
        if self.error:
            raise self.error
        is_entry = data.type.value == "entry"
        return {
            "id": MOVEMENT, "type": data.type.value, "productId": PRODUCT,
            "quantity": data.quantity, "date": data.date.isoformat(), "reason": data.reason,
            "stockBefore": 10, "stockAfter": 10 + (data.quantity if is_entry else -data.quantity),
            "lotId": LOT, "lotNumber": "PAR-027", "expirationDate": "2028-10-31",
            "areaId": None if is_entry else AREA,
        }


@pytest.fixture
def setup():
    app = create_app()
    fake = FakeMovementService()
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, jwt_secret_key=SECRET
    )
    app.dependency_overrides[get_inventory_movement_service] = lambda: fake
    with TestClient(app) as client:
        yield client, fake


def authorization(role="Responsable de almacén"):
    return {"Authorization": "Bearer " + create_access_token(
        subject="user-1", role=role, secret_key=SECRET, expires_minutes=30
    )}


def entry(**changes):
    payload = {
        "type": "entry", "productId": PRODUCT, "quantity": 3,
        "date": "2026-10-31", "reason": "Compra", "lotNumber": "par-027",
        "expirationDate": "2028-10-31",
    }
    payload.update(changes)
    return payload


def exit_payload(**changes):
    payload = {
        "type": "exit", "productId": PRODUCT, "quantity": 2,
        "date": "2026-10-31", "reason": "Reposición de insumos",
        "lotId": LOT, "areaId": AREA,
    }
    payload.update(changes)
    return payload


@pytest.mark.parametrize("data", [entry(), exit_payload()])
def test_sin_token_401_o_rol_invalido_403(setup, data):
    client, fake = setup
    assert client.post("/api/movements", json=data).status_code == 401
    assert client.post("/api/movements", headers=authorization("Visitante"), json=data).status_code == 403
    assert fake.calls == []


def test_entrada_respuesta_201_camel_case_con_saldo_total(setup):
    client, fake = setup
    response = client.post("/api/movements", headers=authorization(), json=entry())
    assert response.status_code == 201
    assert response.json() == {
        "id": MOVEMENT, "type": "entry", "productId": PRODUCT, "quantity": 3,
        "date": "2026-10-31", "reason": "Compra", "stockBefore": 10,
        "stockAfter": 13, "lotId": LOT, "lotNumber": "PAR-027",
        "expirationDate": "2028-10-31", "areaId": None,
    }
    assert fake.calls[0].lot_number == "PAR-027"


def test_salida_respuesta_201_con_area_y_saldo(setup):
    client, fake = setup
    response = client.post("/api/movements", headers=authorization(), json=exit_payload())
    assert response.status_code == 201
    assert response.json()["stockAfter"] == 8
    assert response.json()["areaId"] == AREA
    assert fake.calls[0].lot_id == LOT


@pytest.mark.parametrize("data,field", [
    (entry(quantity=0), "quantity"),
    (entry(quantity=1.5), "quantity"),
    (entry(reason="Otro"), "reason"),
    (entry(lotNumber="  "), "lotNumber"),
    (entry(areaId=AREA), "areaId"),
    (entry(expirationDate="2026-01-01"), "expirationDate"),
    (exit_payload(lotId=None), "lotId"),
    (exit_payload(areaId=None), "areaId"),
    (exit_payload(type="other"), "type"),
])
def test_entrada_invalida_422_sin_servicio(setup, data, field):
    client, fake = setup
    response = client.post("/api/movements", headers=authorization(), json=data)
    assert response.status_code == 422
    assert any(e["loc"][-1] == field for e in response.json()["detail"])
    assert fake.calls == []


def test_fecha_futura_rechazada_sin_servicio(setup):
    client, fake = setup
    future = (fecha_hoy_peru() + timedelta(days=1)).isoformat()
    response = client.post("/api/movements", headers=authorization(), json=entry(date=future))
    assert response.status_code == 422
    assert fake.calls == []


@pytest.mark.parametrize("error,status,body", [
    (InventoryConflictError("Stock insuficiente.", field="quantity"),
     409, {"detail": {"field": "quantity", "message": "Stock insuficiente."}}),
    (InventoryInvalidReferenceError("Área inválida.", field="areaId"),
     422, {"detail": {"field": "areaId", "message": "Área inválida."}}),
])
def test_errores_negocio_compatibles_con_angular(setup, error, status, body):
    client, fake = setup
    fake.error = error
    response = client.post("/api/movements", headers=authorization(), json=entry())
    assert response.status_code == status and response.json() == body


def test_error_base_no_revela_detalles_odbc(setup):
    client, fake = setup
    fake.error = DatabaseConnectionError("PWD=ultra-secreto localhost")
    response = client.post("/api/movements", headers=authorization(), json=entry())
    assert response.status_code == 503
    assert "ultra-secreto" not in response.text


def test_openapi_incluye_post_y_get_de_movimientos(setup):
    client, _ = setup
    paths = client.get("/openapi.json").json()["paths"]
    assert "post" in paths["/api/movements"]
    assert "get" in paths["/api/movements"]


def test_dependencia_real_sin_configuracion_devuelve_503(setup):
    client, _ = setup
    client.app.dependency_overrides.pop(get_inventory_movement_service)
    client.app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, jwt_secret_key=SECRET,
        db_server="", db_name="", db_user="", db_password="",
    )
    response = client.post("/api/movements", headers=authorization(), json=entry())
    assert response.status_code == 503
