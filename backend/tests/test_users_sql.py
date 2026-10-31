"""Inspección estática de los procedimientos de usuarios (sin ejecutar SQL)."""

from __future__ import annotations

from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "db"
SQL = (DB / "13_procedures_users.sql").read_text(encoding="utf-8")


def test_procedimientos_estan_definidos_y_requieren_base_hospital():
    assert "USE [HospitalSanGabriel]" in SQL
    assert "CREATE OR ALTER PROCEDURE dbo.usp_ObtenerUsuarioPorCorreo" in SQL
    assert "CREATE OR ALTER PROCEDURE dbo.usp_ObtenerUsuarioPorId" in SQL
    assert "SET NOCOUNT ON" in SQL


def test_procedimientos_devuelven_campos_para_auth_service():
    for name in ("u.user_id", "u.name", "u.email", "u.role", "u.active", "u.password_hash"):
        assert SQL.count(name) >= 2
    assert "FROM dbo.Users" in SQL
    assert "@email NVARCHAR(254)" in SQL
    assert "@user_id UNIQUEIDENTIFIER" in SQL


def test_no_existen_credenciales_ni_cambios_directos_de_usuarios():
    import re
    cleaned = re.sub(r"/\*.*?\*/|--[^\n]*", "", SQL, flags=re.DOTALL)
    for forbidden in ("CREATE LOGIN", "ALTER LOGIN", "GRANT ", "DROP ",
                      "INSERT INTO", "UPDATE dbo.Users", "DELETE FROM", "PASSWORD =", "EXEC xp_"):
        assert forbidden not in cleaned.upper()
