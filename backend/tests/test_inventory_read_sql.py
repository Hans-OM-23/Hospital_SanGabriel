"""Verificación ESTÁTICA de los scripts SQL de la etapa 7 (sin ejecutarlos)."""

from __future__ import annotations

import re
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "db" / "10_procedures_read.sql"


def test_los_cinco_procedimientos_existen_y_no_aceptan_parametros():
    sql = SCRIPT.read_text(encoding="utf-8")
    names = re.findall(r"(?im)^CREATE OR ALTER PROCEDURE\s+dbo\.(\w+)\s*\nAS\s*\n", sql)
    assert names == [
        "usp_ListarProductos", "usp_ListarCategorias", "usp_ListarLotes",
        "usp_ListarAreas", "usp_ListarMovimientos",
    ]
    # Cada CREATE/ALTER se aísla con GO para SSMS/sqlcmd.
    assert sql.count("\nGO\n") >= 6


def test_historial_usa_secuencia_ascendente_y_join_lote_producto():
    sql = SCRIPT.read_text(encoding="utf-8")
    block = sql.split("CREATE OR ALTER PROCEDURE dbo.usp_ListarMovimientos", 1)[1]
    assert "ORDER BY m.movement_seq ASC" in block
    assert "l.lot_id = m.lot_id" in block
    assert "l.product_id = m.product_id" in block
    assert "l.number AS lot_number" in block
    assert "m.movement_date AS date" in block


def test_procedimientos_de_lectura_no_tienen_dml_ni_crean_cuentas():
    sql = SCRIPT.read_text(encoding="utf-8")
    # Los comentarios pueden nombrar operaciones; comprobar únicamente el SQL
    # dentro de cada bloque BEGIN/END del procedimiento.
    statements = re.findall(r"(?is)CREATE OR ALTER PROCEDURE\b.*?\bAS\s*\nBEGIN\s*(.*?)\nEND;", sql)
    assert len(statements) == 5
    for text in statements:
        assert re.search(r"\bSELECT\b", text, re.I)
        assert not re.search(
            r"\b(?:INSERT|UPDATE|DELETE|MERGE|DROP|GRANT|DENY|CREATE\s+LOGIN)\b", text, re.I
        )
