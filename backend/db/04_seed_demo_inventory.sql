/*
    Sistema de Gestión de Inventario - Hospital San Gabriel
    Etapa 4: datos de DEMOSTRACIÓN (opcional).

    Archivo: 04_seed_demo_inventory.sql
    Requisito: ejecutar 03_seed_reference_data.sql antes.

    ADVERTENCIA:
      - Este script es solo para entornos de demostración, no para producción.
      - Inserta 3 productos, 3 lotes y 4 movimientos que reproducen el
        snapshot de la demo del frontend.
      - Si ya existe cualquiera de los códigos MED-001, MAT-001 o LIM-001,
        el script no inserta nada (evita duplicados y seeds parciales).
      - Las fechas son relativas al día de ejecución para que la demo muestre
        un lote vencido y otro próximo a vencer.

    Consistencia matemática que el script garantiza:
      Producto MED-001: entrada 50, salida 10  -> lote 40, último saldo 40.
      Producto MAT-001: entrada 4              -> lote 4,  último saldo 4.
      Producto LIM-001: entrada 2              -> lote 2,  último saldo 2.
      Cadena por producto: 0 -> 50 -> 40; 0 -> 4; 0 -> 2.
      SUM(Lots.stock) coincide con el último stock_after de cada producto.
*/

USE [HospitalSanGabriel];
GO

SET NOCOUNT ON;
SET XACT_ABORT ON;
GO

-- Misma fecha operativa de Perú que valida FastAPI y el procedimiento.
DECLARE @hoy DATE = CONVERT(DATE, SWITCHOFFSET(SYSDATETIMEOFFSET(), '-05:00'));

DECLARE @cat_medicamentos UNIQUEIDENTIFIER =
    (SELECT category_id FROM dbo.Categories WHERE name = N'Medicamentos');
DECLARE @cat_material UNIQUEIDENTIFIER =
    (SELECT category_id FROM dbo.Categories WHERE name = N'Material médico');
DECLARE @cat_limpieza UNIQUEIDENTIFIER =
    (SELECT category_id FROM dbo.Categories WHERE name = N'Limpieza hospitalaria');
DECLARE @area_emergencia UNIQUEIDENTIFIER =
    (SELECT area_id FROM dbo.HospitalAreas WHERE name = N'Emergencia');

/* Identificadores fijos para que la demo sea reproducible. */
DECLARE @p1 UNIQUEIDENTIFIER = '33333333-3333-3333-3333-333333333301';
DECLARE @p2 UNIQUEIDENTIFIER = '33333333-3333-3333-3333-333333333302';
DECLARE @p3 UNIQUEIDENTIFIER = '33333333-3333-3333-3333-333333333303';

DECLARE @l1 UNIQUEIDENTIFIER = '44444444-4444-4444-4444-444444444401';
DECLARE @l2 UNIQUEIDENTIFIER = '44444444-4444-4444-4444-444444444402';
DECLARE @l3 UNIQUEIDENTIFIER = '44444444-4444-4444-4444-444444444403';

IF EXISTS (
    SELECT 1
    FROM dbo.Products
    WHERE code IN (N'MED-001', N'MAT-001', N'LIM-001')
)
BEGIN
    PRINT N'04_seed_demo_inventory.sql omitido: ya existen productos de demostración.';
END
ELSE
BEGIN
    BEGIN TRY
        BEGIN TRANSACTION;

        IF @cat_medicamentos IS NULL
           OR @cat_material IS NULL
           OR @cat_limpieza IS NULL
           OR @area_emergencia IS NULL
        BEGIN
            ;THROW 50000,
                N'Ejecute 03_seed_reference_data.sql antes de 04_seed_demo_inventory.sql.',
                1;
        END;

        /* ----------------------------- Productos ----------------------------- */
        INSERT INTO dbo.Products
            (product_id, code, name, description, category_id, unit,
             unit_price, min_stock, tracks_expiration, expiration_date, active)
        VALUES
            (@p1, N'MED-001', N'Paracetamol 500 mg',
             N'Tabletas para uso hospitalario.',
             @cat_medicamentos, N'Tableta', 0.50, 20, 1,
             DATEADD(DAY, 180, @hoy), 1);

        INSERT INTO dbo.Products
            (product_id, code, name, description, category_id, unit,
             unit_price, min_stock, tracks_expiration, expiration_date, active)
        VALUES
            (@p2, N'MAT-001', N'Guantes de nitrilo',
             N'Guantes de examen, talla M. Caja de 100 unidades.',
             @cat_material, N'Caja', 28.00, 5, 1,
             DATEADD(DAY, 900, @hoy), 1);

        INSERT INTO dbo.Products
            (product_id, code, name, description, category_id, unit,
             unit_price, min_stock, tracks_expiration, expiration_date, active)
        VALUES
            (@p3, N'LIM-001', N'Alcohol al 70 %',
             N'Frasco de un litro para desinfección.',
             @cat_limpieza, N'Frasco', 12.50, 3, 1,
             DATEADD(DAY, -5, @hoy), 1);

        /* ------------------------------- Lotes ------------------------------- */
        -- Los saldos ya reflejan el resultado de los movimientos siguientes.
        INSERT INTO dbo.Lots (lot_id, product_id, number, expiration_date, stock)
        VALUES (@l1, @p1, N'PAR-026', DATEADD(DAY, 180, @hoy), 40);

        INSERT INTO dbo.Lots (lot_id, product_id, number, expiration_date, stock)
        VALUES (@l2, @p2, N'GUA-026', DATEADD(DAY, 900, @hoy), 4);

        INSERT INTO dbo.Lots (lot_id, product_id, number, expiration_date, stock)
        VALUES (@l3, @p3, N'ALC-025', DATEADD(DAY, -5, @hoy), 2);

        /* ---------------------------- Movimientos ---------------------------- */
        -- Saldos del producto (todos sus lotes), antes y después.
        INSERT INTO dbo.Movements
            (movement_id, type, product_id, lot_id, quantity, movement_date,
             reason, stock_before, stock_after, area_id)
        VALUES
            ('55555555-5555-5555-5555-555555555501', 'entry', @p1, @l1, 50,
             DATEADD(DAY, -10, @hoy), N'Compra', 0, 50, NULL);

        INSERT INTO dbo.Movements
            (movement_id, type, product_id, lot_id, quantity, movement_date,
             reason, stock_before, stock_after, area_id)
        VALUES
            ('55555555-5555-5555-5555-555555555502', 'exit', @p1, @l1, 10,
             DATEADD(DAY, -2, @hoy), N'Reposición de insumos', 50, 40,
             @area_emergencia);

        INSERT INTO dbo.Movements
            (movement_id, type, product_id, lot_id, quantity, movement_date,
             reason, stock_before, stock_after, area_id)
        VALUES
            ('55555555-5555-5555-5555-555555555503', 'entry', @p2, @l2, 4,
             DATEADD(DAY, -10, @hoy), N'Donación', 0, 4, NULL);

        INSERT INTO dbo.Movements
            (movement_id, type, product_id, lot_id, quantity, movement_date,
             reason, stock_before, stock_after, area_id)
        VALUES
            ('55555555-5555-5555-5555-555555555504', 'entry', @p3, @l3, 2,
             DATEADD(DAY, -20, @hoy), N'Compra', 0, 2, NULL);

        COMMIT TRANSACTION;
        PRINT N'Datos de demostración insertados correctamente.';
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;

        PRINT N'04_seed_demo_inventory.sql falló; se revirtieron los cambios.';
        THROW;
    END CATCH;
END;
GO
