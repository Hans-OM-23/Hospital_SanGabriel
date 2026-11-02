"""Etapa 9: procedimientos parametrizados, transacciones y errores seguros."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pyodbc
import pytest

from backend.core.exceptions import (
    DatabaseConnectionError,
    InventoryConflictError,
    InventoryInvalidReferenceError,
    InventoryNotFoundError,
)
from backend.repositories.inventory_write import InventoryWriteRepository
from backend.schemas.category import CategoryCreate
from backend.schemas.product import ProductCreate

CAT_ID = str(uuid4())
PRODUCT_ID = str(uuid4())


class FakeCursor:
    def __init__(self, columns: list[str] | None, row: tuple | None = None,
                 error: Exception | None = None) -> None:
        self.description = None if columns is None else [(x,) for x in columns]
        self.row = row
        self.error = error
        self.executed: list[tuple[str, tuple]] = []
        self.closed = False

    def execute(self, sql: str, *parameters: object):
        self.executed.append((sql, parameters))
        if self.error:
            raise self.error
        return self

    def fetchone(self):
        return self.row


class FakeDatabase:
    def __init__(self, cursor: FakeCursor):
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


PRODUCT_COLS = [
    "id", "code", "name", "description", "category_id", "unit", "unit_price",
    "min_stock", "tracks_expiration", "expiration_date", "active",
]
PRODUCT_ROW = (
    PRODUCT_ID, "MED-001", "Paracetamol", "Tabletas", CAT_ID, "Tableta",
    Decimal("0.50"), 5, True, date(2027, 1, 2), True,
)


def category_payload() -> CategoryCreate:
    return CategoryCreate(name="Medicamentos", description="Tratamientos")


def product_payload() -> ProductCreate:
    return ProductCreate.model_validate({
        "code": "  med-001 ", "name": "Paracetamol", "description": "Tabletas",
        "categoryId": CAT_ID, "unit": "Tableta", "unitPrice": 0.50,
        "minStock": 5, "tracksExpiration": True,
        "expirationDate": "2027-01-02",
    })


def test_crea_categoria_ejecutando_solo_procedimiento_parametrizado():
    cursor = FakeCursor(["id", "name", "description", "active"],
                        (CAT_ID, "Medicamentos", "Tratamientos", True))
    db = FakeDatabase(cursor)
    result = InventoryWriteRepository(db).create_category(category_payload())
    assert result.model_dump(mode="json") == {
        "id": CAT_ID, "name": "Medicamentos", "description": "Tratamientos", "active": True
    }
    statement, params = cursor.executed[0]
    assert statement == "EXEC dbo.usp_CrearCategoria @name=?, @description=?"
    assert params == ("Medicamentos", "Tratamientos")
    assert db.commits == db.closes == 1 and db.rollbacks == 0 and cursor.closed


def test_crea_producto_con_decimal_preciso_y_sin_sql_dinamico():
    cursor = FakeCursor(PRODUCT_COLS, PRODUCT_ROW)
    db = FakeDatabase(cursor)
    result = InventoryWriteRepository(db).create_product(product_payload())
    assert result.id == PRODUCT_ID
    assert result.model_dump(mode="json")["unitPrice"] == 0.5
    sql, params = cursor.executed[0]
    assert sql.startswith("EXEC dbo.usp_CrearProducto")
    assert sql.count("?") == 9
    assert "INSERT " not in sql.upper() and "UPDATE " not in sql.upper()
    assert "MED-001" not in sql and params[0] == "MED-001"
    assert params[3] == CAT_ID
    assert params[5] == Decimal("0.50")
    assert params[-1] == date(2027, 1, 2)
    assert db.commits == 1 and db.rollbacks == 0


def test_actualiza_producto_sin_modificar_estado_activo():
    cursor = FakeCursor(PRODUCT_COLS, PRODUCT_ROW)
    db = FakeDatabase(cursor)
    result = InventoryWriteRepository(db).update_product(PRODUCT_ID, product_payload())
    assert result.active is True
    sql, params = cursor.executed[0]
    assert sql.startswith("EXEC dbo.usp_ActualizarProducto")
    assert len(params) == 10 and params[0] == PRODUCT_ID
    assert db.commits == 1


@pytest.mark.parametrize("active", [True, False])
def test_cambia_estado_sin_cambiar_otra_cosa(active):
    cursor = FakeCursor(None)
    db = FakeDatabase(cursor)
    assert InventoryWriteRepository(db).set_product_status(PRODUCT_ID, active) is None
    assert cursor.executed == [(
        "EXEC dbo.usp_CambiarEstadoProducto @product_id=?, @active=?",
        (PRODUCT_ID, active),
    )]
    assert db.commits == db.closes == 1 and db.rollbacks == 0


@pytest.mark.parametrize(
    "number,expected_class,expected_field",
    [
        ("51011", InventoryConflictError, "name"),
        ("51012", InventoryConflictError, "code"),
        ("51013", InventoryInvalidReferenceError, "categoryId"),
        ("51014", InventoryNotFoundError, None),
        ("51015", InventoryConflictError, "unit"),
        ("51016", InventoryConflictError, "tracksExpiration"),
    ],
)
def test_codigos_throw_se_traducen_y_se_revierte(number, expected_class, expected_field):
    cursor = FakeCursor(
        PRODUCT_COLS, PRODUCT_ROW,
        pyodbc.Error("42000", f"[SQL Server] secretoPWD=abc ({number}) (SQLExecDirectW)"),
    )
    db = FakeDatabase(cursor)
    with pytest.raises(expected_class) as excinfo:
        InventoryWriteRepository(db).create_product(product_payload())
    assert excinfo.value.field == expected_field
    assert "secreto" not in str(excinfo.value)
    assert db.commits == 0 and db.rollbacks == db.closes == 1


def test_error_odbc_desconocido_es_503_seguro_y_revertido():
    cursor = FakeCursor(PRODUCT_COLS, PRODUCT_ROW,
                        pyodbc.Error("42S02", "PWD=muy-secreto, tabla faltante (208)"))
    db = FakeDatabase(cursor)
    with pytest.raises(DatabaseConnectionError) as excinfo:
        InventoryWriteRepository(db).create_product(product_payload())
    assert "PWD" not in str(excinfo.value)
    assert db.rollbacks == 1 and db.commits == 0


@pytest.mark.parametrize(
    "columns,row",
    [
        (None, None),
        (["id", "id"], ("a", "b")),
        (["id"], None),
        (["id", "name"], ("only-one",)),
        (["id", "name"], ("only-one", "other")),
    ],
)
def test_respuesta_invalida_no_confirma_transaccion(columns, row):
    cursor = FakeCursor(columns, row)
    db = FakeDatabase(cursor)
    with pytest.raises(DatabaseConnectionError):
        InventoryWriteRepository(db).create_category(category_payload())
    assert db.rollbacks == db.closes == 1 and db.commits == 0


def test_sin_sql_antes_de_inyectar_dependencias():
    class NeverDatabase:
        def transaction(self):
            raise AssertionError("No conectar en __init__")

    InventoryWriteRepository(NeverDatabase())
