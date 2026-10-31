"""Configuración de la aplicación leída desde variables de entorno."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# config.py -> core -> backend (paquete) -> src -> backend (raíz del proyecto)
BACKEND_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Parámetros generales del servicio.

    En esta etapa solo cubre la identidad de la API y los orígenes CORS.
    Las variables de SQL Server se incorporarán al conectar la base de datos.
    No se definen variables de puerto: el servidor se inicia por línea de comandos.
    """

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "API Inventario Hospital San Gabriel"
    app_version: str = "0.1.0"
    api_prefix: str = "/api"
    cors_origins: str = "http://localhost:4200,http://127.0.0.1:4200"

    @property
    def cors_origin_list(self) -> list[str]:
        """Orígenes permitidos para el frontend Angular, sin espacios vacíos."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Devuelve una única instancia de la configuración."""
    return Settings()
