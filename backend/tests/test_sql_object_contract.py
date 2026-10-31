"""Comprueba que cada EXEC del repositorio coincide con los scripts SQL.

No requiere SQL Server y detecta procedimientos ausentes, nombres de
parámetros incorrectos y cambios accidentales en el contrato Python/SQL.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from backend.repositories.inventory_movements import InventoryMovementRepository
from backend.repositories.inventory_read import InventoryReadRepository
from backend.repositories.inventory_write import InventoryWriteRepository
from backend.repositories.users import SqlServerUserRepository

DB_DIR = Path(__file__).resolve().parents[1] / "db"
PROCEDURE_SCRIPTS = (
    "10_procedures_read.sql", "11_procedures_catalog_write.sql",
    "12_procedures_movements.sql", "13_procedures_users.sql",
)


def _signatures() -> dict[str, tuple[str, ...]]:
    result: dict[str, tuple[str, ...]] = {}
    regex = re.compile(
        r"CREATE\s+OR\s+ALTER\s+PROCEDURE\s+dbo\.(usp_\w+)\s*(.*?)\s*\bAS\b",
        re.I | re.S,
    )
    for file in PROCEDURE_SCRIPTS:
        content = (DB_DIR / file).read_text(encoding="utf-8-sig")
        for name, params in regex.findall(content):
            assert name not in result, f"Procedimiento duplicado: {name}"
            result[name] = tuple(re.findall(r"(?m)^\s*@([a-zA-Z_]\w*)\s", params))
    return result


COMMANDS = (
    InventoryReadRepository._PRODUCTS,
    InventoryReadRepository._CATEGORIES,
    InventoryReadRepository._LOTS,
    InventoryReadRepository._AREAS,
    InventoryReadRepository._MOVEMENTS,
    InventoryWriteRepository._CREATE_CATEGORY,
    InventoryWriteRepository._CREATE_PRODUCT,
    InventoryWriteRepository._UPDATE_PRODUCT,
    InventoryWriteRepository._CHANGE_STATUS,
    InventoryMovementRepository._REGISTER,
    SqlServerUserRepository._BY_EMAIL,
    SqlServerUserRepository._BY_ID,
)


@pytest.mark.parametrize("command", COMMANDS)
def test_repositorio_usa_procedimiento_existente_y_parametros_en_orden(command: str):
    match = re.fullmatch(r"EXEC\s+dbo\.(usp_\w+)(?:\s+(.*))?", command, re.I | re.S)
    assert match is not None, f"El repositorio no utiliza EXEC: {command}"
    procedure, params = match.group(1), match.group(2) or ""
    signature = _signatures()
    assert procedure in signature, f"Procedimiento faltante: {procedure}"
    declared = signature[procedure]
    supplied = tuple(re.findall(r"@([a-zA-Z_]\w*)\s*=\s*\?", params))
    assert supplied == declared, f"Parámetros de {procedure}: Python={supplied}, SQL={declared}"
    assert params.count("?") == len(supplied)


def test_se_incluyen_todos_los_procedimientos_requeridos():
    from backend.core.sql_readiness import EXPECTED_PROCEDURES

    signatures = _signatures()
    assert set(signatures) == EXPECTED_PROCEDURES
    called = set()
    for command in COMMANDS:
        match = re.search(r"EXEC\s+dbo\.(usp_\w+)", command)
        assert match is not None
        called.add(match.group(1))
    assert called == EXPECTED_PROCEDURES
