"""Etapa 8: servicio de inventario con repositorio aislado (sin SQL Server)."""

from __future__ import annotations

from datetime import date

import pytest

from backend.core.exceptions import DatabaseConnectionError
from backend.schemas.area import HospitalAreaResponse
from backend.schemas.category import CategoryResponse
from backend.schemas.lot import LotResponse
from backend.schemas.movement import MovementResponse
from backend.schemas.product import ProductResponse
from backend.services.inventory_read_service import InventoryReadService


class FakeReadRepository:
    def __init__(self) -> None:
        self.called: list[str] = []

    def list_products(self):
        self.called.append("products")
        return [ProductResponse(id="p-1", code="MED-001", name="Paracetamol",
                                description="Tabletas", category_id="c-1", unit="Tableta",
                                unit_price=0.5, min_stock=5, tracks_expiration=False,
                                expiration_date=None, active=False)]

    def list_categories(self):
        self.called.append("categories")
        return [CategoryResponse(id="c-1", name="Medicamentos", description="Fármacos", active=True)]

    def list_lots(self):
        self.called.append("lots")
        return [LotResponse(id="l-1", product_id="p-1", number="PAR-001",
                            expiration_date=date(2027, 4, 5), stock=10)]

    def list_areas(self):
        self.called.append("areas")
        return [HospitalAreaResponse(id="a-1", name="Emergencia")]

    def list_movements(self):
        self.called.append("movements")
        return [MovementResponse(id="m-1", type="entry", product_id="p-1", quantity=10,
                                 date=date(2026, 10, 30), reason="Compra", stock_before=0,
                                 stock_after=10, lot_id="l-1", lot_number="PAR-001",
                                 expiration_date=date(2027, 4, 5), area_id=None)]


@pytest.mark.parametrize("method,repo_name,schema", [
    ("list_products", "products", ProductResponse),
    ("list_categories", "categories", CategoryResponse),
    ("list_lots", "lots", LotResponse),
    ("list_areas", "areas", HospitalAreaResponse),
    ("list_movements", "movements", MovementResponse),
])
def test_servicio_delega_sin_consultar_sql(method: str, repo_name: str, schema: type) -> None:
    repo = FakeReadRepository()
    service = InventoryReadService(repo)
    result = getattr(service, method)()
    assert len(result) == 1
    assert isinstance(result[0], schema)
    assert repo.called == [repo_name]


def test_servicio_no_ordena_de_nuevo_movimientos() -> None:
    class Fake(FakeReadRepository):
        def list_movements(self):
            first = super().list_movements()[0]
            second = first.model_copy(update={"id": "m-2"})
            return [first, second]

    result = InventoryReadService(Fake()).list_movements()
    assert [m.id for m in result] == ["m-1", "m-2"]


def test_servicio_no_oculta_errores_de_repositorio() -> None:
    class Broken(FakeReadRepository):
        def list_products(self):
            raise DatabaseConnectionError("Sin conexión")

    with pytest.raises(DatabaseConnectionError):
        InventoryReadService(Broken()).list_products()
