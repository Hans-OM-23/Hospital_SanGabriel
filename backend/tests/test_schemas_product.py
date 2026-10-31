"""Pruebas de los schemas de productos."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.schemas.common import MAX_SQL_INT
from backend.schemas.product import (
    MEASUREMENT_UNITS,
    ProductCreate,
    ProductInput,
    ProductResponse,
    ProductStatusUpdate,
    ProductUpdate,
)

CAMPOS_ESPERADOS = {
    "code",
    "name",
    "description",
    "categoryId",
    "unit",
    "unitPrice",
    "minStock",
    "tracksExpiration",
    "expirationDate",
}


def payload(**cambios: object) -> dict[str, object]:
    base: dict[str, object] = {
        "code": "MED-001",
        "name": "Paracetamol 500 mg",
        "description": "Tabletas para uso hospitalario.",
        "categoryId": "cat-med",
        "unit": "Tableta",
        "unitPrice": 0.5,
        "minStock": 20,
        "tracksExpiration": True,
        "expirationDate": "2027-10-31",
    }
    base.update(cambios)
    return base


def error_en(excinfo: pytest.ExceptionInfo[ValidationError], campo: str) -> dict:
    return next(e for e in excinfo.value.errors() if e["loc"] == (campo,))


def test_producto_valido_normaliza_codigo_y_textos() -> None:
    producto = ProductInput.model_validate(
        payload(code="  med-001 ", name="  Paracetamol 500 mg  ", description="  Tabletas.  ")
    )

    assert producto.code == "MED-001"
    assert producto.name == "Paracetamol 500 mg"
    assert producto.description == "Tabletas."
    assert producto.category_id == "cat-med"
    assert producto.expiration_date.isoformat() == "2027-10-31"


def test_todas_las_unidades_del_formulario_son_validas() -> None:
    assert len(MEASUREMENT_UNITS) == 10
    for unidad in MEASUREMENT_UNITS:
        assert ProductInput.model_validate(payload(unit=unidad)).unit == unidad


def test_unidad_fuera_del_catalogo_se_rechaza_con_mensaje_en_espanol() -> None:
    with pytest.raises(ValidationError) as excinfo:
        ProductInput.model_validate(payload(unit="Galón"))

    assert "unidad de medida válida" in error_en(excinfo, "unit")["msg"]


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("code", "   "),
        ("name", ""),
        ("description", "   "),
        ("categoryId", ""),
        ("unit", ""),
    ],
)
def test_campos_obligatorios_vacios_se_rechazan(campo: str, valor: str) -> None:
    with pytest.raises(ValidationError) as excinfo:
        ProductInput.model_validate(payload(**{campo: valor}))

    assert excinfo.value.errors()[0]["loc"] == (campo,)


def test_longitudes_maximas_del_formulario() -> None:
    assert ProductInput.model_validate(payload(code="A" * 40)).code == "A" * 40
    assert ProductInput.model_validate(payload(name="A" * 160)).name == "A" * 160
    assert (
        ProductInput.model_validate(payload(description="A" * 1000)).description == "A" * 1000
    )

    for campo, valor in (
        ("code", "A" * 41),
        ("name", "A" * 161),
        ("description", "A" * 1001),
        ("categoryId", "A" * 101),
    ):
        with pytest.raises(ValidationError):
            ProductInput.model_validate(payload(**{campo: valor}))


@pytest.mark.parametrize(
    "precio_invalido", [0, -0.01, 1.234, 10_000_000_000.0, float("nan"), float("inf"), True]
)
def test_precio_unitario_invalido(precio_invalido: object) -> None:
    with pytest.raises(ValidationError) as excinfo:
        ProductInput.model_validate(payload(unitPrice=precio_invalido))

    assert error_en(excinfo, "unitPrice")["loc"] == ("unitPrice",)


def test_precio_unitario_admite_dos_decimales_y_limite_decimal_12_2() -> None:
    assert ProductInput.model_validate(payload(unitPrice=0.01)).unit_price == 0.01
    assert (
        ProductInput.model_validate(payload(unitPrice=9999999999.99)).unit_price
        == 9999999999.99
    )


@pytest.mark.parametrize("stock_invalido", [-1, 1.5, True, "5", MAX_SQL_INT + 1])
def test_stock_minimo_invalido(stock_invalido: object) -> None:
    with pytest.raises(ValidationError) as excinfo:
        ProductInput.model_validate(payload(minStock=stock_invalido))

    assert "stock mínimo" in error_en(excinfo, "minStock")["msg"]


def test_stock_minimo_admite_cero_y_el_maximo_de_sql_server() -> None:
    assert ProductInput.model_validate(payload(minStock=0)).min_stock == 0
    assert ProductInput.model_validate(payload(minStock=MAX_SQL_INT)).min_stock == MAX_SQL_INT


def test_control_de_vencimiento_debe_ser_booleano() -> None:
    for invalido in ("true", 1, 0, None):
        with pytest.raises(ValidationError) as excinfo:
            ProductInput.model_validate(payload(tracksExpiration=invalido))

        assert excinfo.value.errors()[0]["loc"] == ("tracksExpiration",)


def test_vencimiento_es_obligatorio_si_el_producto_lo_controla() -> None:
    with pytest.raises(ValidationError) as excinfo:
        ProductInput.model_validate(payload(tracksExpiration=True, expirationDate=None))

    assert "fecha de vencimiento" in error_en(excinfo, "expirationDate")["msg"]


def test_vencimiento_omitido_reporta_el_alias_camel_case() -> None:
    datos = payload(tracksExpiration=True)
    datos.pop("expirationDate")

    with pytest.raises(ValidationError) as excinfo:
        ProductInput.model_validate(datos)

    assert error_en(excinfo, "expirationDate")["loc"] == ("expirationDate",)


def test_vencimiento_se_descarta_si_el_producto_no_lo_controla() -> None:
    producto = ProductInput.model_validate(
        payload(tracksExpiration=False, expirationDate="2027-10-31")
    )

    assert producto.expiration_date is None


def test_vencimiento_admite_omitirse_sin_control() -> None:
    datos = payload(tracksExpiration=False)
    datos.pop("expirationDate")

    assert ProductInput.model_validate(datos).expiration_date is None


def test_vencimiento_debe_estar_en_formato_iso() -> None:
    with pytest.raises(ValidationError) as excinfo:
        ProductInput.model_validate(payload(expirationDate="31/10/2027"))

    assert error_en(excinfo, "expirationDate")["loc"] == ("expirationDate",)


def test_creacion_y_actualizacion_comparten_el_contrato() -> None:
    assert set(ProductCreate.model_json_schema()["properties"]) == CAMPOS_ESPERADOS
    assert set(ProductUpdate.model_json_schema()["properties"]) == CAMPOS_ESPERADOS
    assert issubclass(ProductUpdate, ProductInput)


def test_estado_de_producto_requiere_booleano() -> None:
    assert ProductStatusUpdate.model_validate({"active": False}).active is False

    with pytest.raises(ValidationError):
        ProductStatusUpdate.model_validate({"active": "false"})
    with pytest.raises(ValidationError):
        ProductStatusUpdate.model_validate({})


def test_producto_respuesta_serializa_camel_case_y_fecha_iso() -> None:
    respuesta = ProductResponse(
        id="p-1",
        code="MED-001",
        name="Paracetamol",
        description="Tabletas",
        category_id="cat-med",
        unit="Tableta",
        unit_price=0.5,
        min_stock=20,
        tracks_expiration=True,
        expiration_date="2027-10-31",
        active=True,
    )

    cuerpo = respuesta.model_dump(mode="json")

    assert set(cuerpo) == CAMPOS_ESPERADOS | {"id", "active"}
    assert cuerpo["expirationDate"] == "2027-10-31"
    assert cuerpo["unitPrice"] == 0.5
    assert cuerpo["categoryId"] == "cat-med"


def test_producto_respuesta_acepta_tipos_devueltos_por_pyodbc() -> None:
    identificador = uuid4()

    producto = ProductResponse.model_validate(
        {
            "id": identificador,
            "code": "MED-001",
            "name": "Paracetamol",
            "description": "Tabletas",
            "categoryId": identificador,
            "unit": "Tableta",
            "unitPrice": Decimal("28.00"),
            "minStock": 20,
            "tracksExpiration": False,
            "expirationDate": None,
            "active": True,
        }
    )

    cuerpo = producto.model_dump(mode="json")
    assert cuerpo["id"] == str(identificador)
    assert cuerpo["categoryId"] == str(identificador)
    assert cuerpo["unitPrice"] == 28.0
