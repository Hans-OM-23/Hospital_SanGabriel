"""Auditoría estática de SQL en etapa 9 (sin ejecutar SQL Server)."""

from pathlib import Path
import re

SQL = Path(__file__).resolve().parents[1] / "db" / "11_procedures_catalog_write.sql"


def body():
    return SQL.read_text(encoding="utf-8")


def test_crea_cuatro_procedimientos_y_no_modifica_tablas_directamente():
    text = body()
    for name in (
        "usp_CrearCategoria", "usp_CrearProducto",
        "usp_ActualizarProducto", "usp_CambiarEstadoProducto",
    ):
        assert f"CREATE OR ALTER PROCEDURE dbo.{name}" in text
    assert len(re.findall(r"CREATE OR ALTER PROCEDURE", text)) == 4
    assert "USE [HospitalSanGabriel]" in text
    assert "USE [master]" not in text
    assert "CREATE LOGIN" not in text.upper()
    assert "DROP TABLE" not in text.upper()


def test_todas_las_escrituras_son_transaccionales_y_con_xact_abort():
    sql = body()
    sections = re.split(r"CREATE OR ALTER PROCEDURE dbo\.", sql)[1:]
    assert len(sections) == 4
    for section in sections:
        for fragment in ("SET NOCOUNT ON", "SET XACT_ABORT ON", "BEGIN TRANSACTION",
                         "COMMIT TRANSACTION", "ROLLBACK TRANSACTION", "BEGIN TRY", "BEGIN CATCH"):
            assert fragment in section


def test_reglas_criticas_estan_documentadas_en_sql():
    sql = body()
    for fragment in (
        "WITH (UPDLOCK, HOLDLOCK)",
        "FROM dbo.Movements WHERE product_id = @product_id",
        "@old_unit <> @unit", "@old_tracks_expiration <> @tracks_expiration",
        "active = 1", "@code = UPPER(LTRIM(RTRIM(@code)))",
        "updated_at = SYSDATETIME()", "THROW 51011", "THROW 51012",
        "THROW 51013", "THROW 51014", "THROW 51015", "THROW 51016",
    ):
        assert fragment in sql
    assert not re.search(r"(?i)PASSWORD\s*=", sql)
