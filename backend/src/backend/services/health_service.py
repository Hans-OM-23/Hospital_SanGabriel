"""Servicio de comprobación de estado del backend."""

from backend.core.config import Settings
from backend.schemas.health import HealthResponse


class HealthService:
    """Informa si el servidor está operativo.

    Todavía no consulta SQL Server: la base de datos se conectará en una etapa
    posterior. La prueba de salud solo confirma que FastAPI responde.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def check(self) -> HealthResponse:
        return HealthResponse(
            status="ok",
            service=self._settings.app_name,
            version=self._settings.app_version,
        )
