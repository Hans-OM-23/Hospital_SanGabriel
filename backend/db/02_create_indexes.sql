/*
    Sistema de Gestión de Inventario - Hospital San Gabriel
    Etapa 4: índices de apoyo.

    Archivo: 02_create_indexes.sql
    Requisito: ejecutar después de 01_create_tables.sql.

    Las restricciones UNIQUE y las claves primarias ya crean sus propios
    índices en 01. Aquí solo se agregan los índices no clusterizados que
    necesitarán las consultas del historial, los lotes por vencimiento y
    los productos por categoría.

    No se crean procedimientos almacenados ni lógica de inventario.
*/

USE [HospitalSanGabriel];
GO

SET NOCOUNT ON;
SET XACT_ABORT ON;
GO

/* Productos por categoría */
IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = N'IX_Products_CategoryId'
      AND object_id = OBJECT_ID(N'dbo.Products')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_Products_CategoryId
        ON dbo.Products (category_id)
        INCLUDE (code, name, active);
END
GO

/* Productos activos para selectores y métricas */
IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = N'IX_Products_Active'
      AND object_id = OBJECT_ID(N'dbo.Products')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_Products_Active
        ON dbo.Products (active)
        INCLUDE (code, name, category_id, min_stock);
END
GO

/* Lotes de un producto ordenados por vencimiento más cercano */
IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = N'IX_Lots_Product_Expiration'
      AND object_id = OBJECT_ID(N'dbo.Lots')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_Lots_Product_Expiration
        ON dbo.Lots (product_id, expiration_date)
        INCLUDE (number, stock);
END
GO

/* Historial por producto en orden interno de registro */
IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = N'IX_Movements_Product_Seq'
      AND object_id = OBJECT_ID(N'dbo.Movements')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_Movements_Product_Seq
        ON dbo.Movements (product_id, movement_seq)
        INCLUDE (type, quantity, movement_date, stock_before, stock_after, lot_id, area_id);
END
GO

/* Historial de un lote: trazabilidad y conciliación por lote */
IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = N'IX_Movements_Lot_Seq'
      AND object_id = OBJECT_ID(N'dbo.Movements')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_Movements_Lot_Seq
        ON dbo.Movements (lot_id, movement_seq);
END
GO

/* Filtros del historial por fecha */
IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = N'IX_Movements_Date'
      AND object_id = OBJECT_ID(N'dbo.Movements')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_Movements_Date
        ON dbo.Movements (movement_date, movement_seq)
        INCLUDE (type, product_id, quantity);
END
GO

/* Filtros del historial por área y auditoría por usuario */
IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = N'IX_Movements_Area'
      AND object_id = OBJECT_ID(N'dbo.Movements')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_Movements_Area
        ON dbo.Movements (area_id, movement_seq);
END
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = N'IX_Movements_User'
      AND object_id = OBJECT_ID(N'dbo.Movements')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_Movements_User
        ON dbo.Movements (created_by_user_id, movement_seq);
END
GO
