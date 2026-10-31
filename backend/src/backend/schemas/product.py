"""Schemas de productos.

``ProductInput`` corresponde a ``ProductInput`` de Angular
(``Omit<Product, 'id' | 'active'>``); ``ProductCreate`` y ``ProductUpdate``
documentan el uso en POST y PUT completo. ``ProductResponse`` es la ficha tal
como la muestra el frontend.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field, ValidationInfo, field_validator, model_validator
from pydantic_core import PydanticCustomError

from backend.schemas.common import (
    MAX_SQL_INT,
    ApiInput,
    ApiResponse,
    Identifier,
    ISODate,
    StrictBool,
    entero,
    precio,
    texto_obligatorio,
)

# Unidades admitidas por el formulario de productos. Se validan aquí porque
# son un valor permitido del contrato; el catálogo definitivo puede ampliarse
# sin migrar la base, que solo exige una unidad no vacía.
MEASUREMENT_UNITS: tuple[str, ...] = (
    "Unidad",
    "Tableta",
    "Cápsula",
    "Ampolla",
    "Frasco",
    "Caja",
    "Par",
    "Paquete",
    "Litro",
    "Kilogramo",
)

ProductCode = texto_obligatorio(
    max_length=40,
    mensaje_requerido="Ingresa el código del producto.",
    mensaje_longitud="El código admite hasta 40 caracteres.",
    mayusculas=True,
)

ProductName = texto_obligatorio(
    max_length=160,
    mensaje_requerido="Ingresa el nombre del producto.",
    mensaje_longitud="El nombre admite hasta 160 caracteres.",
)

ProductDescription = texto_obligatorio(
    max_length=1000,
    mensaje_requerido="Describe el producto y su uso.",
    mensaje_longitud="La descripción admite hasta 1000 caracteres.",
)

CategoryReference = texto_obligatorio(
    max_length=100,
    mensaje_requerido="Selecciona una categoría.",
    mensaje_longitud="La categoría no es válida.",
)

MeasurementUnit = texto_obligatorio(
    max_length=30,
    mensaje_requerido="Selecciona la unidad de medida.",
    mensaje_longitud="La unidad de medida no es válida.",
)

MinStock = entero(
    minimo=0,
    maximo=MAX_SQL_INT,
    mensaje="El stock mínimo debe ser un número entero igual o mayor que cero.",
)

UnitPrice = precio(
    mensaje="El precio debe ser un número mayor que cero.",
    mensaje_decimales="El precio admite como máximo dos decimales.",
    mensaje_maximo="El precio no puede superar 9999999999.99.",
)


class ProductInput(ApiInput):
    """Datos que el frontend envía al crear o reemplazar un producto."""

    code: ProductCode
    name: ProductName
    description: ProductDescription
    category_id: CategoryReference
    unit: MeasurementUnit
    unit_price: UnitPrice
    min_stock: MinStock
    tracks_expiration: StrictBool
    expiration_date: ISODate | None = Field(default=None, validate_default=True)

    @model_validator(mode="before")
    @classmethod
    def _completar_vencimiento(cls, data: Any) -> Any:
        """Incluye ``expirationDate`` ausente para que el error use el alias."""
        if not isinstance(data, dict):
            return data
        if "expirationDate" in data or "expiration_date" in data:
            return data
        return {**data, "expirationDate": None}

    @field_validator("unit")
    @classmethod
    def _validar_unidad(cls, value: str) -> str:
        if value not in MEASUREMENT_UNITS:
            raise PydanticCustomError(
                "unit",
                "Selecciona una unidad de medida válida.",
            )
        return value

    @field_validator("expiration_date")
    @classmethod
    def _coherencia_vencimiento(cls, value: object, info: ValidationInfo) -> object:
        datos = info.data
        controla = datos.get("tracks_expiration")
        if controla is None:
            # El propio campo tracksExpiration ya falló; no se acumulan errores.
            return value
        if not controla:
            # Igual que el formulario y el servicio de la demo: sin control de
            # vencimiento la fecha de referencia no se conserva.
            return None
        if value is None:
            raise PydanticCustomError(
                "expiration_required",
                "Selecciona la fecha de vencimiento del producto.",
            )
        return value


class ProductCreate(ProductInput):
    """Cuerpo de ``POST /products``."""


class ProductUpdate(ProductInput):
    """Cuerpo de ``PUT /products/{id}``; reemplaza la ficha completa."""


class ProductStatusUpdate(ApiInput):
    """Cuerpo de ``PATCH /products/{id}/status``."""

    active: StrictBool


class ProductResponse(ApiResponse):
    """Producto tal como lo espera la interfaz Angular."""

    id: Identifier
    code: str
    name: str
    description: str
    category_id: Identifier
    unit: str
    unit_price: float
    min_stock: int
    tracks_expiration: bool
    expiration_date: ISODate | None
    active: bool


__all__ = [
    "MEASUREMENT_UNITS",
    "ProductCode",
    "ProductCreate",
    "ProductDescription",
    "ProductInput",
    "ProductName",
    "ProductResponse",
    "ProductStatusUpdate",
    "ProductUpdate",
    "UnitPrice",
]
