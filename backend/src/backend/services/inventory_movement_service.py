"""Validación de referencias del registro de movimientos, sin SQL en servicios."""

from __future__ import annotations

from uuid import UUID

from backend.core.exceptions import InventoryInvalidReferenceError
from backend.repositories.inventory_movements import InventoryMovementRepository
from backend.schemas.movement import MovementCreate, MovementResponse, MovementType


def _uuid(value: str, field: str, message: str) -> str:
    try:
        return str(UUID(value))
    except (TypeError, ValueError, AttributeError):
        raise InventoryInvalidReferenceError(message, field=field) from None


class InventoryMovementService:
    def __init__(self, repository: InventoryMovementRepository) -> None:
        self._repository = repository

    def register_movement(self, data: MovementCreate) -> MovementResponse:
        product_id = _uuid(data.product_id, "productId", "Selecciona un producto activo.")
        changes: dict[str, object] = {"product_id": product_id}
        if data.type is MovementType.EXIT:
            # El lote y el área reales siempre se resuelven por UUID desde el servidor.
            changes["lot_id"] = _uuid(
                data.lot_id, "lotId", "Selecciona manualmente un lote del producto."
            )
            changes["area_id"] = _uuid(
                data.area_id, "areaId", "Selecciona un área hospitalaria válida."
            )
        else:
            # La ficha del producto decide si necesita vencimiento y si debe
            # ignorarse la fecha enviada: se valida en el procedimiento.
            changes["lot_id"] = None
            changes["area_id"] = None
        return self._repository.register_movement(data.model_copy(update=changes))


__all__ = ["InventoryMovementService"]
