"""Pruebas de la estructura inicial: salud y CORS."""

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health_responde_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "API Inventario Hospital San Gabriel"
    assert body["version"] == "0.1.0"


def test_cors_permite_origen_de_angular() -> None:
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:4200",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:4200"
    assert "authorization" in response.headers["access-control-allow-headers"].lower()


def test_cors_rechaza_origen_desconocido() -> None:
    response = client.options(
        "/health",
        headers={
            "Origin": "http://origen-no-permitido.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert "access-control-allow-origin" not in response.headers


def test_api_de_inventario_requiere_token() -> None:
    assert client.get("/api/products").status_code == 401
    assert client.get("/api/movements").status_code == 401
