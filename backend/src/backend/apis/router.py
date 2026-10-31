"""Enrutador agregado de la API bajo el prefijo /api.

En la siguiente etapa se incluirán aquí los routers de autenticación,
productos, categorías, lotes, áreas y movimientos.
"""

from fastapi import APIRouter

from backend.core.config import get_settings

api_router = APIRouter(prefix=get_settings().api_prefix)
