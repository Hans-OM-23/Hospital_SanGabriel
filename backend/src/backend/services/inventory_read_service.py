"""Servicios de lectura del inventario, sin consultas SQL en la capa HTTP.

Los métodos delegan a procedimientos almacenados a través del repositorio.
Las escrituras, el stock y las transacciones se gestionan en servicios y procedimientos independientes.
"""

from __future__ import annotations

from backend.repositories.inventory_read import InventoryReadRepository
from backend.schemas.area import HospitalAreaResponse
from backend.schemas.category import CategoryResponse
from backend.schemas.lot import LotResponse
from backend.schemas.movement import MovementResponse
from backend.schemas.product import ProductResponse


class InventoryReadService:
    """Fachada de las cinco lecturas definidas en API-CONTRACT.md."""

    def __init__(self, repository: InventoryReadRepository) -> None:
        self._repository = repository

    def list_products(self) -> list[ProductResponse]:
        return self._repository.list_products()

    def list_categories(self) -> list[CategoryResponse]:
        return self._repository.list_categories()

    def list_lots(self) -> list[LotResponse]:
        return self._repository.list_lots()

    def list_areas(self) -> list[HospitalAreaResponse]:
        return self._repository.list_areas()

    def list_movements(self) -> list[MovementResponse]:
        # El procedimiento usp_ListarMovimientos ya devuelve movement_seq ASC.
        # No reordenar: Angular resuelve la presentación del historial.
        return self._repository.list_movements()


__all__ = ["InventoryReadService"]
