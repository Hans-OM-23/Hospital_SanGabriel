"""Enrutador agregado de la API bajo el prefijo /api.

Las rutas de lectura y escritura de inventario requieren un JWT válido.
El login es público; las operaciones de inventario requieren JWT.
"""

from fastapi import APIRouter

from backend.apis.auth_api import router as auth_router
from backend.apis.inventory_api import router as inventory_router
from backend.core.config import get_settings

api_router = APIRouter(prefix=get_settings().api_prefix)
api_router.include_router(auth_router)
api_router.include_router(inventory_router)
