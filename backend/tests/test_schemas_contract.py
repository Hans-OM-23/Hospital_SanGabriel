"""Correspondencia estricta entre los schemas y las interfaces TypeScript.

Cada conjunto de propiedades debe coincidir con la interfaz declarada en
``frontend/docs/API-CONTRACT.md`` y en ``frontend/src/app/**/interface/*.ts``.
Si alguien renombra un campo, estas pruebas fallan antes de romper Angular.
"""

from __future__ import annotations

import pytest

from backend.schemas.area import HospitalAreaResponse
from backend.schemas.auth import AuthenticatedUser, LoginRequest, LoginResponse
from backend.schemas.category import CategoryCreate, CategoryResponse
from backend.schemas.lot import LotResponse
from backend.schemas.movement import MovementCreate, MovementResponse
from backend.schemas.product import ProductCreate, ProductResponse

CAMPOS_PRODUCT = {
    "id",
    "code",
    "name",
    "description",
    "categoryId",
    "unit",
    "unitPrice",
    "minStock",
    "tracksExpiration",
    "expirationDate",
    "active",
}

CAMPOS_PRODUCT_INPUT = CAMPOS_PRODUCT - {"id", "active"}

CAMPOS_MOVEMENT = {
    "id",
    "type",
    "productId",
    "quantity",
    "date",
    "reason",
    "stockBefore",
    "stockAfter",
    "lotId",
    "lotNumber",
    "expirationDate",
    "areaId",
}

CAMPOS_MOVEMENT_INPUT = {
    "type",
    "productId",
    "quantity",
    "date",
    "reason",
    "lotId",
    "lotNumber",
    "expirationDate",
    "areaId",
}


@pytest.mark.parametrize(
    ("modelo", "esperado"),
    [
        (ProductCreate, CAMPOS_PRODUCT_INPUT),
        (ProductResponse, CAMPOS_PRODUCT),
        (CategoryCreate, {"name", "description"}),
        (CategoryResponse, {"id", "name", "description", "active"}),
        (LotResponse, {"id", "productId", "number", "expirationDate", "stock"}),
        (HospitalAreaResponse, {"id", "name"}),
        (MovementCreate, CAMPOS_MOVEMENT_INPUT),
        (MovementResponse, CAMPOS_MOVEMENT),
        (LoginRequest, {"email", "password"}),
        (AuthenticatedUser, {"id", "name", "email", "role"}),
        (LoginResponse, {"accessToken", "user"}),
    ],
)
def test_propiedades_del_schema_coinciden_con_typescript(modelo: type, esperado: set[str]) -> None:
    assert set(modelo.model_json_schema()["properties"]) == esperado


@pytest.mark.parametrize(
    ("modelo", "campo"),
    [
        (ProductCreate, "categoryId"),
        (ProductCreate, "unitPrice"),
        (ProductCreate, "minStock"),
        (ProductCreate, "tracksExpiration"),
        (ProductCreate, "expirationDate"),
        (MovementCreate, "productId"),
        (MovementCreate, "lotId"),
        (MovementCreate, "lotNumber"),
        (MovementCreate, "expirationDate"),
        (MovementCreate, "areaId"),
        (MovementResponse, "stockBefore"),
        (MovementResponse, "stockAfter"),
        (LoginResponse, "accessToken"),
    ],
)
def test_los_alias_son_camel_case_sin_guiones_bajos(modelo: type, campo: str) -> None:
    propiedades = set(modelo.model_json_schema()["properties"])

    assert campo in propiedades
    assert "_" not in campo
