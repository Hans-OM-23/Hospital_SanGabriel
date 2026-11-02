"""Modelos Pydantic de entrada y salida de la API.

Se reexportan los schemas por comodidad de las capas ``apis`` y ``services``.
Los modelos solo validan forma y coherencia básica: no acceden a la base de
datos ni aplican reglas de inventario que dependan de datos persistidos.
"""

from backend.schemas.area import HospitalAreaResponse
from backend.schemas.auth import (
    AccessToken,
    AuthenticatedUser,
    EmailAddress,
    LoginRequest,
    LoginResponse,
    Password,
    UserRole,
)
from backend.schemas.category import (
    CategoryCreate,
    CategoryDescription,
    CategoryName,
    CategoryResponse,
)
from backend.schemas.common import ApiInput, ApiModel, ApiResponse, Identifier, ISODate
from backend.schemas.health import HealthResponse
from backend.schemas.lot import LotResponse
from backend.schemas.movement import (
    ENTRY_REASONS,
    MovementCreate,
    MovementResponse,
    MovementType,
    Quantity,
)
from backend.schemas.product import (
    MEASUREMENT_UNITS,
    ProductCreate,
    ProductInput,
    ProductResponse,
    ProductStatusUpdate,
    ProductUpdate,
)

__all__ = [
    "ENTRY_REASONS",
    "MEASUREMENT_UNITS",
    "AccessToken",
    "ApiInput",
    "ApiModel",
    "ApiResponse",
    "AuthenticatedUser",
    "CategoryCreate",
    "CategoryDescription",
    "CategoryName",
    "CategoryResponse",
    "EmailAddress",
    "HealthResponse",
    "HospitalAreaResponse",
    "ISODate",
    "Identifier",
    "LoginRequest",
    "LoginResponse",
    "LotResponse",
    "MovementCreate",
    "MovementResponse",
    "MovementType",
    "Password",
    "ProductCreate",
    "ProductInput",
    "ProductResponse",
    "ProductStatusUpdate",
    "ProductUpdate",
    "Quantity",
    "UserRole",
]
