"""Endpoints GET/POST/PUT/PATCH de inventario según contrato Angular.

Todas las rutas requieren Bearer JWT con el rol Responsable de almacén.
Los servicios delegan exclusivamente a repositorios de procedimientos
almacenados; no se ejecuta SQL directo desde esta capa HTTP.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from backend.apis.dependencies import require_responsable_almacen
from backend.core.config import Settings, get_settings
from backend.core.database import Database
from backend.repositories.inventory_read import InventoryReadRepository
from backend.repositories.inventory_write import InventoryWriteRepository
from backend.schemas.area import HospitalAreaResponse
from backend.schemas.category import CategoryCreate, CategoryResponse
from backend.schemas.lot import LotResponse
from backend.schemas.movement import MovementResponse
from backend.schemas.product import ProductCreate, ProductResponse, ProductStatusUpdate, ProductUpdate
from backend.services.inventory_read_service import InventoryReadService
from backend.services.inventory_write_service import InventoryWriteService

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




def get_inventory_write_service(
    settings: Settings = Depends(get_settings),
) -> InventoryWriteService:
    """Inyección real de transacciones SQL; sustituible en pruebas sin SQL."""
    return InventoryWriteService(InventoryWriteRepository(Database(settings)))


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED,
             summary="Crear categoría")
def create_category(
    data: CategoryCreate,
    service: InventoryWriteService = Depends(get_inventory_write_service),
) -> CategoryResponse:
    return service.create_category(data)


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED,
             summary="Crear producto")
def create_product(
    data: ProductCreate,
    service: InventoryWriteService = Depends(get_inventory_write_service),
) -> ProductResponse:
    return service.create_product(data)


@router.put("/products/{product_id}", response_model=ProductResponse,
            summary="Actualizar ficha de producto")
def update_product(
    product_id: str,
    data: ProductUpdate,
    service: InventoryWriteService = Depends(get_inventory_write_service),
) -> ProductResponse:
    return service.update_product(product_id, data)


@router.patch("/products/{product_id}/status", status_code=status.HTTP_204_NO_CONTENT,
              summary="Activar o desactivar producto")
def change_product_status(
    product_id: str,
    data: ProductStatusUpdate,
    service: InventoryWriteService = Depends(get_inventory_write_service),
) -> Response:
    service.set_product_status(product_id, data)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router", "get_inventory_read_service", "get_inventory_write_service"]
