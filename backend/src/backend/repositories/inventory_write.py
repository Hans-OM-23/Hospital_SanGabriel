"""Mutaciones del catálogo exclusivamente mediante procedimientos parametrizados.

Los métodos reciben schemas ya validados y abren una transacción con
``Database.transaction``. Ninguna sentencia hace INSERT/UPDATE directos.
Las claves de error SQL Server 51011..51016 son un contrato entre los
procedimientos y el repositorio: jamás se devuelve el mensaje bruto ODBC.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import TYPE_CHECKING, TypeVar

import pyodbc
from pydantic import BaseModel, ValidationError

from backend.core.exceptions import (
    DatabaseConnectionError,
    InventoryConflictError,
    InventoryInvalidReferenceError,
    InventoryNotFoundError,
)
from backend.schemas.category import CategoryCreate, CategoryResponse
from backend.schemas.product import ProductCreate, ProductResponse, ProductUpdate

if TYPE_CHECKING:
    from backend.core.database import Database

T = TypeVar("T", bound=BaseModel)

# No se exponen mensajes devueltos por el controlador ODBC al cliente.
_SQL_ERRORS: dict[str, tuple[type[Exception], str, str | None]] = {
    "51011": (InventoryConflictError, "Esta categoría ya existe.", "name"),
    "51012": (InventoryConflictError, "Este código ya está registrado. Usa un código único.", "code"),
    "51013": (InventoryInvalidReferenceError, "Selecciona una categoría disponible.", "categoryId"),
    "51014": (InventoryNotFoundError, "El producto ya no está disponible.", None),
    "51015": (InventoryConflictError, "La unidad de medida no puede cambiar cuando existen movimientos.", "unit"),
    "51016": (InventoryConflictError, "El control de vencimiento no puede cambiar cuando existen movimientos.", "tracksExpiration"),
}


def _translate_sql_error(error: pyodbc.Error) -> Exception:
    """Reconoce solo números THROW del contrato, nunca texto arbitrario ODBC."""
    diagnostic = " ".join(str(part) for part in getattr(error, "args", ()))
    for match in re.findall(r"\((5101[1-6])\)", diagnostic):
        exception_type, message, field = _SQL_ERRORS[match]
        return exception_type(message, field=field)
    return DatabaseConnectionError("No se pudo completar la operación de inventario.")


def _product_parameters(data: ProductCreate | ProductUpdate) -> tuple[object, ...]:
    """DECIMAL(12,2) exacto y el resto de tipos admitidos por pyodbc."""
    return (
        data.code, data.name, data.description, data.category_id,
        data.unit, Decimal(str(data.unit_price)), data.min_stock,
        data.tracks_expiration, data.expiration_date,
    )


class InventoryWriteRepository:
    _CREATE_CATEGORY = "EXEC dbo.usp_CrearCategoria @name=?, @description=?"
    _CREATE_PRODUCT = (
        "EXEC dbo.usp_CrearProducto @code=?, @name=?, @description=?, "
        "@category_id=?, @unit=?, @unit_price=?, @min_stock=?, "
        "@tracks_expiration=?, @expiration_date=?"
    )
    _UPDATE_PRODUCT = (
        "EXEC dbo.usp_ActualizarProducto @product_id=?, @code=?, "
        "@name=?, @description=?, @category_id=?, @unit=?, "
        "@unit_price=?, @min_stock=?, @tracks_expiration=?, @expiration_date=?"
    )
    _CHANGE_STATUS = "EXEC dbo.usp_CambiarEstadoProducto @product_id=?, @active=?"

    def __init__(self, database: Database) -> None:
        self._database = database

    def _write_one(self, sql: str, parameters: tuple[object, ...], schema: type[T]) -> T:
        try:
            with self._database.transaction() as cursor:
                cursor.execute(sql, *parameters)
                if cursor.description is None:
                    raise DatabaseConnectionError("El procedimiento no devolvió el registro creado.")
                columns = [str(c[0]) for c in cursor.description]
                if len(columns) != len(set(columns)):
                    raise DatabaseConnectionError("El procedimiento devolvió columnas repetidas.")
                row = cursor.fetchone()
                if row is None or len(columns) != len(row):
                    raise DatabaseConnectionError("El procedimiento no devolvió el registro esperado.")
                try:
                    result = schema.model_validate(dict(zip(columns, row, strict=True)))
                except ValidationError:
                    raise DatabaseConnectionError("El procedimiento devolvió un formato inválido.") from None
            return result
        except pyodbc.Error as error:
            raise _translate_sql_error(error) from None

    def create_category(self, data: CategoryCreate) -> CategoryResponse:
        return self._write_one(
            self._CREATE_CATEGORY, (data.name, data.description), CategoryResponse
        )

    def create_product(self, data: ProductCreate) -> ProductResponse:
        return self._write_one(
            self._CREATE_PRODUCT, _product_parameters(data), ProductResponse
        )

    def update_product(self, product_id: str, data: ProductUpdate) -> ProductResponse:
        return self._write_one(
            self._UPDATE_PRODUCT, (product_id, *_product_parameters(data)), ProductResponse
        )

    def set_product_status(self, product_id: str, active: bool) -> None:
        try:
            with self._database.transaction() as cursor:
                cursor.execute(self._CHANGE_STATUS, product_id, active)
        except pyodbc.Error as error:
            raise _translate_sql_error(error) from None


__all__ = ["InventoryWriteRepository"]
