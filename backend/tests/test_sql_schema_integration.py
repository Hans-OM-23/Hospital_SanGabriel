"""Integración real, solo lectura y OPT-IN, para usar después de instalar SQL.

NO corre con pytest normal. Exige RUN_DB_TESTS=1 y DB_NAME=HospitalSanGabriel.
NO modifica tablas, usuarios, permisos, procedimientos ni datos de negocio.
"""

from __future__ import annotations

import os

import pytest

from backend.core.config import get_settings
from backend.core.database import Database
from backend.core.sql_readiness import format_report, inspect_sql_readiness
from backend.repositories.inventory_read import InventoryReadRepository

settings = get_settings()
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_DB_TESTS") != "1"
        or not settings.database_configured
        or settings.db_name.casefold() != "hospitalsangabriel",
        reason="Requiere RUN_DB_TESTS=1, .env SQL válido y DB_NAME=HospitalSanGabriel",
    ),
]


def test_tablas_procedimientos_restricciones_y_permisos_reales():
    report = inspect_sql_readiness(Database(settings), settings)
    assert report.ready, "\n".join(format_report(report))


def test_procedimientos_de_lectura_reales_sin_modificar_datos():
    repo = InventoryReadRepository(Database(settings))
    assert isinstance(repo.list_products(), list)
    assert isinstance(repo.list_categories(), list)
    assert isinstance(repo.list_lots(), list)
    assert isinstance(repo.list_areas(), list)
    assert isinstance(repo.list_movements(), list)
