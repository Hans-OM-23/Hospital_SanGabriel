"""Registro de entradas/salidas exclusivamente mediante un SP parametrizado.

No abre conexión en el constructor ni ejecuta INSERT/UPDATE directos.
La transacción y el cursor los administra ``Database.transaction``.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pyodbc
from pydantic import ValidationError

from backend.core.exceptions import (
    DatabaseConnectionError,
    InventoryConflictError,
    InventoryInvalidReferenceError,
)
from backend.schemas.movement import MovementCreate, MovementResponse

if TYPE_CHECKING:
    from backend.core.database import Database

_SQL_ERRORS: dict[str, tuple[type[Exception], str, str | None]] = {
    "51021": (InventoryInvalidReferenceError, "Selecciona un producto activo.", "productId"),
    "51022": (InventoryInvalidReferenceError, "Selecciona manualmente un lote del producto.", "lotId"),
    "51023": (InventoryConflictError, "Este lote ya tiene otro vencimiento registrado. Verifica sus datos.", "expirationDate"),
    "51024": (InventoryConflictError, "El lote está vencido y no puede salir para uso hospitalario.", "lotId"),
    "51025": (InventoryConflictError, "El lote no tiene existencias suficientes.", "quantity"),
    "51026": (InventoryInvalidReferenceError, "Selecciona un área hospitalaria válida.", "areaId"),
    "51027": (InventoryInvalidReferenceError, "Selecciona un vencimiento válido para el lote.", "expirationDate"),
    "51028": (InventoryInvalidReferenceError, "El lote no puede estar vencido a la fecha de ingreso.", "expirationDate"),
    "51029": (InventoryInvalidReferenceError, "Selecciona una fecha válida que no sea futura.", "date"),
    "51030": (InventoryConflictError, "La cantidad supera el máximo permitido.", "quantity"),
    "51031": (InventoryInvalidReferenceError, "Revisa el lote y área del movimiento.", None),
    "51032": (InventoryInvalidReferenceError, "Selecciona un motivo válido para el movimiento.", "reason"),
    "51033": (InventoryInvalidReferenceError, "La cantidad debe ser un entero positivo.", "quantity"),
    "51034": (InventoryInvalidReferenceError, "Indica el número de lote.", "lotNumber"),
}


def _translate_sql_error(error: pyodbc.Error) -> Exception:
    """Lee únicamente los números THROW conocidos del diagnóstico ODBC."""
    diagnostic = " ".join(str(part) for part in getattr(error, "args", ()))
    for number in re.findall(r"\((510(?:2[1-9]|3[0-4]))\)", diagnostic):
        exception_type, message, field = _SQL_ERRORS[number]
        return exception_type(message, field=field)
    return DatabaseConnectionError("No se pudo registrar el movimiento.")


class InventoryMovementRepository:
    _REGISTER = (
        "EXEC dbo.usp_RegistrarMovimiento "
        "@type=?, @product_id=?, @quantity=?, @movement_date=?, @reason=?, "
        "@lot_id=?, @lot_number=?, @expiration_date=?, @area_id=?"
    )

    def __init__(self, database: Database) -> None:
        self._database = database

    def register_movement(self, data: MovementCreate) -> MovementResponse:
        parameters = (
            data.type.value, data.product_id, data.quantity, data.date, data.reason,
            data.lot_id, data.lot_number, data.expiration_date, data.area_id,
        )
        try:
            with self._database.transaction() as cursor:
                cursor.execute(self._REGISTER, *parameters)
                if cursor.description is None:
                    raise DatabaseConnectionError("El procedimiento no devolvió el movimiento.")
                columns = [str(item[0]) for item in cursor.description]
                if len(columns) != len(set(columns)):
                    raise DatabaseConnectionError("El procedimiento devolvió columnas repetidas.")
                row = cursor.fetchone()
                if row is None or len(row) != len(columns):
                    raise DatabaseConnectionError("El procedimiento no devolvió un movimiento válido.")
                try:
                    result = MovementResponse.model_validate(dict(zip(columns, row, strict=True)))
                except ValidationError:
                    raise DatabaseConnectionError("El procedimiento devolvió un formato inválido.") from None
            return result
        except pyodbc.Error as error:
            raise _translate_sql_error(error) from None


__all__ = ["InventoryMovementRepository"]
