"""Pruebas de los schemas de inicio de sesión y usuario autenticado."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.schemas.auth import (
    LoginRequest,
    LoginResponse,
    UserRole,
)


def error_en(excinfo: pytest.ExceptionInfo[ValidationError], campo: str) -> dict:
    return next(e for e in excinfo.value.errors() if e["loc"] == (campo,))


def test_login_valido_recorta_el_correo() -> None:
    credenciales = LoginRequest.model_validate(
        {"email": "  hans.orellana@sgabriel.pe  ", "password": "SanGabriel2026!"}
    )

    assert credenciales.email == "hans.orellana@sgabriel.pe"
    assert credenciales.password == "SanGabriel2026!"


@pytest.mark.parametrize(
    "correo",
    [
        "",
        "   ",
        "sin-arroba",
        "a@",
        "@sgabriel.pe",
        "a b@sgabriel.pe",
        "a..b@sgabriel.pe",
        "a@-sgabriel.pe",
        "a@sgabriel..pe",
        "a@sgabriel.pe.",
        "a@" + "b" * 64 + ".pe",
        "a" * 65 + "@sgabriel.pe",
    ],
)
def test_correo_invalido_se_rechaza(correo: str) -> None:
    with pytest.raises(ValidationError) as excinfo:
        LoginRequest.model_validate({"email": correo, "password": "clave"})

    assert "correo" in error_en(excinfo, "email")["msg"]


@pytest.mark.parametrize(
    "correo", ["hans.orellana@sgabriel.pe", "a@b", "usuario+etiqueta@dominio.com"]
)
def test_correos_que_el_frontend_admite(correo: str) -> None:
    assert LoginRequest.model_validate({"email": correo, "password": "clave"}).email == correo


@pytest.mark.parametrize("password", ["", "   ", "\t\n"])
def test_password_vacia_o_solo_espacios_se_rechaza(password: str) -> None:
    with pytest.raises(ValidationError) as excinfo:
        LoginRequest.model_validate({"email": "a@b.pe", "password": password})

    assert error_en(excinfo, "password")["loc"] == ("password",)


def test_password_conserva_espacios_internos_y_exteriores() -> None:
    clave = "  clave con espacios  "
    assert LoginRequest.model_validate({"email": "a@b.pe", "password": clave}).password == clave


def test_password_admite_hasta_200_caracteres() -> None:
    clave = "x" * 200
    assert LoginRequest.model_validate({"email": "a@b.pe", "password": clave}).password == clave

    with pytest.raises(ValidationError) as excinfo:
        LoginRequest.model_validate({"email": "a@b.pe", "password": "x" * 201})

    assert "hasta 200" in error_en(excinfo, "password")["msg"]


def test_login_rechaza_campos_extra() -> None:
    with pytest.raises(ValidationError) as excinfo:
        LoginRequest.model_validate({"email": "a@b.pe", "password": "clave", "role": "admin"})

    assert excinfo.value.errors()[0]["type"] == "extra_forbidden"


def test_rol_admite_solo_el_valor_de_la_interfaz() -> None:
    assert UserRole.RESPONSABLE_ALMACEN.value == "Responsable de almacén"

    with pytest.raises(ValidationError):
        LoginResponse.model_validate(
            {
                "accessToken": "token",
                "user": {"id": "u1", "name": "Hans", "email": "a@b.pe", "role": "Administrador"},
            }
        )


def test_respuesta_de_login_usa_camel_case() -> None:
    respuesta = LoginResponse.model_validate(
        {
            "accessToken": "token-de-prueba",
            "user": {
                "id": "user-1",
                "name": "Hans Orellana",
                "email": "hans.orellana@sgabriel.pe",
                "role": "Responsable de almacén",
            },
        }
    )

    cuerpo = respuesta.model_dump(mode="json")

    assert set(cuerpo) == {"accessToken", "user"}
    assert set(cuerpo["user"]) == {"id", "name", "email", "role"}
    assert cuerpo["accessToken"] == "token-de-prueba"
    assert cuerpo["user"]["role"] == "Responsable de almacén"


def test_token_vacio_se_rechaza() -> None:
    with pytest.raises(ValidationError):
        LoginResponse.model_validate(
            {
                "accessToken": "   ",
                "user": {
                    "id": "u1",
                    "name": "Hans",
                    "email": "a@b.pe",
                    "role": "Responsable de almacén",
                },
            }
        )
