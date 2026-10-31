"""Etapa 9: reglas locales de IDs sin conexión con SQL Server."""
from __future__ import annotations

from uuid import uuid4

import pytest

from backend.core.exceptions import InventoryInvalidReferenceError, InventoryNotFoundError
from backend.schemas.category import CategoryCreate
from backend.schemas.product import ProductCreate, ProductStatusUpdate, ProductUpdate
from backend.services.inventory_write_service import InventoryWriteService

CAT = str(uuid4())
PRODUCT = str(uuid4())


class FakeRepository:
    def __init__(self):
        self.calls = []

    def create_category(self, data):
        self.calls.append(("category", data))
        return "category-created"

    def create_product(self, data):
        self.calls.append(("product", data))
        return "product-created"

    def update_product(self, product_id, data):
        self.calls.append(("update", product_id, data))
        return "product-updated"

    def set_product_status(self, product_id, active):
        self.calls.append(("status", product_id, active))


def payload(cls=ProductCreate, category_id=CAT):
    return cls.model_validate({
        "code": "MED-1", "name": "Producto", "description": "Descripción",
        "categoryId": category_id, "unit": "Unidad", "unitPrice": 1.25,
        "minStock": 0, "tracksExpiration": False, "expirationDate": None,
    })


def test_crea_categoria_delegando_a_repositorio():
    repo = FakeRepository()
    service = InventoryWriteService(repo)
    data = CategoryCreate(name="Nueva", description="Descripción")
    assert service.create_category(data) == "category-created"
    assert repo.calls == [("category", data)]


def test_crear_y_actualizar_producto_normaliza_uuid_sin_mutar_input():
    repo = FakeRepository()
    service = InventoryWriteService(repo)
    data = payload(category_id=CAT.upper())
    assert service.create_product(data) == "product-created"
    assert repo.calls[-1][1].category_id == CAT
    assert data.category_id == CAT.upper()
    updated = payload(ProductUpdate, category_id=CAT.upper())
    assert service.update_product(PRODUCT.upper(), updated) == "product-updated"
    assert repo.calls[-1][1] == PRODUCT
    assert repo.calls[-1][2].category_id == CAT


def test_estado_pasa_booleano_y_uuid_al_repositorio():
    repo = FakeRepository()
    InventoryWriteService(repo).set_product_status(
        PRODUCT.upper(), ProductStatusUpdate(active=False)
    )
    assert repo.calls == [("status", PRODUCT, False)]


@pytest.mark.parametrize("operation", ["create", "update"])
def test_categoria_invalida_rechazada_antes_del_repo(operation):
    repo = FakeRepository()
    service = InventoryWriteService(repo)
    with pytest.raises(InventoryInvalidReferenceError) as excinfo:
        if operation == "create":
            service.create_product(payload(category_id="no-es-uuid"))
        else:
            service.update_product(PRODUCT, payload(ProductUpdate, category_id="no-es-uuid"))
    assert excinfo.value.field == "categoryId"
    assert repo.calls == []


@pytest.mark.parametrize("operation", ["update", "status"])
def test_producto_id_invalido_es_404_sin_consultar_repositorio(operation):
    repo = FakeRepository()
    service = InventoryWriteService(repo)
    with pytest.raises(InventoryNotFoundError):
        if operation == "update":
            service.update_product("x", payload(ProductUpdate))
        else:
            service.set_product_status("x", ProductStatusUpdate(active=True))
    assert repo.calls == []
