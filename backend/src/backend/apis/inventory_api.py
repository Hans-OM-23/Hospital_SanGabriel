"""Endpoints de consulta que consume Angular bajo /api.

La autenticación Bearer se exige para TODAS las rutas del router.
No hay queries directas ni datos de prueba en la aplicación: cada lectura
pasa por el servicio y el repositorio de procedimientos almacenados.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.apis.dependencies import require_responsable_almacen
from backend.core.config import Settings, get_settings
from backend.core.database import Database
from backend.repositories.inventory_read import InventoryReadRepository
from backend.schemas.area import HospitalAreaResponse
from backend.schemas.category import CategoryResponse
from backend.schemas.lot import LotResponse
from backend.schemas.movement import MovementResponse
from backend.schemas.product import ProductResponse
from backend.services.inventory_read_service import InventoryReadService

router = APIRouter(
    tags=["inventario"],
    dependencies=[Depends(require_responsable_almacen)],
)


def get_inventory_read_service(
    settings: Settings = Depends(get_settings),
) -> InventoryReadService:
    """Construye las capas por solicitud y sin abrir conexiones al importar.

    SQL Server se abre únicamente al invocar un método del repositorio.
    FastAPI permite sustituir esta dependencia en tests sin conectar a la BD.
    """
    return InventoryReadService(InventoryReadRepository(Database(settings)))


@router.get("/products", response_model=list[ProductResponse], summary="Listar productos")
def list_products(
    service: InventoryReadService = Depends(get_inventory_read_service),
) -> list[ProductResponse]:
    """Incluye productos inactivos para interpretar movimientos históricos."""
    return service.list_products()


@router.get("/categories", response_model=list[CategoryResponse], summary="Listar categorías")
def list_categories(
    service: InventoryReadService = Depends(get_inventory_read_service),
) -> list[CategoryResponse]:
    return service.list_categories()


@router.get("/lots", response_model=list[LotResponse], summary="Listar lotes")
def list_lots(
    service: InventoryReadService = Depends(get_inventory_read_service),
) -> list[LotResponse]:
    return service.list_lots()


@router.get("/areas", response_model=list[HospitalAreaResponse], summary="Listar áreas")
def list_areas(
    service: InventoryReadService = Depends(get_inventory_read_service),
) -> list[HospitalAreaResponse]:
    return service.list_areas()


@router.get("/movements", response_model=list[MovementResponse], summary="Listar movimientos")
def list_movements(
    service: InventoryReadService = Depends(get_inventory_read_service),
) -> list[MovementResponse]:
    return service.list_movements()


__all__ = ["router", "get_inventory_read_service"]
