"""Pruebas de los schemas de solo lectura: lotes y áreas hospitalarias."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.schemas.area import HospitalAreaResponse
from backend.schemas.lot import LotResponse


def test_lote_respuesta_serializa_camel_case_y_fecha_iso() -> None:
    lote = LotResponse(
        id="l-1",
        product_id="p-1",
        number="PAR-026",
        expiration_date="2027-10-31",
        stock=40,
    )

    cuerpo = lote.model_dump(mode="json")

    assert cuerpo == {
        "id": "l-1",
        "productId": "p-1",
        "number": "PAR-026",
        "expirationDate": "2027-10-31",
        "stock": 40,
    }


def test_lote_sin_vencimiento_serializa_null() -> None:
    lote = LotResponse(id="l-2", product_id="p-1", number="PAR-027", expiration_date=None, stock=0)

    assert lote.model_dump(mode="json")["expirationDate"] is None


def test_lote_respuesta_convierte_uuid_de_pyodbc_a_texto() -> None:
    identificador = uuid4()

    lote = LotResponse(
        id=identificador,
        product_id=identificador,
        number="PAR-026",
        expiration_date=None,
        stock=1,
    )

    cuerpo = lote.model_dump(mode="json")
    assert cuerpo["id"] == str(identificador)
    assert isinstance(cuerpo["productId"], str)


def test_lote_rechaza_fecha_con_hora() -> None:
    with pytest.raises(ValidationError):
        LotResponse(
            id="l-1",
            product_id="p-1",
            number="PAR-026",
            expiration_date="2027-10-31T08:00:00",
            stock=1,
        )


def test_area_respuesta_solo_expone_id_y_nombre() -> None:
    area = HospitalAreaResponse.model_validate(
        {"id": "emergencia", "name": "Emergencia", "created_at": "2026-01-01"}
    )

    assert area.model_dump() == {"id": "emergencia", "name": "Emergencia"}
