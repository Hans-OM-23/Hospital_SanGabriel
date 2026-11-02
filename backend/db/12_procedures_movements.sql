/*
    Hospital San Gabriel — etapa 10: registro transaccional de movimientos.

    Instalar desde SSMS cuando se prepare una nueva instancia SQL Server. No se ejecuta desde Python.
    Requiere 00_create_database.sql y 01_create_tables.sql; instalar con SSMS/sqlcmd.
    Se invoca desde el repositorio exclusivamente mediante parámetros pyodbc.

    El saldo del producto es SUM(Lots.stock); Movements almacena su fotografía
    histórica. Todas las mutaciones de stock bloquean primero Products con
    UPDLOCK/HOLDLOCK y después Lots, durante una sola transacción.

    Errores de dominio (THROW) traducidos por el repositorio:
      51021 producto inexistente/inactivo; 51022 lote inválido;
      51023 número de lote existente con otro vencimiento;
      51024 lote vencido para una salida; 51025 stock insuficiente;
      51026 área inexistente; 51027 vencimiento requerido;
      51028 lote vencido a la fecha de entrada; 51029 fecha futura;
      51030 desbordamiento de INT; 51031 campos incompatible con el tipo;
      51032 motivo inválido; 51033 cantidad inválida;
      51034 número de lote requerido.

    LIMITACIÓN CONOCIDA: el contrato Angular no incluye una clave de
    idempotencia. Un reintento de POST después de perder la respuesta podría
    registrar un segundo movimiento. Se resolverá de forma coordinada con el
    frontend antes de afirmar garantías de entrega exactamente una vez.
*/
USE [HospitalSanGabriel];
GO
SET ANSI_NULLS ON;
GO
SET QUOTED_IDENTIFIER ON;
GO

CREATE OR ALTER PROCEDURE dbo.usp_RegistrarMovimiento
    @type VARCHAR(5),
    @product_id UNIQUEIDENTIFIER,
    @quantity INT,
    @movement_date DATE,
    @reason NVARCHAR(200),
    @lot_id UNIQUEIDENTIFIER = NULL,
    @lot_number NVARCHAR(50) = NULL,
    @expiration_date DATE = NULL,
    @area_id UNIQUEIDENTIFIER = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    -- Validaciones sencillas; todas las validaciones con tablas ocurren
    -- después de bloquear la ficha del producto.
    IF @type IS NULL OR @type COLLATE Latin1_General_BIN2 NOT IN ('entry', 'exit')
        THROW 51031, N'Selecciona un tipo de movimiento válido.', 1;
    IF @quantity IS NULL OR @quantity <= 0
        THROW 51033, N'La cantidad debe ser un entero mayor que cero.', 1;
    -- Fecha del hospital en Perú (UTC-05), no la zona configurada en SQL Server.
    DECLARE @today_peru DATE = CONVERT(DATE, SWITCHOFFSET(SYSDATETIMEOFFSET(), '-05:00'));
    IF @movement_date IS NULL OR @movement_date > @today_peru
        THROW 51029, N'Selecciona una fecha válida que no sea futura.', 1;

    SET @reason = LTRIM(RTRIM(@reason));
    IF @reason IS NULL OR LEN(@reason) = 0
        THROW 51032, N'Indica el motivo del movimiento.', 1;

    IF @type = 'entry'
    BEGIN
        IF @lot_id IS NOT NULL OR @area_id IS NOT NULL
            THROW 51031, N'Una entrada no debe incluir lote por ID ni área.', 1;
        SET @lot_number = UPPER(LTRIM(RTRIM(@lot_number)));
        IF @lot_number IS NULL OR LEN(@lot_number) = 0
            THROW 51034, N'Indica el número de lote.', 1;
        IF @reason COLLATE Latin1_General_BIN2 NOT IN (N'Compra', N'Donación', N'Devolución')
            THROW 51032, N'Selecciona compra, donación o devolución.', 1;
    END
    ELSE
    BEGIN
        IF @lot_id IS NULL OR @area_id IS NULL
            THROW 51031, N'Selecciona un lote y un área hospitalaria.', 1;
    END;

    BEGIN TRY
        BEGIN TRANSACTION;

        DECLARE @active BIT = NULL;
        DECLARE @tracks_expiration BIT = NULL;
        SELECT @active = active, @tracks_expiration = tracks_expiration
        FROM dbo.Products WITH (UPDLOCK, HOLDLOCK)
        WHERE product_id = @product_id;

        IF @active IS NULL OR @active = 0
            THROW 51021, N'Selecciona un producto activo.', 1;

        -- El bloqueo de Products permanece hasta el COMMIT y serializa todas
        -- las entradas/salidas del mismo producto, incluidos lotes nuevos.
        DECLARE @stock_before BIGINT = 0;
        SELECT @stock_before = COALESCE(SUM(CONVERT(BIGINT, stock)), 0)
        FROM dbo.Lots WHERE product_id = @product_id;

        IF @stock_before > 2147483647
            THROW 51030, N'El inventario supera el límite de cantidad.', 1;
        IF @type = 'entry'
        BEGIN
            IF @tracks_expiration = 1 AND @expiration_date IS NULL
                THROW 51027, N'Selecciona un vencimiento válido para el lote.', 1;
            IF @tracks_expiration = 0
                SET @expiration_date = NULL;
            IF @expiration_date IS NOT NULL AND @expiration_date < @movement_date
                THROW 51028, N'El lote no puede estar vencido a la fecha de ingreso.', 1;
            IF @stock_before > 2147483647 - CONVERT(BIGINT, @quantity)
                THROW 51030, N'La cantidad supera el máximo permitido.', 1;

            DECLARE @existing_expiration DATE = NULL;
            SELECT @lot_id = lot_id, @existing_expiration = expiration_date
            FROM dbo.Lots WITH (UPDLOCK, HOLDLOCK)
            WHERE product_id = @product_id AND number = @lot_number;

            IF @lot_id IS NOT NULL
            BEGIN
                IF (@existing_expiration IS NULL AND @expiration_date IS NOT NULL)
                   OR (@existing_expiration IS NOT NULL AND @expiration_date IS NULL)
                   OR (@existing_expiration <> @expiration_date)
                    THROW 51023, N'Este lote ya tiene otro vencimiento registrado.', 1;
            END
            ELSE
            BEGIN
                SET @lot_id = NEWID();
                INSERT INTO dbo.Lots
                    (lot_id, product_id, number, expiration_date, stock)
                VALUES (@lot_id, @product_id, @lot_number, @expiration_date, 0);
            END;

            UPDATE dbo.Lots
            SET stock = stock + @quantity
            WHERE lot_id = @lot_id AND product_id = @product_id
              AND stock <= 2147483647 - @quantity;
            IF @@ROWCOUNT <> 1
                THROW 51030, N'La cantidad supera el máximo permitido.', 1;
        END
        ELSE
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM dbo.HospitalAreas WHERE area_id = @area_id)
                THROW 51026, N'Selecciona un área hospitalaria válida.', 1;

            DECLARE @lot_stock INT = NULL;
            SELECT @lot_stock = stock,
                   @expiration_date = expiration_date,
                   @lot_number = number
            FROM dbo.Lots WITH (UPDLOCK, HOLDLOCK)
            WHERE lot_id = @lot_id AND product_id = @product_id;
            IF @lot_stock IS NULL
                THROW 51022, N'Selecciona manualmente un lote del producto.', 1;
            IF @expiration_date IS NOT NULL
               AND (@expiration_date < @today_peru
                    OR @expiration_date < @movement_date)
                THROW 51024, N'El lote está vencido y no puede salir para uso hospitalario.', 1;
            IF @lot_stock < @quantity
                THROW 51025, N'El lote no tiene existencias suficientes.', 1;

            -- Defensa adicional ante escritura simultánea ajena al SP.
            UPDATE dbo.Lots
            SET stock = stock - @quantity
            WHERE lot_id = @lot_id AND product_id = @product_id AND stock >= @quantity;
            IF @@ROWCOUNT <> 1
                THROW 51025, N'El lote no tiene existencias suficientes.', 1;
        END;

        DECLARE @stock_after BIGINT = @stock_before
            + CASE WHEN @type = 'entry' THEN CONVERT(BIGINT, @quantity)
                   ELSE -CONVERT(BIGINT, @quantity) END;
        DECLARE @movement_id UNIQUEIDENTIFIER = NEWID();

        INSERT INTO dbo.Movements
            (movement_id, type, product_id, lot_id, quantity, movement_date,
             reason, stock_before, stock_after, area_id)
        VALUES
            (@movement_id, @type, @product_id, @lot_id, @quantity, @movement_date,
             @reason, CONVERT(INT, @stock_before), CONVERT(INT, @stock_after), @area_id);

        COMMIT TRANSACTION;

        SELECT CONVERT(VARCHAR(36), m.movement_id) AS id,
               m.type, CONVERT(VARCHAR(36), m.product_id) AS product_id,
               m.quantity, m.movement_date AS date, m.reason,
               m.stock_before, m.stock_after,
               CONVERT(VARCHAR(36), m.lot_id) AS lot_id,
               l.number AS lot_number, l.expiration_date,
               CONVERT(VARCHAR(36), m.area_id) AS area_id
        FROM dbo.Movements AS m
        INNER JOIN dbo.Lots AS l
            ON l.lot_id = m.lot_id AND l.product_id = m.product_id
        WHERE m.movement_id = @movement_id;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        -- No se reenvían mensajes de SQL Server directamente a Angular.
        THROW;
    END CATCH;
END;
GO
