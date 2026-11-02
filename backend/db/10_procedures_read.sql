/*
    Hospital San Gabriel — etapa 7: consultas del inventario.

    REQUISITOS: 00_create_database.sql y 01_create_tables.sql ya ejecutados.
    No se ejecutó este script durante su elaboración.
    Para instalarlo, abrirlo en SSMS (o sqlcmd). GO es un separador de lotes
    de SSMS/sqlcmd; no enviar este archivo completo por pyodbc.

    Las cinco operaciones del backend SOLO leen datos. Las mutaciones y su
    control transaccional se implementan en procedimientos de escritura separados.

    Permisos recomendados: conceder EXECUTE a una cuenta SQL de aplicación con
    privilegios mínimos. No se crean logins ni se conceden permisos aquí.
*/
USE [HospitalSanGabriel];
GO

SET ANSI_NULLS ON;
GO
SET QUOTED_IDENTIFIER ON;
GO

/* Incluye productos inactivos: el historial debe poder interpretarse. */
CREATE OR ALTER PROCEDURE dbo.usp_ListarProductos
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        CONVERT(VARCHAR(36), p.product_id) AS id,
        p.code,
        p.name,
        p.description,
        CONVERT(VARCHAR(36), p.category_id) AS category_id,
        p.unit,
        p.unit_price,
        p.min_stock,
        p.tracks_expiration,
        p.expiration_date,
        p.active
    FROM dbo.Products AS p
    ORDER BY p.code, p.product_id;
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_ListarCategorias
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        CONVERT(VARCHAR(36), c.category_id) AS id,
        c.name,
        c.description,
        c.active
    FROM dbo.Categories AS c
    ORDER BY c.name, c.category_id;
END;
GO

/* Incluye lotes sin existencias: pueden figurar en movimientos anteriores. */
CREATE OR ALTER PROCEDURE dbo.usp_ListarLotes
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        CONVERT(VARCHAR(36), l.lot_id) AS id,
        CONVERT(VARCHAR(36), l.product_id) AS product_id,
        l.number,
        l.expiration_date,
        l.stock
    FROM dbo.Lots AS l
    ORDER BY l.product_id,
             CASE WHEN l.expiration_date IS NULL THEN 1 ELSE 0 END,
             l.expiration_date, l.number, l.lot_id;
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_ListarAreas
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        CONVERT(VARCHAR(36), a.area_id) AS id,
        a.name
    FROM dbo.HospitalAreas AS a
    ORDER BY a.name, a.area_id;
END;
GO

/*
    Orden de registro ASC exigido por API-CONTRACT.md.
    movement_seq solo determina un orden interno de inserción; no es la hora
    exacta de COMMIT global entre productos distintos.
    La fecha/numero de lote se obtienen mediante JOIN al catálogo de lotes.
*/
CREATE OR ALTER PROCEDURE dbo.usp_ListarMovimientos
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        CONVERT(VARCHAR(36), m.movement_id) AS id,
        m.type,
        CONVERT(VARCHAR(36), m.product_id) AS product_id,
        m.quantity,
        m.movement_date AS date,
        m.reason,
        m.stock_before,
        m.stock_after,
        CONVERT(VARCHAR(36), m.lot_id) AS lot_id,
        l.number AS lot_number,
        l.expiration_date,
        CONVERT(VARCHAR(36), m.area_id) AS area_id
    FROM dbo.Movements AS m
    INNER JOIN dbo.Lots AS l
        ON l.lot_id = m.lot_id
       AND l.product_id = m.product_id
    ORDER BY m.movement_seq ASC;
END;
GO
