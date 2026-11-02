"""Diagnóstico optativo y SOLO LECTURA de la instalación SQL Server.

No se usa en el flujo HTTP ni en repositorios de negocio. Examina únicamente
metadatos de SQL Server y permisos EXECUTE, nunca datos de pacientes, usuarios
ni inventario. Solo se llama de manera explícita tras instalar la BD.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.core.config import Settings
from backend.core.database import Database

TARGET_DB = "HospitalSanGabriel"

EXPECTED_TABLES = frozenset({
    "Users", "Categories", "Products", "HospitalAreas", "Lots", "Movements",
})
EXPECTED_PROCEDURES = frozenset({
    "usp_ListarProductos", "usp_ListarCategorias", "usp_ListarLotes",
    "usp_ListarAreas", "usp_ListarMovimientos", "usp_CrearCategoria",
    "usp_CrearProducto", "usp_ActualizarProducto", "usp_CambiarEstadoProducto",
    "usp_RegistrarMovimiento", "usp_ObtenerUsuarioPorCorreo", "usp_ObtenerUsuarioPorId",
})
EXPECTED_CONSTRAINTS = frozenset({
    "PK_Users", "PK_Categories", "PK_Products", "PK_HospitalAreas",
    "PK_Lots", "PK_Movements", "FK_Movements_Lots_Product",
    "CK_Lots_Stock", "CK_Movements_Balance", "UQ_Movements_Seq",
})

_TABLES_SQL = "SELECT name FROM sys.tables WHERE schema_id = SCHEMA_ID(N'dbo')"
_PROCEDURES_SQL = "SELECT name FROM sys.procedures WHERE schema_id = SCHEMA_ID(N'dbo')"
_CONSTRAINTS_SQL = (
    "SELECT name FROM sys.objects WHERE schema_id = SCHEMA_ID(N'dbo') "
    "AND type IN ('PK', 'UQ', 'F', 'C')"
)
_COMPOSITE_FK_SQL = """
SELECT origin.name, destination.name
FROM sys.foreign_key_columns AS fkc
JOIN sys.foreign_keys AS fk ON fk.object_id = fkc.constraint_object_id
JOIN sys.columns AS origin
  ON origin.object_id = fkc.parent_object_id AND origin.column_id = fkc.parent_column_id
JOIN sys.columns AS destination
  ON destination.object_id = fkc.referenced_object_id
 AND destination.column_id = fkc.referenced_column_id
WHERE fk.name = N'FK_Movements_Lots_Product'
ORDER BY fkc.constraint_column_id
"""
_PERMISSION_SQL = "SELECT HAS_PERMS_BY_NAME(?, 'OBJECT', 'EXECUTE')"
_EXPECTED_FK_COLUMNS = (("lot_id", "lot_id"), ("product_id", "product_id"))


@dataclass(frozen=True, slots=True)
class SqlReadinessReport:
    """Objetos ausentes o no visibles, y permisos insuficientes."""

    missing_tables: tuple[str, ...]
    missing_procedures: tuple[str, ...]
    missing_constraints: tuple[str, ...]
    procedures_without_execute: tuple[str, ...]
    composite_lot_fk_valid: bool

    @property
    def ready(self) -> bool:
        return not (
            self.missing_tables
            or self.missing_procedures
            or self.missing_constraints
            or self.procedures_without_execute
        ) and self.composite_lot_fk_valid


def _names(cursor: object, statement: str) -> set[str]:
    cursor.execute(statement)
    return {str(row[0]) for row in cursor.fetchall()}


def inspect_sql_readiness(database: Database, settings: Settings) -> SqlReadinessReport:
    """Consulta metadatos; no modifica nada ni se conecta a ``master``.

    El comando es diagnóstico administrativo explícito, NO acceso del backend
    a datos de negocio: las operaciones de inventario siguen usando SP.
    """
    if settings.db_name.casefold() != TARGET_DB.casefold():
        raise ValueError(
            "Diagnóstico cancelado: DB_NAME debe ser HospitalSanGabriel. "
            "No se consultó ninguna base de datos."
        )

    with database.connection() as cursor:
        tables = _names(cursor, _TABLES_SQL)
        procedures = _names(cursor, _PROCEDURES_SQL)
        constraints = _names(cursor, _CONSTRAINTS_SQL)

        cursor.execute(_COMPOSITE_FK_SQL)
        fk_pairs = tuple((str(row[0]), str(row[1])) for row in cursor.fetchall())

        no_execute: list[str] = []
        for proc in sorted(EXPECTED_PROCEDURES & procedures):
            cursor.execute(_PERMISSION_SQL, f"dbo.{proc}")
            result = cursor.fetchone()
            if result is None or result[0] != 1:
                no_execute.append(proc)

    return SqlReadinessReport(
        missing_tables=tuple(sorted(EXPECTED_TABLES - tables)),
        missing_procedures=tuple(sorted(EXPECTED_PROCEDURES - procedures)),
        missing_constraints=tuple(sorted(EXPECTED_CONSTRAINTS - constraints)),
        procedures_without_execute=tuple(no_execute),
        composite_lot_fk_valid=fk_pairs == _EXPECTED_FK_COLUMNS,
    )


def format_report(report: SqlReadinessReport) -> list[str]:
    """Devuelve solo nombres públicos de objetos, nunca credenciales."""
    details = [
        ("Tablas ausentes/no visibles", report.missing_tables),
        ("Procedimientos ausentes/no visibles", report.missing_procedures),
        ("Restricciones ausentes/no visibles", report.missing_constraints),
        ("Procedimientos sin EXECUTE confirmado", report.procedures_without_execute),
    ]
    output = ["Instalación SQL: " + ("LISTA" if report.ready else "INCOMPLETA")]
    for title, names in details:
        output.append(f"{title}: " + (", ".join(names) if names else "ninguno"))
    output.append("FK lote-producto compuesta: " + ("correcta" if report.composite_lot_fk_valid else "revisar"))
    return output


__all__ = [
    "SqlReadinessReport", "TARGET_DB", "EXPECTED_TABLES", "EXPECTED_PROCEDURES",
    "EXPECTED_CONSTRAINTS", "inspect_sql_readiness", "format_report",
]
