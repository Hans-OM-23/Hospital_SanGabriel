"""Diagnóstico voluntario de SQL Server: por defecto NO se conecta.

Uso desde backend/:
  uv run python scripts/check_sql_readiness.py
  uv run python scripts/check_sql_readiness.py --connect

El segundo comando SOLO LEE metadatos; requiere que HospitalSanGabriel esté
instalada y que el .env corresponda a esa base. Nunca imprime credenciales.
"""

from __future__ import annotations

import argparse
import sys

import pyodbc

from backend.core.config import Settings
from backend.core.database import Database
from backend.core.exceptions import DatabaseError
from backend.core.sql_readiness import TARGET_DB, format_report, inspect_sql_readiness


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verificación segura de preparación SQL Server")
    parser.add_argument(
        "--connect", action="store_true", help="Consultar metadatos SQL solo en HospitalSanGabriel"
    )
    args = parser.parse_args(argv)

    try:
        settings = Settings()
    except ValueError:
        print("Configuración no válida; revisa backend/.env sin compartir secretos.")
        return 2

    try:
        installed = set(pyodbc.drivers())
    except pyodbc.Error:
        installed = set()
    driver_found = settings.db_driver in installed
    print("Controlador ODBC configurado: " + ("instalado" if driver_found else "no encontrado"))
    print("Configuración SQL: " + ("completa" if settings.database_configured else "incompleta"))
    print("Clave JWT: " + ("configurada" if settings.jwt_configured else "pendiente"))
    print("Base objetivo: " + TARGET_DB)

    if not args.connect:
        print("Modo local: NO se abrió conexión ni se ejecutó SQL.")
        return 0

    if settings.db_name.casefold() != TARGET_DB.casefold():
        print("No se consultó SQL Server: DB_NAME debe ser HospitalSanGabriel, no master.")
        return 2
    if not settings.database_configured or not driver_found:
        print("No se consultó SQL Server: falta configuración o controlador ODBC.")
        return 2

    try:
        report = inspect_sql_readiness(Database(settings), settings)
    except (DatabaseError, pyodbc.Error):
        print("No se pudo completar el diagnóstico SQL. Revisa conexión y permisos.")
        return 2
    for line in format_report(report):
        print(line)
    return 0 if report.ready else 1


if __name__ == "__main__":
    sys.exit(main())
