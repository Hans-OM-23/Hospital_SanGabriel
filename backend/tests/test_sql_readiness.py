"""Pruebas del diagnóstico SQL: todas usan cursores simulados."""

from __future__ import annotations

from contextlib import contextmanager
from io import StringIO
from unittest.mock import patch

import pytest

from backend.core.config import Settings
from backend.core.sql_readiness import (
    EXPECTED_CONSTRAINTS, EXPECTED_PROCEDURES, EXPECTED_TABLES,
    SqlReadinessReport, format_report, inspect_sql_readiness,
)
from scripts.check_sql_readiness import main


class FakeCursor:
    def __init__(
        self, *, tables=None, procedures=None, constraints=None,
        fk_pairs=(("lot_id", "lot_id"), ("product_id", "product_id")), permitted=True,
    ):
        self.tables = EXPECTED_TABLES if tables is None else tables
        self.procedures = EXPECTED_PROCEDURES if procedures is None else procedures
        self.constraints = EXPECTED_CONSTRAINTS if constraints is None else constraints
        self.fk_pairs = fk_pairs
        self.permitted = permitted
        self.executed = []
        self.current = []
        self.closed = False

    def execute(self, statement, *params):
        self.executed.append((statement, params))
        if "FROM sys.tables" in statement:
            self.current = [(item,) for item in self.tables]
        elif "FROM sys.procedures" in statement:
            self.current = [(item,) for item in self.procedures]
        elif "FROM sys.objects" in statement:
            self.current = [(item,) for item in self.constraints]
        elif "FROM sys.foreign_key_columns" in statement:
            self.current = list(self.fk_pairs)
        elif "HAS_PERMS_BY_NAME" in statement:
            self.current = [(1 if self.permitted else 0,)]
        else:
            raise AssertionError("Consulta no prevista")
        return self

    def fetchall(self):
        return self.current

    def fetchone(self):
        return self.current[0] if self.current else None


class FakeDatabase:
    def __init__(self, cursor):
        self.cursor = cursor
        self.opens = 0
        self.closes = 0

    @contextmanager
    def connection(self):
        self.opens += 1
        try:
            yield self.cursor
        finally:
            self.closes += 1
            self.cursor.closed = True


def settings(name="HospitalSanGabriel"):
    return Settings(
        _env_file=None, db_server="localhost", db_name=name, db_user="sql_test",
        db_password="solo_para_pruebas", jwt_secret_key="",
    )


def test_reporte_sano_revisa_objetos_fk_y_permisos():
    cursor = FakeCursor()
    db = FakeDatabase(cursor)
    report = inspect_sql_readiness(db, settings())
    assert report.ready
    assert db.opens == db.closes == 1
    assert cursor.closed
    assert len([call for call in cursor.executed if "HAS_PERMS_BY_NAME" in call[0]]) == 12
    assert all("dbo.usp_" in call[1][0] for call in cursor.executed if call[1])
    assert format_report(report)[0] == "Instalación SQL: LISTA"


def test_informa_ausencias_sin_alterar_ninguna_tabla():
    cursor = FakeCursor(
        tables=EXPECTED_TABLES - {"Lots"},
        procedures=EXPECTED_PROCEDURES - {"usp_RegistrarMovimiento"},
        constraints=EXPECTED_CONSTRAINTS - {"CK_Lots_Stock"},
        fk_pairs=(), permitted=False,
    )
    report = inspect_sql_readiness(FakeDatabase(cursor), settings())
    assert report.missing_tables == ("Lots",)
    assert report.missing_procedures == ("usp_RegistrarMovimiento",)
    assert report.missing_constraints == ("CK_Lots_Stock",)
    assert not report.composite_lot_fk_valid
    assert len(report.procedures_without_execute) == 11
    assert not report.ready
    for sql, params in cursor.executed:
        statement = sql.lstrip().upper()
        assert statement.startswith("SELECT")
        assert not any(word in statement for word in ("INSERT INTO", "UPDATE ", "DELETE FROM", "DROP ", "CREATE ", "ALTER "))
        assert all(str(p).startswith("dbo.usp_") for p in params)


def test_rechaza_master_antes_de_abrir_una_conexion():
    db = FakeDatabase(FakeCursor())
    with pytest.raises(ValueError, match="DB_NAME debe ser HospitalSanGabriel"):
        inspect_sql_readiness(db, settings("master"))
    assert db.opens == 0


def test_rechaza_fk_compuesta_parcial():
    cursor = FakeCursor(fk_pairs=(("lot_id", "lot_id"),))
    report = inspect_sql_readiness(FakeDatabase(cursor), settings())
    assert report.missing_constraints == ()
    assert not report.composite_lot_fk_valid
    assert not report.ready


def test_formato_no_incluye_password_ni_errores_odbc():
    report = SqlReadinessReport(
        missing_tables=("Users",), missing_procedures=(), missing_constraints=(),
        procedures_without_execute=("usp_ListarProductos",), composite_lot_fk_valid=True,
    )
    text = "\n".join(format_report(report))
    assert "Users" in text
    assert "usp_ListarProductos" in text
    assert "PWD=" not in text
    assert "INCOMPLETA" in text


def test_cli_sin_connect_jamas_conecta(monkeypatch, capsys):
    import scripts.check_sql_readiness as cli
    monkeypatch.setattr(cli, "Settings", lambda: settings("master"))
    monkeypatch.setattr(cli.pyodbc, "drivers", lambda: ["ODBC Driver 18 for SQL Server"])
    monkeypatch.setattr(cli, "Database", lambda *a: pytest.fail("No debe abrir SQL Server"))
    assert main([]) == 0
    assert "NO se abrió conexión" in capsys.readouterr().out


def test_cli_connect_rechaza_master_sin_instanciar_database(monkeypatch, capsys):
    import scripts.check_sql_readiness as cli
    monkeypatch.setattr(cli, "Settings", lambda: settings("master"))
    monkeypatch.setattr(cli.pyodbc, "drivers", lambda: ["ODBC Driver 18 for SQL Server"])
    monkeypatch.setattr(cli, "Database", lambda *a: pytest.fail("No debe abrir SQL Server"))
    assert main(["--connect"]) == 2
    assert "no master" in capsys.readouterr().out


def test_cli_con_reporte_incompleto_devuelve_estado_uno(monkeypatch, capsys):
    import scripts.check_sql_readiness as cli
    monkeypatch.setattr(cli, "Settings", lambda: settings())
    monkeypatch.setattr(cli.pyodbc, "drivers", lambda: ["ODBC Driver 18 for SQL Server"])
    monkeypatch.setattr(cli, "Database", lambda _: object())
    report = SqlReadinessReport(("Users",), (), (), (), True)
    monkeypatch.setattr(cli, "inspect_sql_readiness", lambda *_: report)
    assert main(["--connect"]) == 1
    assert "INCOMPLETA" in capsys.readouterr().out
