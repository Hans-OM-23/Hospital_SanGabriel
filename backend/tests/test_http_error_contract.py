"""Etapa 12: contrato HTTP, errores seguros y compatibilidad con Angular.

Las pruebas no abren conexiones con SQL Server. Las operaciones autorizadas
que necesiten datos utilizan dependencias sustitutas dentro de pytest.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from backend.apis.auth_api import get_auth_service
from backend.apis.inventory_api import (
    get_inventory_movement_service, get_inventory_write_service,
)
from backend.core.config import Settings, get_settings
from backend.core.exceptions import DatabaseConnectionError, InventoryConflictError
from backend.core.security import create_access_token
from backend.main import create_app
from backend.apis.error_handlers import public_validation_errors

SECRET = "secret-exclusivo-pruebas-etapa12-" + "x" * 48
PRIVATE = "CLAVE_NO_DEBE_APARECER_985123_PRIVATE"


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, jwt_secret_key=SECRET,
        db_server="", db_name="", db_user="", db_password="",
    )
    # FastAPI resuelve dependencias antes de validar el cuerpo: sustituimos
    # los servicios para probar errores 422 sin abrir SQL Server.
    for dependency in (get_auth_service, get_inventory_write_service, get_inventory_movement_service):
        app.dependency_overrides[dependency] = lambda: object()
    with TestClient(app) as test_client:
        yield test_client


def bearer(role: str = "Responsable de almacén") -> dict[str, str]:
    token = create_access_token(
        subject="usuario-tests-12", role=role, secret_key=SECRET, expires_minutes=20
    )
    return {"Authorization": f"Bearer {token}"}


def product_input(**changes: object) -> dict[str, object]:
    data: dict[str, object] = {
        "code": "MED-001", "name": "Paracetamol", "description": "Tabletas",
        "categoryId": "categoria-1", "unit": "Tableta", "unitPrice": 1.5,
        "minStock": 2, "tracksExpiration": False, "expirationDate": None,
    }
    data.update(changes)
    return data


def movement_input(**changes: object) -> dict[str, object]:
    data: dict[str, object] = {
        "type": "entry", "productId": "producto-1", "quantity": 2,
        "date": "2026-01-01", "reason": "Compra", "lotNumber": "LOTE-A",
        "expirationDate": "2028-01-01",
    }
    data.update(changes)
    return data


def assert_private_data_absent(response) -> None:
    assert PRIVATE not in response.text
    if isinstance(response.json()["detail"], list):
        for error in response.json()["detail"]:
            assert set(error) == {"loc", "msg", "type"}
            assert "input" not in error and "ctx" not in error and "url" not in error
            assert isinstance(error["loc"], list)
            assert isinstance(error["msg"], str)


# Estos 11 métodos/rutas son exactamente los de frontend/docs/API-CONTRACT.md.
EXPECTED_METHODS = {
    ("post", "/api/auth/login"),
    ("get", "/api/products"), ("post", "/api/products"),
    ("put", "/api/products/{product_id}"),
    ("patch", "/api/products/{product_id}/status"),
    ("get", "/api/categories"), ("post", "/api/categories"),
    ("get", "/api/lots"), ("get", "/api/areas"),
    ("get", "/api/movements"), ("post", "/api/movements"),
}


def test_openapi_registra_los_11_metodos_del_contrato(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    actual = {
        (method, path)
        for path, spec in paths.items() for method in spec
        if method in {"get", "post", "put", "patch"} and path.startswith("/api/")
    }
    assert actual == EXPECTED_METHODS


@pytest.mark.parametrize("method,path", sorted(EXPECTED_METHODS - {("post", "/api/auth/login")}))
def test_todas_las_operaciones_de_inventario_exigen_bearer(
    client: TestClient, method: str, path: str,
) -> None:
    real_path = path.replace("{product_id}", "producto-1")
    response = client.request(method.upper(), real_path)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert set(response.json()) == {"detail"}


@pytest.mark.parametrize("method,path", [
    ("get", "/api/products"), ("get", "/api/categories"),
    ("get", "/api/lots"), ("get", "/api/areas"), ("get", "/api/movements"),
    ("post", "/api/categories"), ("post", "/api/products"),
    ("put", "/api/products/producto-1"),
    ("patch", "/api/products/producto-1/status"),
    ("post", "/api/movements"),
])
def test_rol_incorrecto_es_403_y_no_401(client: TestClient, method: str, path: str) -> None:
    response = client.request(method.upper(), path, headers=bearer("Visitante"))
    assert response.status_code == 403
    assert "permisos" in response.json()["detail"]


def test_login_password_de_tipo_incorrecto_no_se_refleja(client: TestClient) -> None:
    response = client.post("/api/auth/login", json={
        "email": "personal@hospital.example", "password": {"clavePrivada": PRIVATE}
    })
    assert response.status_code == 422
    assert_private_data_absent(response)
    assert response.json()["detail"][0]["loc"] == ["body", "password"]
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"


def test_login_con_campo_extra_no_devuelve_su_contenido(client: TestClient) -> None:
    response = client.post("/api/auth/login", json={
        "email": "personal@hospital.example", "password": "claveValida",
        "propiedadDesconocida": PRIVATE,
    })
    assert response.status_code == 422
    assert_private_data_absent(response)
    errors = response.json()["detail"]
    assert errors[0] == {
        "loc": ["body", "propiedadDesconocida"],
        "msg": "Este campo no está permitido.",
        "type": "extra_forbidden",
    }


def test_login_error_json_mal_formado_no_repite_fragmento(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login", content='{"password": "' + PRIVATE + '",',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert_private_data_absent(response)
    assert response.json()["detail"][0] == {
        "loc": ["body"], "msg": "El cuerpo JSON no tiene un formato válido.", "type": "json_invalid",
    }


@pytest.mark.parametrize("payload,field", [
    (product_input(unitPrice=-2), "unitPrice"),
    (product_input(minStock="no"), "minStock"),
    (product_input(tracksExpiration="false"), "tracksExpiration"),
    (product_input(categoryId=""), "categoryId"),
    (product_input(code=""), "code"),
])
def test_422_producto_respeta_camel_case_y_no_refleja_datos(
    client: TestClient, payload: dict, field: str,
) -> None:
    payload["datoPrivado"] = PRIVATE
    response = client.post("/api/products", json=payload, headers=bearer())
    assert response.status_code == 422
    assert_private_data_absent(response)
    assert any(err["loc"][-1] == field for err in response.json()["detail"])


@pytest.mark.parametrize("payload,field", [
    (movement_input(quantity=0), "quantity"),
    (movement_input(reason="No es motivo válido"), "reason"),
    (movement_input(lotNumber=None), "lotNumber"),
    (movement_input(expirationDate="2030-02-31"), "expirationDate"),
])
def test_422_movimiento_respeta_camel_case(
    client: TestClient, payload: dict, field: str,
) -> None:
    response = client.post("/api/movements", json=payload, headers=bearer())
    assert response.status_code == 422
    assert_private_data_absent(response)
    assert any(err["loc"][-1] == field for err in response.json()["detail"])


def test_faltan_campos_error_en_espanol_sin_eco(client: TestClient) -> None:
    response = client.post("/api/auth/login", json={})
    assert response.status_code == 422
    assert_private_data_absent(response)
    assert {e["loc"][-1] for e in response.json()["detail"]} == {"email", "password"}
    assert all(e["msg"] == "Este campo es obligatorio." for e in response.json()["detail"])


def test_404_y_405_tienen_formato_detail_en_espanol(client: TestClient) -> None:
    missing = client.get("/api/ruta-que-no-existe")
    assert missing.status_code == 404
    assert missing.json() == {"detail": "La ruta solicitada no existe."}
    wrong_method = client.delete("/api/auth/login")
    assert wrong_method.status_code == 405
    assert wrong_method.json() == {
        "detail": "El método HTTP no está permitido para esta ruta."
    }
    assert "POST" in wrong_method.headers["allow"]
    assert wrong_method.headers["cache-control"] == "no-store"


def test_validacion_no_devuelve_ctx_input_ni_mensajes_desconocidos() -> None:
    errors = public_validation_errors([{
        "type": "error_futuro", "loc": ("body", "password"),
        "msg": PRIVATE, "input": PRIVATE, "ctx": {"raw": PRIVATE},
    }])
    assert errors == [{
        "loc": ["body", "password"], "msg": "El valor enviado no es válido.",
        "type": "error_futuro",
    }]


def test_validacion_no_devuelve_mas_de_30_errores() -> None:
    errors = [{"type": "missing", "loc": ("body", f"campo{i}"), "msg": "Field required"}
              for i in range(80)]
    result = public_validation_errors(errors)
    assert len(result) == 30
    assert result[-1]["loc"] == ["body", "campo29"]


def test_error_de_domino_conserva_formato_angular(client: TestClient) -> None:
    # Se inyecta el error después de autenticación, sin abrir SQL Server.
    from backend.apis.inventory_api import get_inventory_write_service

    class FailingService:
        def create_category(self, _data):
            raise InventoryConflictError("El nombre ya existe.", field="name")

    client.app.dependency_overrides[get_inventory_write_service] = lambda: FailingService()
    response = client.post("/api/categories", json={"name": "Medicamentos", "description": ""}, headers=bearer())
    assert response.status_code == 409
    assert response.json() == {"detail": {"field": "name", "message": "El nombre ya existe."}}


def test_error_sql_sigue_oculto_bajo_503(client: TestClient) -> None:
    from backend.apis.inventory_api import get_inventory_read_service

    class FailingRead:
        def list_products(self):
            raise DatabaseConnectionError("PWD=" + PRIVATE)

    client.app.dependency_overrides[get_inventory_read_service] = lambda: FailingRead()
    response = client.get("/api/products", headers=bearer())
    assert response.status_code == 503
    assert response.json() == {
        "detail": "El servicio de inventario no está disponible en este momento."
    }
    assert PRIVATE not in response.text


def test_respuesta_health_sigue_publica(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()


def test_cors_de_angular_se_conserva(client: TestClient) -> None:
    response = client.options("/api/products", headers={
        "Origin": "http://localhost:4200",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type",
    })
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:4200"
