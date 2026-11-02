"""Schemas de movimientos de inventario.

``MovementCreate`` valida la forma del ``MovementInput`` de Angular y las
reglas que no necesitan consultar la base de datos:

- cantidad entera positiva;
- fecha de calendario no futura;
- motivo de entrada dentro del catálogo (Compra, Donación, Devolución);
- entrada con número de lote y sin área; salida con lote y área;
- vencimiento del lote no anterior a la fecha de ingreso.

En una salida se aceptan ``lotNumber`` y ``expirationDate`` como datos
informativos, pero el lote se resuelve siempre por ``lotId``.

Quedan para el servicio y los procedimientos almacenados: producto activo,
lote perteneciente al producto, saldo real del lote, bloqueo de lotes vencidos
y cálculo de ``stockBefore`` / ``stockAfter``. El cliente nunca los envía.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta, timezone
from enum import StrEnum
from typing import Any

from pydantic import Field, ValidationInfo, field_validator, model_validator
from pydantic_core import PydanticCustomError

from backend.schemas.common import (
    MAX_SQL_INT,
    ApiInput,
    ApiResponse,
    Identifier,
    ISODate,
    entero,
    texto_obligatorio,
)

ENTRY_REASONS: tuple[str, ...] = ("Compra", "Donación", "Devolución")

# Perú mantiene UTC-05 durante todo el año, sin horario de verano. Usar la
# zona horaria del hospital, no la del servidor, evita rechazar fechas de hoy
# cuando FastAPI se ejecuta en otro país o en una máquina configurada en UTC.
_PERU_TIMEZONE = timezone(timedelta(hours=-5))


def fecha_hoy_peru(utc_now: datetime | None = None) -> date:
    """Fecha de calendario del hospital, independiente del reloj local del servidor."""
    ahora = utc_now if utc_now is not None else datetime.now(UTC)
    if ahora.tzinfo is None:
        raise ValueError("La fecha de referencia debe incluir zona horaria.")
    return ahora.astimezone(_PERU_TIMEZONE).date()


class MovementType(StrEnum):
    """Tipos admitidos por el contrato (``MovementType`` en Angular)."""

    ENTRY = "entry"
    EXIT = "exit"


ProductReference = texto_obligatorio(
    max_length=100,
    mensaje_requerido="Selecciona un producto.",
    mensaje_longitud="El producto no es válido.",
)

LotReference = texto_obligatorio(
    max_length=100,
    mensaje_requerido="Selecciona manualmente un lote del producto.",
    mensaje_longitud="El lote no es válido.",
)

LotNumber = texto_obligatorio(
    max_length=50,
    mensaje_requerido="Indica el número de lote para conservar la trazabilidad.",
    mensaje_longitud="El número de lote admite hasta 50 caracteres.",
    mayusculas=True,
)

AreaReference = texto_obligatorio(
    max_length=100,
    mensaje_requerido="Selecciona el área hospitalaria de destino.",
    mensaje_longitud="El área hospitalaria no es válida.",
)

MovementReason = texto_obligatorio(
    max_length=200,
    mensaje_requerido="Indica el motivo del movimiento.",
    mensaje_longitud="El motivo admite hasta 200 caracteres.",
)

Quantity = entero(
    minimo=1,
    maximo=MAX_SQL_INT,
    mensaje="La cantidad debe ser un número entero mayor que cero.",
)


class MovementCreate(ApiInput):
    """Cuerpo de ``POST /movements`` (``MovementInput`` en Angular)."""

    type: MovementType
    product_id: ProductReference
    quantity: Quantity
    date: ISODate
    reason: MovementReason
    lot_id: LotReference | None = Field(default=None, validate_default=True)
    lot_number: LotNumber | None = Field(default=None, validate_default=True)
    expiration_date: ISODate | None = Field(default=None, validate_default=True)
    area_id: AreaReference | None = Field(default=None, validate_default=True)

    @model_validator(mode="before")
    @classmethod
    def _completar_opcionales(cls, data: Any) -> Any:
        """Incluye las claves opcionales ausentes usando su alias camelCase.

        Si la validación falla al aplicar una regla dependiente del tipo, el
        ``loc`` debe ser ``lotNumber``/``areaId`` y no ``lot_number``/``area_id``:
        el frontend identifica el campo por el último elemento de ``loc``.
        """
        if not isinstance(data, dict):
            return data

        faltantes = {
            alias: None
            for alias, nombre in (
                ("lotId", "lot_id"),
                ("lotNumber", "lot_number"),
                ("expirationDate", "expiration_date"),
                ("areaId", "area_id"),
            )
            if alias not in data and nombre not in data
        }
        return {**data, **faltantes} if faltantes else data

    @field_validator("date")
    @classmethod
    def _fecha_no_futura(cls, value: date) -> date:
        if value > fecha_hoy_peru():
            raise PydanticCustomError(
                "date_future",
                "Ingresa una fecha válida que no sea futura.",
            )
        return value

    @field_validator("reason")
    @classmethod
    def _motivo_segun_tipo(cls, value: str, info: ValidationInfo) -> str:
        tipo = info.data.get("type")
        if tipo is None:
            return value
        if tipo is MovementType.ENTRY and value not in ENTRY_REASONS:
            raise PydanticCustomError(
                "reason_entry",
                "Selecciona compra, donación o devolución.",
            )
        return value

    @field_validator("lot_id")
    @classmethod
    def _lote_segun_tipo(cls, value: str | None, info: ValidationInfo) -> str | None:
        tipo = info.data.get("type")
        if tipo is None:
            return value
        if tipo is MovementType.ENTRY:
            if value is not None:
                raise PydanticCustomError(
                    "lot_entry",
                    "Una entrada identifica el lote con lotNumber, no con lotId.",
                )
            return None
        if value is None:
            raise PydanticCustomError(
                "lot_required",
                "Selecciona manualmente el lote que se utilizará.",
            )
        return value

    @field_validator("lot_number")
    @classmethod
    def _numero_lote_segun_tipo(cls, value: str | None, info: ValidationInfo) -> str | None:
        tipo = info.data.get("type")
        if tipo is None:
            return value
        if tipo is MovementType.ENTRY and value is None:
            raise PydanticCustomError(
                "lot_number_required",
                "Indica el número de lote para conservar la trazabilidad.",
            )
        return value

    @field_validator("expiration_date")
    @classmethod
    def _vencimiento_segun_tipo(cls, value: date | None, info: ValidationInfo) -> date | None:
        tipo = info.data.get("type")
        fecha = info.data.get("date")
        if tipo is None or fecha is None or value is None:
            return value
        if tipo is MovementType.ENTRY and value < fecha:
            raise PydanticCustomError(
                "expiration_before_entry",
                "El lote no puede estar vencido a la fecha del ingreso.",
            )
        return value

    @field_validator("area_id")
    @classmethod
    def _area_segun_tipo(cls, value: str | None, info: ValidationInfo) -> str | None:
        tipo = info.data.get("type")
        if tipo is None:
            return value
        if tipo is MovementType.ENTRY:
            if value is not None:
                raise PydanticCustomError(
                    "area_entry",
                    "Una entrada no debe incluir un área de destino.",
                )
            return None
        if value is None:
            raise PydanticCustomError(
                "area_required",
                "Selecciona el área hospitalaria de destino.",
            )
        return value


class MovementResponse(ApiResponse):
    """Movimiento confirmado, con los saldos calculados por el servidor."""

    id: Identifier
    type: MovementType
    product_id: Identifier
    quantity: int
    date: ISODate
    reason: str
    stock_before: int
    stock_after: int
    lot_id: Identifier
    lot_number: str
    expiration_date: ISODate | None
    area_id: Identifier | None


__all__ = [
    "ENTRY_REASONS",
    "MovementCreate",
    "MovementResponse",
    "MovementType",
    "Quantity",
]
