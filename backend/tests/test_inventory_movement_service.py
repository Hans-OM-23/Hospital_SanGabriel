"""Servicio: referencias UUID y delegación sin SQL."""
from __future__ import annotations

from uuid import uuid4

import pytest

from backend.core.exceptions import InventoryInvalidReferenceError
from backend.schemas.movement import MovementCreate
from backend.services.inventory_movement_service import InventoryMovementService

PRODUCT = str(uuid4())
LOT = str(uuid4())
AREA = str(uuid4())


class FakeRepository:
    def __init__(self):
        self.requests = []

    def register_movement(self, data):
        self.requests.append(data)
        return "movimiento-ok"


def input_data(**changes):
    data = {
        "type": "entry", "productId": PRODUCT, "quantity": 2,
        "date": "2026-10-30", "reason": "Compra", "lotNumber": "L-001",
        "expirationDate": "2028-05-01",
    }
    data.update(changes)
    return MovementCreate.model_validate(data)


def test_entrada_normaliza_producto_y_delega_sin_escribir():
    repo = FakeRepository()
    result = InventoryMovementService(repo).register_movement(input_data())
    assert result == "movimiento-ok"
    assert repo.requests[0].product_id == PRODUCT
    assert repo.requests[0].lot_number == "L-001"


def test_salida_normaliza_ids_y_delega():
    repo = FakeRepository()
    data = input_data(type="exit", lotNumber=None, expirationDate=None,
                      lotId=LOT.upper(), areaId=AREA.upper(), reason="Reposición")
    InventoryMovementService(repo).register_movement(data)
    assert repo.requests[0].lot_id == LOT
    assert repo.requests[0].area_id == AREA


@pytest.mark.parametrize("field,invalid,expected", [
    ("productId", "no-es-uuid", "productId"),
    ("lotId", "no-es-uuid", "lotId"),
    ("areaId", "no-es-uuid", "areaId"),
])
def test_referencia_invalida_422_sin_ejecutar_repositorio(field, invalid, expected):
    repo = FakeRepository()
    if field == "productId":
        data = input_data(productId=invalid)
    else:
        data = input_data(type="exit", lotNumber=None, expirationDate=None,
                          lotId=invalid if field == "lotId" else LOT,
                          areaId=invalid if field == "areaId" else AREA,
                          reason="Reposición")
    with pytest.raises(InventoryInvalidReferenceError) as e:
        InventoryMovementService(repo).register_movement(data)
    assert e.value.field == expected
    assert repo.requests == []
