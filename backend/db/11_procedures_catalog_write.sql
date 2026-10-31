/*
    Hospital San Gabriel — etapa 9: escrituras de categorías y productos.

    INSTALACIÓN PENDIENTE: requiere 00_create_database.sql y 01_create_tables.sql.
    Se ejecuta con SSMS/sqlcmd, no con pyodbc (GO divide los lotes).
    El backend invoca únicamente estos procedimientos parametrizados.
    No crea cuentas, permisos ni datos de demostración.

    Errores de dominio (THROW con número fijo; nunca incluye valores privados):
      51011 nombre de categoría duplicado
      51012 código de producto duplicado
      51013 categoría inexistente o inactiva
      51014 producto inexistente
      51015 unidad inmutable si existen movimientos
      51016 seguimiento de vencimiento inmutable si existen movimientos

    Estas operaciones se serializan con UPDLOCK/HOLDLOCK sobre la ficha del
    producto. Los futuros procedimientos de movimientos DEBEN bloquear la
    misma fila de Products antes de modificar Lots o Movements.
*/
USE [HospitalSanGabriel];
GO
SET ANSI_NULLS ON;
GO
SET QUOTED_IDENTIFIER ON;
GO

CREATE OR ALTER PROCEDURE dbo.usp_CrearCategoria
    @name NVARCHAR(100),
    @description NVARCHAR(500)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    SET @name = LTRIM(RTRIM(@name));
    SET @description = LTRIM(RTRIM(@description));

    BEGIN TRY
        BEGIN TRANSACTION;
        IF EXISTS (
            SELECT 1 FROM dbo.Categories WITH (UPDLOCK, HOLDLOCK)
            WHERE name = @name
        )
            THROW 51011, N'Esta categoría ya existe.', 1;

        DECLARE @id UNIQUEIDENTIFIER = NEWID();
        INSERT INTO dbo.Categories (category_id, name, description)
        VALUES (@id, @name, @description);
        COMMIT TRANSACTION;

        SELECT CONVERT(VARCHAR(36), category_id) AS id,
               name, description, active
        FROM dbo.Categories WHERE category_id = @id;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        IF ERROR_NUMBER() IN (2601, 2627)
            THROW 51011, N'Esta categoría ya existe.', 1;
        THROW;
    END CATCH;
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_CrearProducto
    @code NVARCHAR(40),
    @name NVARCHAR(160),
    @description NVARCHAR(1000),
    @category_id UNIQUEIDENTIFIER,
    @unit NVARCHAR(30),
    @unit_price DECIMAL(12,2),
    @min_stock INT,
    @tracks_expiration BIT,
    @expiration_date DATE = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    SET @code = UPPER(LTRIM(RTRIM(@code)));
    SET @name = LTRIM(RTRIM(@name));
    SET @description = LTRIM(RTRIM(@description));
    SET @unit = LTRIM(RTRIM(@unit));

    BEGIN TRY
        BEGIN TRANSACTION;
        IF NOT EXISTS (
            SELECT 1 FROM dbo.Categories WITH (UPDLOCK, HOLDLOCK)
            WHERE category_id = @category_id AND active = 1
        )
            THROW 51013, N'Selecciona una categoría disponible.', 1;
        IF EXISTS (
            SELECT 1 FROM dbo.Products WITH (UPDLOCK, HOLDLOCK)
            WHERE code = @code
        )
            THROW 51012, N'Este código ya está registrado.', 1;

        DECLARE @id UNIQUEIDENTIFIER = NEWID();
        INSERT INTO dbo.Products
            (product_id, code, name, description, category_id, unit,
             unit_price, min_stock, tracks_expiration, expiration_date)
        VALUES
            (@id, @code, @name, @description, @category_id, @unit,
             @unit_price, @min_stock, @tracks_expiration, @expiration_date);
        COMMIT TRANSACTION;

        SELECT CONVERT(VARCHAR(36), product_id) AS id,
               code, name, description,
               CONVERT(VARCHAR(36), category_id) AS category_id,
               unit, unit_price, min_stock, tracks_expiration,
               expiration_date, active
        FROM dbo.Products WHERE product_id = @id;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        IF ERROR_NUMBER() IN (2601, 2627)
            THROW 51012, N'Este código ya está registrado.', 1;
        THROW;
    END CATCH;
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_ActualizarProducto
    @product_id UNIQUEIDENTIFIER,
    @code NVARCHAR(40),
    @name NVARCHAR(160),
    @description NVARCHAR(1000),
    @category_id UNIQUEIDENTIFIER,
    @unit NVARCHAR(30),
    @unit_price DECIMAL(12,2),
    @min_stock INT,
    @tracks_expiration BIT,
    @expiration_date DATE = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    SET @code = UPPER(LTRIM(RTRIM(@code)));
    SET @name = LTRIM(RTRIM(@name));
    SET @description = LTRIM(RTRIM(@description));
    SET @unit = LTRIM(RTRIM(@unit));

    BEGIN TRY
        BEGIN TRANSACTION;
        -- Orden fijo de bloqueos en altas y ediciones: Categories -> Products.
        IF NOT EXISTS (
            SELECT 1 FROM dbo.Categories WITH (UPDLOCK, HOLDLOCK)
            WHERE category_id = @category_id AND active = 1
        )
            THROW 51013, N'Selecciona una categoría disponible.', 1;

        DECLARE @old_unit NVARCHAR(30);
        DECLARE @old_tracks_expiration BIT;
        SELECT @old_unit = unit,
               @old_tracks_expiration = tracks_expiration
        FROM dbo.Products WITH (UPDLOCK, HOLDLOCK)
        WHERE product_id = @product_id;
        IF @@ROWCOUNT = 0
            THROW 51014, N'El producto ya no está disponible.', 1;
        IF EXISTS (
            SELECT 1 FROM dbo.Products WITH (UPDLOCK, HOLDLOCK)
            WHERE code = @code AND product_id <> @product_id
        )
            THROW 51012, N'Este código ya está registrado.', 1;
        IF EXISTS (
            SELECT 1 FROM dbo.Movements WHERE product_id = @product_id
        )
        BEGIN
            IF @old_unit <> @unit
                THROW 51015, N'La unidad de medida no puede cambiar cuando existen movimientos.', 1;
            IF @old_tracks_expiration <> @tracks_expiration
                THROW 51016, N'El control de vencimiento no puede cambiar cuando existen movimientos.', 1;
        END;

        UPDATE dbo.Products
        SET code = @code,
            name = @name,
            description = @description,
            category_id = @category_id,
            unit = @unit,
            unit_price = @unit_price,
            min_stock = @min_stock,
            tracks_expiration = @tracks_expiration,
            expiration_date = @expiration_date,
            updated_at = SYSDATETIME()
        WHERE product_id = @product_id;
        -- El estado active se conserva: solo se cambia con PATCH /status.
        COMMIT TRANSACTION;

        SELECT CONVERT(VARCHAR(36), product_id) AS id,
               code, name, description,
               CONVERT(VARCHAR(36), category_id) AS category_id,
               unit, unit_price, min_stock, tracks_expiration,
               expiration_date, active
        FROM dbo.Products WHERE product_id = @product_id;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        IF ERROR_NUMBER() IN (2601, 2627)
            THROW 51012, N'Este código ya está registrado.', 1;
        THROW;
    END CATCH;
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_CambiarEstadoProducto
    @product_id UNIQUEIDENTIFIER,
    @active BIT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRY
        BEGIN TRANSACTION;
        -- Se toma el mismo bloqueo que deberán respetar los movimientos.
        IF NOT EXISTS (
            SELECT 1 FROM dbo.Products WITH (UPDLOCK, HOLDLOCK)
            WHERE product_id = @product_id
        )
            THROW 51014, N'No se encontró el producto.', 1;
        UPDATE dbo.Products
        SET active = @active, updated_at = SYSDATETIME()
        WHERE product_id = @product_id;
        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;
END;
GO
