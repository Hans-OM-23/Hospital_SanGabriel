"""Modelos de la comprobación de estado del servicio."""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Respuesta de GET /health."""

    status: Literal["ok"] = "ok"
    service: str
    version: str
