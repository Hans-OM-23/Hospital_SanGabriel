/*
    Sistema de Gestión de Inventario - Hospital San Gabriel
    Etapa 4: verificación del esquema (SOLO LECTURA).

    Archivo: 99_verify_schema.sql

    Este script no crea, modifica ni elimina datos. Devuelve varios
    conjuntos de resultados; en las consultas marcadas "Esperado: 0 filas"
    cualquier fila indica una incoherencia que debe revisarse.

    Requisito: 00, 01 y 02 ejecutados. 03 y 04 son opcionales.
*/

USE [master];
GO

IF DB_ID(N'HospitalSanGabriel') IS NULL
BEGIN
    ;THROW 50000,
        N'La base HospitalSanGabriel no existe. Ejecute 00_create_database.sql.',
        1;
END;
GO

USE [HospitalSanGabriel];
GO

SET NOCOUNT ON;
GO

/* ------------------------------------------------------------------ */
/* 1. Base de datos y colación actual                                 */
/* ------------------------------------------------------------------ */
SELECT
    DB_NAME()      AS base_actual,
    d.collation_name AS colacion
FROM sys.databases AS d
WHERE d.name = N'HospitalSanGabriel';

/* ------------------------------------------------------------------ */
/* 2. Tablas esperadas y cantidad de filas                            */
/* ------------------------------------------------------------------ */
SELECT
    s.name AS esquema,
    t.name AS tabla,
    SUM(p.rows) AS filas
FROM sys.tables AS t
INNER JOIN sys.schemas AS s ON s.schema_id = t.schema_id
INNER JOIN sys.partitions AS p
    ON p.object_id = t.object_id
   AND p.index_id IN (0, 1)
WHERE s.name = N'dbo'
GROUP BY s.name, t.name
ORDER BY t.name;

/* Tablas esperadas que faltan. Esperado: 0 filas. */
SELECT esperada.tabla AS tabla_faltante
FROM (VALUES
        (N'Users'),
        (N'Categories'),
        (N'Products'),
        (N'HospitalAreas'),
        (N'Lots'),
        (N'Movements')
     ) AS esperada(tabla)
WHERE NOT EXISTS (
    SELECT 1
    FROM sys.tables AS t
    INNER JOIN sys.schemas AS s ON s.schema_id = t.schema_id
    WHERE s.name = N'dbo'
      AND t.name = esperada.tabla
);

/* ------------------------------------------------------------------ */
/* 3. Claves foráneas y acciones referenciales                        */
/* ------------------------------------------------------------------ */
SELECT
    fk.name                         AS clave_foranea,
    OBJECT_NAME(fk.parent_object_id) AS tabla_origen,
    OBJECT_NAME(fk.referenced_object_id) AS tabla_destino,
    fk.delete_referential_action_desc AS al_eliminar,
    fk.update_referential_action_desc AS al_actualizar
FROM sys.foreign_keys AS fk
WHERE fk.parent_object_id IN (
    SELECT object_id FROM sys.tables WHERE schema_id = SCHEMA_ID(N'dbo')
)
ORDER BY tabla_origen, fk.name;

/* Columnas de la FK compuesta. Esperado: 2 filas (lot_id y product_id). */
SELECT
    fk.name         AS clave_foranea,
    col_origen.name AS columna_origen,
    col_destino.name AS columna_destino
FROM sys.foreign_keys AS fk
INNER JOIN sys.foreign_key_columns AS fkc
    ON fkc.constraint_object_id = fk.object_id
INNER JOIN sys.columns AS col_origen
    ON col_origen.object_id = fkc.parent_object_id
   AND col_origen.column_id = fkc.parent_column_id
INNER JOIN sys.columns AS col_destino
    ON col_destino.object_id = fkc.referenced_object_id
   AND col_destino.column_id = fkc.referenced_column_id
WHERE fk.name = N'FK_Movements_Lots_Product'
ORDER BY fkc.constraint_column_id;

/* ------------------------------------------------------------------ */
/* 4. Restricciones CHECK                                             */
/* ------------------------------------------------------------------ */
SELECT
    cc.name                       AS restriccion,
    OBJECT_NAME(cc.parent_object_id) AS tabla,
    cc.definition                 AS definicion
FROM sys.check_constraints AS cc
WHERE cc.parent_object_id IN (
    SELECT object_id FROM sys.tables WHERE schema_id = SCHEMA_ID(N'dbo')
)
ORDER BY tabla, cc.name;

/* ------------------------------------------------------------------ */
/* 5. Claves primarias, UNIQUE e índices                              */
/* ------------------------------------------------------------------ */
SELECT
    i.name             AS indice,
    OBJECT_NAME(i.object_id) AS tabla,
    i.type_desc        AS tipo,
    i.is_primary_key   AS es_pk,
    i.is_unique_constraint AS es_unique,
    i.is_unique        AS es_unico
FROM sys.indexes AS i
WHERE i.object_id IN (
    SELECT object_id FROM sys.tables WHERE schema_id = SCHEMA_ID(N'dbo')
)
  AND i.name IS NOT NULL
ORDER BY tabla, i.name;

/* ------------------------------------------------------------------ */
/* 6. Integridad referencial: huérfanos e incoherencias               */
/*    Todas estas consultas deben devolver 0 filas.                   */
/* ------------------------------------------------------------------ */

/* Productos sin categoría válida */
SELECT p.product_id, p.code
FROM dbo.Products AS p
LEFT JOIN dbo.Categories AS c ON c.category_id = p.category_id
WHERE c.category_id IS NULL;

/* Lotes sin producto válido */
SELECT l.lot_id, l.number
FROM dbo.Lots AS l
LEFT JOIN dbo.Products AS p ON p.product_id = l.product_id
WHERE p.product_id IS NULL;

/* Movimientos con lote de otro producto (debe ser imposible por la FK) */
SELECT m.movement_id, m.product_id, m.lot_id
FROM dbo.Movements AS m
INNER JOIN dbo.Lots AS l ON l.lot_id = m.lot_id
WHERE l.product_id <> m.product_id;

/* Entradas con área o salidas sin área */
SELECT m.movement_id, m.type, m.area_id
FROM dbo.Movements AS m
WHERE (m.type = 'entry' AND m.area_id IS NOT NULL)
   OR (m.type = 'exit'  AND m.area_id IS NULL);

/* Motivos inválidos para entradas */
SELECT m.movement_id, m.reason
FROM dbo.Movements AS m
WHERE m.type = 'entry'
  AND m.reason COLLATE Latin1_General_BIN2
      NOT IN (N'Compra', N'Donación', N'Devolución');

/* Saldos negativos */
SELECT l.lot_id, l.stock
FROM dbo.Lots AS l
WHERE l.stock < 0;

SELECT m.movement_id, m.stock_before, m.stock_after
FROM dbo.Movements AS m
WHERE m.stock_before < 0
   OR m.stock_after < 0;

/* Aritmética de saldos incoherente (la restricción ya lo impide) */
SELECT m.movement_id, m.type, m.quantity, m.stock_before, m.stock_after
FROM dbo.Movements AS m
WHERE m.stock_after <> m.stock_before
      + CASE WHEN m.type = 'entry' THEN m.quantity ELSE -m.quantity END;

/* Duplicados lógicos (las restricciones UNIQUE ya los impiden) */
SELECT p.code, COUNT(*) AS repeticiones
FROM dbo.Products AS p
GROUP BY p.code
HAVING COUNT(*) > 1;

SELECT c.name, COUNT(*) AS repeticiones
FROM dbo.Categories AS c
GROUP BY c.name
HAVING COUNT(*) > 1;

SELECT l.product_id, l.number, COUNT(*) AS repeticiones
FROM dbo.Lots AS l
GROUP BY l.product_id, l.number
HAVING COUNT(*) > 1;

/* ------------------------------------------------------------------ */
/* 7. Consistencia de stockBefore / stockAfter por producto           */
/*    La cadena se evalúa con movement_seq, que es el orden interno   */
/*    estable. No representa el orden global de COMMIT entre          */
/*    productos distintos, pero sí es consistente dentro de cada      */
/*    producto porque los procedimientos serializarán por producto.   */
/*    Esperado: 0 filas.                                              */
/* ------------------------------------------------------------------ */
WITH cadena AS (
    SELECT
        m.movement_id,
        m.product_id,
        m.movement_seq,
        m.stock_before,
        m.stock_after,
        LAG(m.stock_after) OVER (
            PARTITION BY m.product_id
            ORDER BY m.movement_seq
        ) AS stock_after_anterior
    FROM dbo.Movements AS m
)
SELECT
    c.product_id,
    c.movement_seq,
    c.stock_before,
    c.stock_after_anterior
FROM cadena AS c
WHERE c.stock_after_anterior IS NOT NULL
  AND c.stock_before <> c.stock_after_anterior;

/* Último stock_after de cada producto contra la suma de sus lotes.
   Esperado: 0 filas. */
WITH ultimo AS (
    SELECT
        m.product_id,
        m.stock_after,
        ROW_NUMBER() OVER (
            PARTITION BY m.product_id
            ORDER BY m.movement_seq DESC
        ) AS posicion
    FROM dbo.Movements AS m
)
SELECT
    p.product_id,
    p.code,
    COALESCE(lotes.total, 0) AS stock_lotes,
    u.stock_after            AS ultimo_stock_after
FROM dbo.Products AS p
LEFT JOIN (
    SELECT l.product_id, SUM(l.stock) AS total
    FROM dbo.Lots AS l
    GROUP BY l.product_id
) AS lotes ON lotes.product_id = p.product_id
LEFT JOIN ultimo AS u
    ON u.product_id = p.product_id
   AND u.posicion = 1
WHERE COALESCE(lotes.total, 0) <> COALESCE(u.stock_after, 0);

/* Movimientos por lote contra el saldo actual del lote.
   Esperado: 0 filas. */
SELECT
    l.lot_id,
    l.number,
    l.stock AS stock_actual,
    COALESCE(SUM(
        CASE
            WHEN m.movement_id IS NULL THEN 0
            WHEN m.type = 'entry' THEN m.quantity
            ELSE -m.quantity
        END
    ), 0) AS stock_segun_movimientos
FROM dbo.Lots AS l
LEFT JOIN dbo.Movements AS m ON m.lot_id = l.lot_id
GROUP BY l.lot_id, l.number, l.stock
HAVING l.stock <> COALESCE(SUM(
    CASE
        WHEN m.movement_id IS NULL THEN 0
        WHEN m.type = 'entry' THEN m.quantity
        ELSE -m.quantity
    END
), 0);

/* ------------------------------------------------------------------ */
/* 8. Resumen del orden interno de movimientos                        */
/*    Informativo: los huecos en movement_seq son normales porque un  */
/*    ROLLBACK consume números de IDENTITY.                           */
/* ------------------------------------------------------------------ */
SELECT
    COUNT(*)                    AS total_movimientos,
    MIN(m.movement_seq)         AS primera_secuencia,
    MAX(m.movement_seq)         AS ultima_secuencia,
    COUNT(DISTINCT m.movement_seq) AS secuencias_distintas
FROM dbo.Movements AS m;
GO
