"""Schema de áreas hospitalarias.

La interfaz ``HospitalArea`` solo tiene ``id`` y ``name``. El catálogo es de
solo lectura para la aplicación: no existe endpoint de alta ni de baja.
"""

from __future__ import annotations

from backend.schemas.common import ApiResponse, Identifier


class HospitalAreaResponse(ApiResponse):
    """Área hospitalaria de destino de una salida."""

    id: Identifier
    name: str


__all__ = ["HospitalAreaResponse"]
