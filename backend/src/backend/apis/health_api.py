"""Endpoint de comprobación de estado del servidor."""

from fastapi import APIRouter, Depends

from backend.core.config import Settings, get_settings
from backend.schemas.health import HealthResponse
from backend.services.health_service import HealthService

router = APIRouter(tags=["salud"])


def get_health_service(settings: Settings = Depends(get_settings)) -> HealthService:
    """Construye el servicio con la configuración de la aplicación."""
    return HealthService(settings)


@router.get("/health", response_model=HealthResponse, summary="Estado del servidor")
def health(service: HealthService = Depends(get_health_service)) -> HealthResponse:
    """Confirma que la API está en ejecución."""
    return service.check()
