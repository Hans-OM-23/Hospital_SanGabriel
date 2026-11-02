"""Reglas sin conexión SQL de alta y actualización del catálogo.

La unicidad, la existencia de la categoría y la inmutabilidad con movimientos
se verifican transaccionalmente en los procedimientos almacenados, no mediante
consultas independientes (que introducirían condiciones de carrera).
"""

from __future__ import annotations

from uuid import UUID

from backend.core.exceptions import InventoryInvalidReferenceError, InventoryNotFoundError
from backend.repositories.inventory_write import InventoryWriteRepository
from backend.schemas.category import CategoryCreate, CategoryResponse
from backend.schemas.product import (
    ProductCreate, ProductResponse, ProductStatusUpdate, ProductUpdate,
)


def _product_uuid(value: str) -> str:
    try:
        return str(UUID(value))
    except (TypeError, ValueError, AttributeError):
        raise InventoryNotFoundError("El producto ya no está disponible.") from None


def _category_uuid(value: str) -> str:
    try:
        return str(UUID(value))
    except (TypeError, ValueError, AttributeError):
        raise InventoryInvalidReferenceError(
            "Selecciona una categoría disponible.", field="categoryId"
        ) from None


class InventoryWriteService:
    def __init__(self, repository: InventoryWriteRepository) -> None:
        self._repository = repository

    def create_category(self, data: CategoryCreate) -> CategoryResponse:
        return self._repository.create_category(data)

    def create_product(self, data: ProductCreate) -> ProductResponse:
        validado = data.model_copy(update={"category_id": _category_uuid(data.category_id)})
        return self._repository.create_product(validado)

    def update_product(self, product_id: str, data: ProductUpdate) -> ProductResponse:
        producto_id = _product_uuid(product_id)
        validado = data.model_copy(update={"category_id": _category_uuid(data.category_id)})
        return self._repository.update_product(producto_id, validado)

    def set_product_status(self, product_id: str, data: ProductStatusUpdate) -> None:
        self._repository.set_product_status(_product_uuid(product_id), data.active)


__all__ = ["InventoryWriteService"]
