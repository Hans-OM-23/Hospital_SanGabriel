"""Pruebas de los tipos y la configuración compartida de los schemas."""

from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace

import pytest
from pydantic import BaseModel, ValidationError

from backend.schemas.common import (
    MAX_SQL_INT,
    ApiInput,
    ApiResponse,
    ISODate,
    StrictBool,
    entero,
    precio,
    texto_obligatorio,
)
from backend.schemas.product import ProductCreate, ProductResponse


class ModeloFecha(BaseModel):
    fecha: ISODate


@pytest.mark.parametrize("texto", ["2026-10-31", "2024-02-29", " 2026-01-01 "])
def test_fecha_iso_acepta_calendario_valido(texto: str) -> None:
    assert ModeloFecha(fecha=texto).fecha == date.fromisoformat(texto.strip())


@pytest.mark.parametrize(
    "texto",
    [
        "31-10-2026",
        "2026-2-3",
        "2026/10/31",
        "2026-10-31T00:00:00",
        "2026-10-31 08:00",
        "2026-02-30",
        "2026-13-01",
        "20261031",
        "",
        "   ",
    ],
)
def test_fecha_iso_rechaza_formatos_y_fechas_inexistentes(texto: str) -> None:
    with pytest.raises(ValidationError) as excinfo:
        ModeloFecha(fecha=texto)

    assert excinfo.value.errors()[0]["loc"] == ("fecha",)


def test_fecha_iso_rechaza_datetime_aunque_represente_medianoche() -> None:
    with pytest.raises(ValidationError):
        ModeloFecha(fecha=datetime(2026, 10, 31))


def test_fecha_iso_serializa_sin_hora_ni_zona() -> None:
    assert ModeloFecha(fecha="2026-10-31").model_dump(mode="json") == {"fecha": "2026-10-31"}


def test_texto_obligatorio_recorta_y_convierte_a_mayusculas() -> None:
    Codigo = texto_obligatorio(
        max_length=10,
        mensaje_requerido="Requerido.",
        mensaje_longitud="Máximo 10.",
        mayusculas=True,
    )

    class Modelo(BaseModel):
        codigo: Codigo

    assert Modelo(codigo="  ab-1  ").codigo == "AB-1"


def test_texto_obligatorio_rechaza_solo_espacios_y_exceso_de_longitud() -> None:
    Codigo = texto_obligatorio(
        max_length=5,
        mensaje_requerido="Requerido.",
        mensaje_longitud="Máximo 5.",
    )

    class Modelo(BaseModel):
        codigo: Codigo

    with pytest.raises(ValidationError, match="Requerido"):
        Modelo(codigo="   ")
    with pytest.raises(ValidationError, match="Máximo 5"):
        Modelo(codigo="123456")


def test_entero_estricto_rechaza_booleanos_decimales_y_cadenas() -> None:
    Numero = entero(minimo=1, maximo=MAX_SQL_INT, mensaje="Entero positivo.")

    class Modelo(BaseModel):
        valor: Numero

    for invalido in (True, 1.5, "2", 0, -1, MAX_SQL_INT + 1):
        with pytest.raises(ValidationError):
            Modelo(valor=invalido)

    assert Modelo(valor=MAX_SQL_INT).valor == MAX_SQL_INT


def test_precio_rechaza_cero_negativos_exceso_de_decimales_y_no_finitos() -> None:
    Precio = precio(
        mensaje="Mayor que cero.",
        mensaje_decimales="Dos decimales.",
        mensaje_maximo="Demasiado grande.",
    )

    class Modelo(BaseModel):
        valor: Precio

    for invalido in (0, -1, 1.234, float("nan"), float("inf"), True, "5"):
        with pytest.raises(ValidationError):
            Modelo(valor=invalido)

    assert Modelo(valor=0.5).valor == 0.5
    assert Modelo(valor=28).valor == 28.0


def test_booleano_estricto_no_acepta_texto_ni_numeros() -> None:
    class Modelo(BaseModel):
        activo: StrictBool

    for invalido in ("true", 1, 0, None):
        with pytest.raises(ValidationError):
            Modelo(activo=invalido)


def test_entrada_rechaza_propiedades_fuera_del_contrato() -> None:
    with pytest.raises(ValidationError) as excinfo:
        ProductCreate.model_validate(
            {
                "id": "p-1",
                "code": "MED-001",
                "name": "Paracetamol",
                "description": "Tabletas",
                "categoryId": "cat-med",
                "unit": "Tableta",
                "unitPrice": 0.5,
                "minStock": 0,
                "tracksExpiration": False,
                "expirationDate": None,
            }
        )

    assert excinfo.value.errors()[0]["type"] == "extra_forbidden"
    assert excinfo.value.errors()[0]["loc"] == ("id",)


def test_salida_ignora_columnas_extra_de_la_base() -> None:
    fila = SimpleNamespace(
        id="p-1",
        code="MED-001",
        name="Paracetamol",
        description="Tabletas",
        category_id="cat-med",
        unit="Tableta",
        unit_price=0.5,
        min_stock=0,
        tracks_expiration=False,
        expiration_date=None,
        active=True,
        created_at="2026-01-01",
    )

    producto = ProductResponse.model_validate(fila)

    assert producto.category_id == "cat-med"
    assert "created_at" not in producto.model_dump()


def test_entrada_acepta_nombres_python_y_alias_camel_case() -> None:
    por_alias = ProductCreate.model_validate(
        {
            "code": "MED-001",
            "name": "Paracetamol",
            "description": "Tabletas",
            "categoryId": "cat-med",
            "unit": "Tableta",
            "unitPrice": 0.5,
            "minStock": 0,
            "tracksExpiration": False,
            "expirationDate": None,
        }
    )
    por_nombre = ProductCreate(
        code="MED-001",
        name="Paracetamol",
        description="Tabletas",
        category_id="cat-med",
        unit="Tableta",
        unit_price=0.5,
        min_stock=0,
        tracks_expiration=False,
        expiration_date=None,
    )

    assert por_alias == por_nombre


def test_configuracion_base_de_entrada_y_salida() -> None:
    assert ApiInput.model_config["extra"] == "forbid"
    assert ApiResponse.model_config["extra"] == "ignore"
    assert ApiInput.model_config["serialize_by_alias"] is True
    assert ApiInput.model_config["validate_by_name"] is True
