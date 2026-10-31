"""Chequeos estáticos del procedimiento; no sustituye integración SQL real."""
from __future__ import annotations

from pathlib import Path

SQL_PATH = Path(__file__).resolve().parents[1] / "db" / "12_procedures_movements.sql"


def read_sql():
    return SQL_PATH.read_text(encoding="utf-8")


def test_procedimiento_reproducible_sin_ddl_destructivo():
    sql = read_sql().upper()
    assert "CREATE OR ALTER PROCEDURE DBO.USP_REGISTRARMOVIMIENTO" in sql
    assert "DROP TABLE" not in sql and "DROP DATABASE" not in sql
    assert "CREATE LOGIN" not in sql and "PASSWORD=" not in sql
    assert sql.count("\nGO") >= 3


def test_transacciones_rollback_y_bloqueo_por_producto():
    sql = read_sql().upper()
    assert "BEGIN TRANSACTION" in sql and "COMMIT TRANSACTION" in sql
    assert "ROLLBACK TRANSACTION" in sql and "SET XACT_ABORT ON" in sql
    assert "PRODUCTS WITH (UPDLOCK, HOLDLOCK)" in sql
    assert sql.index("PRODUCTS WITH (UPDLOCK, HOLDLOCK)") < sql.index("LOTS WITH (UPDLOCK, HOLDLOCK)")


def test_stock_por_lote_y_snapshots_totales():
    sql = read_sql().upper()
    assert "SUM(CONVERT(BIGINT, STOCK))" in sql
    assert "STOCK = STOCK + @QUANTITY" in sql
    assert "STOCK = STOCK - @QUANTITY" in sql
    assert "STOCK >= @QUANTITY" in sql
    assert "STOCK_BEFORE" in sql and "STOCK_AFTER" in sql
    assert "2147483647" in sql


def test_contrato_lotes_vencimientos_y_salidas():
    sql = read_sql().upper()
    assert "@EXPIRATION_DATE < @MOVEMENT_DATE" in sql
    assert "@EXPIRATION_DATE < CONVERT(DATE, SYSDATETIME())" in sql
    assert "@EXISTING_EXPIRATION" in sql
    assert "@AREA_ID" in sql and "HOSPITALAREAS" in sql
    assert "LATIN1_GENERAL_BIN2" in sql
    assert "INNER JOIN DBO.LOTS" in sql


def test_no_hay_clave_de_idempotencia_inventada():
    sql = read_sql().lower()
    assert "limitación conocida" in sql
    assert "idempotencia" in sql
