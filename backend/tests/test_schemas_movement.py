"""Pruebas de los schemas de movimientos de inventario."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from backend.schemas.common import MAX_SQL_INT
from backend.schemas.movement import (
    ENTRY_REASONS,
    MovementCreate,
    MovementResponse,
    MovementType,
)

HOY = date.today()
AYER = HOY - timedelta(days=1)
MANANA = HOY + timedelta(days=1)


def entrada(**cambios: object) -> dict[str, object]:
    base: dict[str, object] = {
        "type": "entry",
        "productId": "p-1",
        "quantity": 3,
        "date": HOY.isoformat(),
        "reason": "Compra",
        "lotNumber": "PAR-027",
        "expirationDate": (HOY + timedelta(days=365)).isoformat(),
    }
    base.update(cambios)
    return base


def salida(**cambios: object) -> dict[str, object]:
    base: dict[str, object] = {
        "type": "exit",
        "productId": "p-1",
        "quantity": 1,
        "date": HOY.isoformat(),
        "reason": "Reposición de insumos",
        "lotId": "l-1",
        "areaId": "emergencia",
    }
    base.update(cambios)
    return base


def error_en(excinfo: pytest.ExceptionInfo[ValidationError], campo: str) -> dict:
    return next(e for e in excinfo.value.errors() if e["loc"] == (campo,))


def test_entrada_valida_del_contrato() -> None:
    movimiento = MovementCreate.model_validate(
        entrada(lotNumber="  par-027  ", expirationDate="2028-10-31")
    )

    assert movimiento.type is MovementType.ENTRY
    assert movimiento.lot_number == "PAR-027"
    assert movimiento.lot_id is None
    assert movimiento.area_id is None
    assert movimiento.expiration_date.isoformat() == "2028-10-31"


def test_salida_valida_del_contrato() -> None:
    movimiento = MovementCreate.model_validate(salida())

    assert movimiento.type is MovementType.EXIT
    assert movimiento.lot_id == "l-1"
    assert movimiento.area_id == "emergencia"
    assert movimiento.expiration_date is None


def test_salida_omite_campos_opcionales_no_enviados() -> None:
    datos = salida()
    movimiento = MovementCreate.model_validate(datos)

    assert movimiento.lot_number is None
    assert movimiento.expiration_date is None


def test_tipo_de_movimiento_solo_admite_entry_o_exit() -> None:
    with pytest.raises(ValidationError) as excinfo:
        MovementCreate.model_validate(entrada(type="transfer"))

    assert excinfo.value.errors()[0]["loc"] == ("type",)


@pytest.mark.parametrize("cantidad", [0, -1, 1.5, True, "3", MAX_SQL_INT + 1])
def test_cantidad_debe_ser_entero_positivo(cantidad: object) -> None:
    with pytest.raises(ValidationError) as excinfo:
        MovementCreate.model_validate(entrada(quantity=cantidad))

    assert "número entero mayor que cero" in error_en(excinfo, "quantity")["msg"]


def test_cantidad_admite_uno_y_el_maximo_de_sql_server() -> None:
    assert MovementCreate.model_validate(entrada(quantity=1)).quantity == 1
    assert MovementCreate.model_validate(entrada(quantity=MAX_SQL_INT)).quantity == MAX_SQL_INT


def test_fecha_futura_se_rechaza() -> None:
    with pytest.raises(ValidationError) as excinfo:
        MovementCreate.model_validate(entrada(date=MANANA.isoformat()))

    assert "no sea futura" in error_en(excinfo, "date")["msg"]


def test_fecha_de_hoy_y_pasada_son_validas() -> None:
    assert MovementCreate.model_validate(entrada(date=HOY.isoformat())).date == HOY
    assert MovementCreate.model_validate(entrada(date=AYER.isoformat())).date == AYER


def test_fecha_con_formato_invalido_se_rechaza() -> None:
    with pytest.raises(ValidationError) as excinfo:
        MovementCreate.model_validate(entrada(date="31/10/2026"))

    assert error_en(excinfo, "date")["loc"] == ("date",)


def test_entrada_exige_numero_de_lote() -> None:
    datos = entrada()
    datos.pop("lotNumber")

    with pytest.raises(ValidationError) as excinfo:
        MovementCreate.model_validate(datos)

    assert "número de lote" in error_en(excinfo, "lotNumber")["msg"]


def test_entrada_no_debe_enviar_lot_id() -> None:
    with pytest.raises(ValidationError) as excinfo:
        MovementCreate.model_validate(entrada(lotId="l-1"))

    assert "lotNumber" in error_en(excinfo, "lotId")["msg"]


def test_entrada_no_debe_enviar_area() -> None:
    with pytest.raises(ValidationError) as excinfo:
        MovementCreate.model_validate(entrada(areaId="emergencia"))

    assert "no debe incluir" in error_en(excinfo, "areaId")["msg"]


def test_salida_exige_lote_y_area() -> None:
    datos = salida()
    datos.pop("lotId")
    datos.pop("areaId")

    with pytest.raises(ValidationError) as excinfo:
        MovementCreate.model_validate(datos)

    ubicaciones = {error["loc"] for error in excinfo.value.errors()}
    assert ("lotId",) in ubicaciones
    assert ("areaId",) in ubicaciones


def test_motivo_de_entrada_esta_limitado_al_catalogo() -> None:
    assert set(ENTRY_REASONS) == {"Compra", "Donación", "Devolución"}

    for motivo in ENTRY_REASONS:
        assert MovementCreate.model_validate(entrada(reason=motivo)).reason == motivo

    for invalido in ("compra", "Venta", "Compra interna"):
        with pytest.raises(ValidationError) as excinfo:
            MovementCreate.model_validate(entrada(reason=invalido))

        assert "compra, donación o devolución" in error_en(excinfo, "reason")["msg"]


def test_motivo_recorta_espacios_antes_de_comparar() -> None:
    assert MovementCreate.model_validate(entrada(reason="  Donación  ")).reason == "Donación"


def test_motivo_de_salida_es_texto_libre_no_vacio() -> None:
    assert MovementCreate.model_validate(salida(reason="  Uso en emergencia  ")).reason == (
        "Uso en emergencia"
    )

    with pytest.raises(ValidationError) as excinfo:
        MovementCreate.model_validate(salida(reason="   "))

    assert "motivo" in error_en(excinfo, "reason")["msg"]


def test_motivo_admite_hasta_200_caracteres() -> None:
    assert MovementCreate.model_validate(salida(reason="A" * 200)).reason == "A" * 200

    with pytest.raises(ValidationError) as excinfo:
        MovementCreate.model_validate(salida(reason="A" * 201))

    assert "hasta 200" in error_en(excinfo, "reason")["msg"]


def test_vencimiento_anterior_al_ingreso_se_rechaza() -> None:
    with pytest.raises(ValidationError) as excinfo:
        MovementCreate.model_validate(
            entrada(expirationDate=(HOY - timedelta(days=1)).isoformat())
        )

    assert "vencido a la fecha" in error_en(excinfo, "expirationDate")["msg"]


def test_vencimiento_igual_a_la_fecha_de_ingreso_es_valido() -> None:
    movimiento = MovementCreate.model_validate(entrada(expirationDate=HOY.isoformat()))

    assert movimiento.expiration_date == HOY


def test_entrada_sin_vencimiento_es_valida() -> None:
    datos = entrada()
    datos.pop("expirationDate")

    assert MovementCreate.model_validate(datos).expiration_date is None


def test_salida_acepta_vencimiento_informativo_ya_pasado() -> None:
    movimiento = MovementCreate.model_validate(
        salida(expirationDate=(HOY - timedelta(days=30)).isoformat())
    )

    assert movimiento.expiration_date == HOY - timedelta(days=30)


def test_producto_vacio_se_rechaza() -> None:
    with pytest.raises(ValidationError) as excinfo:
        MovementCreate.model_validate(salida(productId="   "))

    assert "producto" in error_en(excinfo, "productId")["msg"]


def test_movimiento_rechaza_campos_extra() -> None:
    with pytest.raises(ValidationError) as excinfo:
        MovementCreate.model_validate(salida(stockBefore=10))

    assert excinfo.value.errors()[0]["type"] == "extra_forbidden"


def test_movimiento_respuesta_incluye_saldos_y_trazabilidad() -> None:
    respuesta = MovementResponse(
        id="m-1",
        type="exit",
        product_id="p-1",
        quantity=1,
        date="2026-10-31",
        reason="Reposición de insumos",
        stock_before=50,
        stock_after=49,
        lot_id="l-1",
        lot_number="PAR-026",
        expiration_date="2027-10-31",
        area_id="emergencia",
    )

    cuerpo = respuesta.model_dump(mode="json")

    assert set(cuerpo) == {
        "id",
        "type",
        "productId",
        "quantity",
        "date",
        "reason",
        "stockBefore",
        "stockAfter",
        "lotId",
        "lotNumber",
        "expirationDate",
        "areaId",
    }
    assert cuerpo["type"] == "exit"
    assert cuerpo["date"] == "2026-10-31"
    assert cuerpo["stockAfter"] == 49
