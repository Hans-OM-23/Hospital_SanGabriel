"""Comprobaciones del instalador de un solo archivo para SSMS (sin conexión)."""

from __future__ import annotations

import re
from pathlib import Path

DB_DIR = Path(__file__).resolve().parents[1] / "db"
INSTALLER = DB_DIR / "INSTALAR_HOSPITAL_SAN_GABRIEL.sql"
SOURCES = (
    "00_create_database.sql",
    "01_create_tables.sql",
    "02_create_indexes.sql",
    "03_seed_reference_data.sql",
    "04_seed_demo_inventory.sql",
    "10_procedures_read.sql",
    "11_procedures_catalog_write.sql",
    "12_procedures_movements.sql",
    "13_procedures_users.sql",
    "99_verify_schema.sql",
)


def _normalizar(text: str) -> str:
    return text.replace("\r\n", "\n").lstrip("\ufeff").strip()


def test_incluye_los_scripts_en_el_orden_correcto() -> None:
    content = _normalizar(INSTALLER.read_text(encoding="utf-8-sig"))
    positions = []
    for name in SOURCES:
        source = _normalizar((DB_DIR / name).read_text(encoding="utf-8-sig"))
        assert source in content, f"Instalador no incluye {name} sin cambios"
        positions.append(content.index(source))
    assert positions == sorted(positions)


def test_contiene_12_procedimientos_y_separadores_ssms() -> None:
    content = _normalizar(INSTALLER.read_text(encoding="utf-8-sig"))
    names = re.findall(r"(?im)^CREATE OR ALTER PROCEDURE dbo\.(\w+)", content)
    assert len(names) == len(set(names)) == 12
    assert len(re.findall(r"(?im)^GO\s*$", content)) >= 60


def test_cuenta_de_demostracion_solo_se_agrega_si_falta() -> None:
    content = _normalizar(INSTALLER.read_text(encoding="utf-8-sig"))
    assert "IF NOT EXISTS (SELECT 1 FROM dbo.Users" in content
    assert "admin@hospital.com" in content
    assert "argon2id" in content
    assert "DROP DATABASE" not in content.upper()
    assert "DROP TABLE" not in content.upper()


def test_el_instalador_comprueba_consistencia_con_throw() -> None:
    content = _normalizar(INSTALLER.read_text(encoding="utf-8-sig"))
    assert "SQL Server 2016 SP1+" in content
    assert "THROW 51081" in content  # saldo de lote contra movimientos
    assert "THROW 51082" in content  # secuencia de saldos por producto
    assert "THROW 51083" in content  # stock final contra lotes
