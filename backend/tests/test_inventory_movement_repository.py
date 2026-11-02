"""La escritura de movimientos es transaccional y usa solo SP parametrizados."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from uuid import uuid4

import pyodbc
import pytest

from backend.core.exceptions import (
    DatabaseConnectionError,
    InventoryConflictError,
    InventoryInvalidReferenceError,
)
from backend.repositories.inventory_movements import InventoryMovementRepository
from backend.schemas.movement import MovementCreate

PRODUCT_ID = str(uuid4())
LOT_ID = str(uuid4())
AREA_ID = str(uuid4())
MOVEMENT_ID = str(uuid4())
COLS = [
    "id", "type", "product_id", "quantity", "date", "reason", "stock_before",
    "stock_after", "lot_id", "lot_number", "expiration_date", "area_id",
]
ENTRY_ROW = (
    MOVEMENT_ID, "entry", PRODUCT_ID, 4, date(2026, 10, 31), "Compra", 10, 14,
    LOT_ID, "PAR-027", date(2028, 10, 31), None,
)
EXIT_ROW = (
    MOVEMENT_ID, "exit", PRODUCT_ID, 3, date(2026, 10, 31), "Reposición", 14, 11,
    LOT_ID, "PAR-027", date(2028, 10, 31), AREA_ID,
)


class FakeCursor:
    def __init__(self, columns=COLS, row=ENTRY_ROW, error=None):
        self.description = None if columns is None else [(name,) for name in columns]
        self.row = row
        self.error = error
        self.calls: list[tuple[str, tuple]] = []
        self.closed = False

    def execute(self, sql, *params):
        self.calls.append((sql, params))
        if self.error:
            raise self.error
        return self

    def fetchone(self):
        return self.row


class FakeDatabase:
    def __init__(self, cursor):
        self.cursor = cursor
        self.commits = 0
        self.rollbacks = 0
        self.closes = 0

    @contextmanager
    def transaction(self):
        try:
            yield self.cursor
            self.commits += 1
        except BaseException:
            self.rollbacks += 1
            raise
        finally:
            self.closes += 1
            self.cursor.closed = True


def payload(kind="entry"):
    if kind == "entry":
        return MovementCreate.model_validate({
            "type": "entry", "productId": PRODUCT_ID, "quantity": 4,
            "date": "2026-10-31", "reason": "Compra", "lotNumber": "par-027",
            "expirationDate": "2028-10-31",
        })
    return MovementCreate.model_validate({
        "type": "exit", "productId": PRODUCT_ID, "quantity": 3,
        "date": "2026-10-31", "reason": "Reposición", "lotId": LOT_ID,
        "areaId": AREA_ID,
    })


def test_entrada_confirma_movimiento_y_usa_parametros():
    cursor = FakeCursor()
    db = FakeDatabase(cursor)
    result = InventoryMovementRepository(db).register_movement(payload())
    assert result.id == MOVEMENT_ID
    assert result.model_dump(mode="json")["stockAfter"] == 14
    assert result.model_dump(mode="json")["lotNumber"] == "PAR-027"
    statement, params = cursor.calls[0]
    assert statement.startswith("EXEC dbo.usp_RegistrarMovimiento")
    assert statement.count("?") == 9
    assert "INSERT " not in statement.upper() and "UPDATE " not in statement.upper()
    assert "PAR-027" not in statement
    assert params == (
        "entry", PRODUCT_ID, 4, date(2026, 10, 31), "Compra", None,
        "PAR-027", date(2028, 10, 31), None,
    )
    assert db.commits == db.closes == 1 and db.rollbacks == 0 and cursor.closed


def test_salida_devuelve_lote_y_area_del_servidor():
    cursor = FakeCursor(row=EXIT_ROW)
    db = FakeDatabase(cursor)
    response = InventoryMovementRepository(db).register_movement(payload("exit"))
    assert response.stock_before == 14 and response.stock_after == 11
    assert response.area_id == AREA_ID and response.lot_id == LOT_ID
    assert cursor.calls[0][1] == (
        "exit", PRODUCT_ID, 3, date(2026, 10, 31), "Reposición", LOT_ID,
        None, None, AREA_ID,
    )
    assert db.commits == 1 and db.rollbacks == 0


@pytest.mark.parametrize("error_number,error_class,field", [
    ("51021", InventoryInvalidReferenceError, "productId"),
    ("51022", InventoryInvalidReferenceError, "lotId"),
    ("51023", InventoryConflictError, "expirationDate"),
    ("51024", InventoryConflictError, "lotId"),
    ("51025", InventoryConflictError, "quantity"),
    ("51026", InventoryInvalidReferenceError, "areaId"),
    ("51027", InventoryInvalidReferenceError, "expirationDate"),
    ("51028", InventoryInvalidReferenceError, "expirationDate"),
    ("51029", InventoryInvalidReferenceError, "date"),
    ("51030", InventoryConflictError, "quantity"),
    ("51031", InventoryInvalidReferenceError, None),
    ("51032", InventoryInvalidReferenceError, "reason"),
    ("51033", InventoryInvalidReferenceError, "quantity"),
    ("51034", InventoryInvalidReferenceError, "lotNumber"),
])
def test_errores_del_sp_se_traducen_sin_fuga(error_number, error_class, field):
    cursor = FakeCursor(error=pyodbc.Error(
        "42000", f"[Microsoft][ODBC Driver 18] PWD=clave-super-secreta ({error_number})",
    ))
    db = FakeDatabase(cursor)
    with pytest.raises(error_class) as error:
        InventoryMovementRepository(db).register_movement(payload())
    assert error.value.field == field
    assert "clave-super-secreta" not in str(error.value)
    assert db.rollbacks == db.closes == 1 and db.commits == 0


def test_error_desconocido_es_seguro_y_hace_rollback():
    cursor = FakeCursor(error=pyodbc.Error("42S02", "PWD=oculto (208)"))
    db = FakeDatabase(cursor)
    with pytest.raises(DatabaseConnectionError) as exc:
        InventoryMovementRepository(db).register_movement(payload())
    assert "PWD" not in str(exc.value) and db.rollbacks == 1


@pytest.mark.parametrize("columns,row", [
    (None, None),
    (["id", "id"], ("a", "b")),
    (COLS, None),
    (["id", "type"], ("1",)),
    (["id", "type"], ("1", "entry")),
])
def test_respuesta_invalida_no_se_confirma(columns, row):
    cursor = FakeCursor(columns=columns, row=row)
    db = FakeDatabase(cursor)
    with pytest.raises(DatabaseConnectionError):
        InventoryMovementRepository(db).register_movement(payload())
    assert db.rollbacks == db.closes == 1 and db.commits == 0


def test_construir_repositorio_no_abre_conexion():
    class NeverConnect:
        def transaction(self):
            raise AssertionError("No se debe conectar en __init__")
    InventoryMovementRepository(NeverConnect())
