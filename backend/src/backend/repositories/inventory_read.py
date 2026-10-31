"""Consultas de inventario vía procedimientos almacenados de SQL Server.

Etapa 7: solo lectura. Los procedimientos se definen en
``backend/db/10_procedures_read.sql`` y NO se ejecutan al importar el módulo.

No hay acceso directo a tablas desde Python, SQL dinámico, conexión en tiempo
 de importación ni datos de inventario de demostración. Los servicios y las
rutas HTTP se incorporarán en otras etapas.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

import pyodbc
from pydantic import BaseModel

from backend.core.exceptions import DatabaseConnectionError
from backend.schemas.area import HospitalAreaResponse
from backend.schemas.category import CategoryResponse
from backend.schemas.lot import LotResponse
from backend.schemas.movement import MovementResponse
from backend.schemas.product import ProductResponse

if TYPE_CHECKING:
    from backend.core.database import Database

T = TypeVar("T", bound=BaseModel)


class InventoryReadRepository:
    """Adaptador SQL Server para las cinco lecturas del contrato Angular.

    El llamador inyecta ``Database``: no se establece ninguna conexión hasta
    ejecutar una operación. Cada lectura abre y cierra su cursor mediante
    ``Database.connection()``; no realiza escrituras ni commits.
    """

    # Constantes internas, no configurables desde entradas del usuario. De
    # esta forma ningún nombre de procedimiento se concatena dinámicamente.
    _PRODUCTS = "EXEC dbo.usp_ListarProductos"
    _CATEGORIES = "EXEC dbo.usp_ListarCategorias"
    _LOTS = "EXEC dbo.usp_ListarLotes"
    _AREAS = "EXEC dbo.usp_ListarAreas"
    _MOVEMENTS = "EXEC dbo.usp_ListarMovimientos"

    def __init__(self, database: Database) -> None:
        self._database = database

    def _list(self, statement: str, schema: type[T]) -> list[T]:
        try:
            with self._database.connection() as cursor:
                cursor.execute(statement)
                # Evita asumir índices de columnas, que pueden cambiar cuando
                # evolucione el procedimiento almacenado.
                if cursor.description is None:
                    raise DatabaseConnectionError(
                        "El procedimiento de lectura no devolvió columnas."
                    )
                names = [str(column[0]) for column in cursor.description]
                if len(names) != len(set(names)):
                    raise DatabaseConnectionError(
                        "El procedimiento de lectura devolvió columnas repetidas."
                    )
                # model_validate aplica alias, valores y tipos de los schemas
                # aprobados en la etapa 5. Las fechas se devuelven como date y
                # los GUID como texto desde T-SQL.
                return [
                    schema.model_validate(dict(zip(names, row, strict=True)))
                    for row in cursor.fetchall()
                ]
        except pyodbc.Error:
            # Nunca exponer el error bruto del driver: puede contener datos
            # sensibles del servidor. La falla es de consulta, no de schema.
            raise DatabaseConnectionError(
                "No se pudieron consultar los datos del inventario."
            ) from None

    def list_products(self) -> list[ProductResponse]:
        return self._list(self._PRODUCTS, ProductResponse)

    def list_categories(self) -> list[CategoryResponse]:
        return self._list(self._CATEGORIES, CategoryResponse)

    def list_lots(self) -> list[LotResponse]:
        return self._list(self._LOTS, LotResponse)

    def list_areas(self) -> list[HospitalAreaResponse]:
        return self._list(self._AREAS, HospitalAreaResponse)

    def list_movements(self) -> list[MovementResponse]:
        return self._list(self._MOVEMENTS, MovementResponse)


__all__ = ["InventoryReadRepository"]
