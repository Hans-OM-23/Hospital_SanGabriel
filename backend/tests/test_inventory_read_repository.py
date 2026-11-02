"""Etapa 7: repositorios de consultas usando cursores simulados, sin SQL Server."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from decimal import Decimal

import pyodbc
import pytest

from backend.core.exceptions import DatabaseConnectionError
from backend.repositories.inventory_read import InventoryReadRepository


class FakeCursor:
    def __init__(self, columns: list[str], rows: list[tuple[object, ...]]) -> None:
        self.description = [(column,) for column in columns]
        self.rows = rows
        self.executed: list[str] = []
        self.closed = False

    def execute(self, sql: str) -> None:
        self.executed.append(sql)

    def fetchall(self) -> list[tuple[object, ...]]:
        return self.rows


class FakeDatabase:
    def __init__(self, cursor: FakeCursor) -> None:
        self.cursor = cursor
        self.opens = 0
        self.closes = 0

    @contextmanager
    def connection(self):
        self.opens += 1
        try:
            yield self.cursor
        finally:
            self.cursor.closed = True
            self.closes += 1


def repo(columns: list[str], *rows: tuple[object, ...]):
    cursor = FakeCursor(columns, list(rows))
    db = FakeDatabase(cursor)
    return InventoryReadRepository(db), cursor, db


@pytest.mark.parametrize(
    ("method", "statement"),
    [
        ("list_products", "EXEC dbo.usp_ListarProductos"),
        ("list_categories", "EXEC dbo.usp_ListarCategorias"),
        ("list_lots", "EXEC dbo.usp_ListarLotes"),
        ("list_areas", "EXEC dbo.usp_ListarAreas"),
        ("list_movements", "EXEC dbo.usp_ListarMovimientos"),
    ],
)
def test_lectura_vacia_ejecuta_solo_procedimiento_y_cierra_conexion(method, statement):
    inventory, cursor, db = repo(["id"])
    assert getattr(inventory, method)() == []
    assert cursor.executed == [statement]
    assert db.opens == db.closes == 1
    assert cursor.closed is True
    assert all("SELECT" not in sql.upper() for sql in cursor.executed)


def test_lista_productos_con_precio_decimal_y_alias_camel_case():
    columns = [
        "id", "code", "name", "description", "category_id", "unit",
        "unit_price", "min_stock", "tracks_expiration", "expiration_date", "active",
    ]
    data = (
        "p-1", "MED-001", "Paracetamol", "Tabletas", "cat-1", "Tableta",
        Decimal("0.50"), 20, True, date(2027, 11, 1), False,
    )
    inventory, cursor, db = repo(columns, data)
    products = inventory.list_products()
    assert len(products) == 1
    assert products[0].unit_price == 0.5
    assert products[0].active is False  # los inactivos no deben ocultarse
    assert products[0].model_dump(mode="json") == {
        "id": "p-1", "code": "MED-001", "name": "Paracetamol",
        "description": "Tabletas", "categoryId": "cat-1", "unit": "Tableta",
        "unitPrice": 0.5, "minStock": 20, "tracksExpiration": True,
        "expirationDate": "2027-11-01", "active": False,
    }
    assert cursor.closed and db.closes == 1


def test_lista_categorias_y_areas():
    categories, _, _ = repo(
        ["id", "name", "description", "active"],
        ("cat-1", "Medicamentos", "Farmacia", True),
    )
    assert categories.list_categories()[0].model_dump(mode="json") == {
        "id": "cat-1", "name": "Medicamentos", "description": "Farmacia", "active": True,
    }
    areas, _, _ = repo(["id", "name"], ("area-1", "Emergencia"))
    assert areas.list_areas()[0].model_dump(mode="json") == {
        "id": "area-1", "name": "Emergencia",
    }


def test_lote_sin_vencimiento_y_sin_existencias_se_conserva():
    inventory, _, _ = repo(
        ["id", "product_id", "number", "expiration_date", "stock"],
        ("lot-1", "p-1", "PAR-026", None, 0),
    )
    assert inventory.list_lots()[0].model_dump(mode="json") == {
        "id": "lot-1", "productId": "p-1", "number": "PAR-026",
        "expirationDate": None, "stock": 0,
    }


def test_movimientos_usan_saldos_del_producto_y_lote_del_join():
    columns = [
        "id", "type", "product_id", "quantity", "date", "reason",
        "stock_before", "stock_after", "lot_id", "lot_number",
        "expiration_date", "area_id",
    ]
    inventory, _, _ = repo(
        columns,
        ("m-1", "entry", "p-1", 50, date(2026, 10, 30), "Compra",
         0, 50, "l-1", "PAR-026", date(2027, 10, 30), None),
        ("m-2", "exit", "p-1", 10, date(2026, 10, 31), "Uso",
         50, 40, "l-1", "PAR-026", date(2027, 10, 30), "a-1"),
    )
    result = [movement.model_dump(mode="json") for movement in inventory.list_movements()]
    assert [row["id"] for row in result] == ["m-1", "m-2"]
    assert [(row["stockBefore"], row["stockAfter"]) for row in result] == [
        (0, 50), (50, 40),
    ]
    assert result[1]["lotNumber"] == "PAR-026"
    assert result[1]["areaId"] == "a-1"
    assert result[0]["date"] == "2026-10-30"


def test_conexion_se_cierra_si_respuesta_no_cumple_el_schema():
    inventory, cursor, db = repo(["id"], ("p-1",))
    with pytest.raises(Exception):
        inventory.list_products()
    assert cursor.closed and db.opens == db.closes == 1


def test_columnas_repetidas_o_ausentes_se_rechazan():
    for columns in ([], ["id", "id"]):
        inventory, cursor, _ = repo(columns)
        if not columns:
            cursor.description = None
        with pytest.raises(DatabaseConnectionError):
            inventory.list_areas()


def test_error_del_driver_no_expone_su_mensaje():
    class BadCursor(FakeCursor):
        def execute(self, sql: str) -> None:
            raise pyodbc.Error("42000", "PWD=clave-privada; Login failed")

    cursor = BadCursor(["id"], [])
    db = FakeDatabase(cursor)
    with pytest.raises(DatabaseConnectionError) as excinfo:
        InventoryReadRepository(db).list_products()
    assert excinfo.value.__suppress_context__ is True
    assert "PWD=" not in str(excinfo.value)
    assert "Login failed" not in str(excinfo.value)
    assert cursor.closed
