"""Configuración de la aplicación leída desde variables de entorno."""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# config.py -> core -> backend (paquete) -> src -> backend (raíz del proyecto)
BACKEND_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Parámetros generales del servicio.

    Las variables de SQL Server usan autenticación propia de SQL Server
    (usuario y contraseña), nunca autenticación integrada de Windows.
    No se definen variables de puerto: el servidor se inicia por línea de
    comandos y, si se requiere TCP, el puerto forma parte de DB_SERVER.
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

    db_server: str = ""
    db_name: str = ""
    db_user: str = ""
    db_password: SecretStr = SecretStr("")
    db_driver: str = "ODBC Driver 18 for SQL Server"
    db_encrypt: str = "yes"
    db_trust_server_certificate: str = "no"

    @field_validator("db_driver")
    @classmethod
    def _normalizar_driver(cls, value: str) -> str:
        """Acepta el nombre del controlador con o sin llaves."""
        return value.strip().strip("{}")

    @property
    def cors_origin_list(self) -> list[str]:
        """Orígenes permitidos para el frontend Angular, sin espacios vacíos."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def missing_database_settings(self) -> list[str]:
        """Nombres de las variables de conexión faltantes, nunca sus valores."""
        obligatorias = {
            "DB_SERVER": self.db_server,
            "DB_NAME": self.db_name,
            "DB_USER": self.db_user,
            "DB_PASSWORD": self.db_password.get_secret_value(),
        }
        return [nombre for nombre, valor in obligatorias.items() if not valor.strip()]

    @property
    def database_configured(self) -> bool:
        """Indica si la conexión a SQL Server está completamente configurada."""
        return not self.missing_database_settings


@lru_cache
def get_settings() -> Settings:
    """Devuelve una única instancia de la configuración."""
    return Settings()
