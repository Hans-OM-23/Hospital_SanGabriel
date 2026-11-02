/*
    Sistema de Gestión de Inventario - Hospital San Gabriel
    Etapa 4: tablas, claves y restricciones del esquema inicial.

    Archivo: 01_create_tables.sql
    Requisito: ejecutar después de 00_create_database.sql.

    Contenido:
      dbo.Users          Usuarios de la aplicación (contraseña solo como hash).
      dbo.Categories     Categorías de productos.
      dbo.Products       Fichas de productos.
      dbo.HospitalAreas  Áreas hospitalarias de destino.
      dbo.Lots           Lotes y su saldo individual.
      dbo.Movements      Entradas y salidas con saldos históricos.

    Decisiones relevantes:
      - No existe columna de stock total en Products: el saldo del producto
        es SUM(Lots.stock), una sola fuente de verdad.
      - Los saldos de Movements son fotografías históricas del total del
        producto y se calculan dentro de la transacción que actualiza el lote.
      - Las claves naturales que deben ser exactas (code, number) se validan
        con COLLATE Latin1_General_BIN2. La base es CI, por lo que comparar
        con la colación por defecto no garantizaría mayúsculas. La
        normalización (TRIM + UPPER) se completará en los procedimientos
        almacenados antes de insertar o actualizar.
      - La FK compuesta (lot_id, product_id) impide asociar un movimiento a
        un lote de otro producto.
      - Este script no crea procedimientos almacenados; la lógica de
        inventario y su concurrencia están implementados en los procedimientos de movimientos.
*/

USE [HospitalSanGabriel];
GO

SET NOCOUNT ON;
SET XACT_ABORT ON;
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

/* ------------------------------------------------------------------ */
/* dbo.Users                                                          */
/* ------------------------------------------------------------------ */
IF OBJECT_ID(N'dbo.Users', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Users
    (
        user_id        UNIQUEIDENTIFIER NOT NULL
            CONSTRAINT DF_Users_UserId DEFAULT NEWID(),
        name           NVARCHAR(160)    NOT NULL,
        email          NVARCHAR(254)    NOT NULL,
        password_hash  NVARCHAR(255)    NOT NULL,
        role           NVARCHAR(50)     NOT NULL
            CONSTRAINT DF_Users_Role DEFAULT N'Responsable de almacén',
        active         BIT              NOT NULL
            CONSTRAINT DF_Users_Active DEFAULT 1,
        created_at     DATETIME2(0)     NOT NULL
            CONSTRAINT DF_Users_CreatedAt DEFAULT SYSDATETIME(),
        updated_at     DATETIME2(0)     NULL,
        CONSTRAINT PK_Users PRIMARY KEY (user_id),
        CONSTRAINT UQ_Users_Email UNIQUE (email),
        CONSTRAINT CK_Users_Name
            CHECK (LEN(LTRIM(RTRIM(name))) > 0),
        CONSTRAINT CK_Users_Email
            CHECK (email LIKE N'%_@_%._%'),
        CONSTRAINT CK_Users_Role
            CHECK (role = N'Responsable de almacén'),
        -- Solo se almacena el hash; nunca la contraseña en texto plano.
        CONSTRAINT CK_Users_PasswordHash
            CHECK (LEN(password_hash) >= 20)
    );
END
GO

/* ------------------------------------------------------------------ */
/* dbo.Categories                                                     */
/* ------------------------------------------------------------------ */
IF OBJECT_ID(N'dbo.Categories', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Categories
    (
        category_id  UNIQUEIDENTIFIER NOT NULL
            CONSTRAINT DF_Categories_CategoryId DEFAULT NEWID(),
        name         NVARCHAR(100)    NOT NULL,
        description  NVARCHAR(500)    NOT NULL
            CONSTRAINT DF_Categories_Description DEFAULT N'',
        active       BIT              NOT NULL
            CONSTRAINT DF_Categories_Active DEFAULT 1,
        created_at   DATETIME2(0)     NOT NULL
            CONSTRAINT DF_Categories_CreatedAt DEFAULT SYSDATETIME(),
        CONSTRAINT PK_Categories PRIMARY KEY (category_id),
        -- La colación CI de la base hace que 'Medicamentos' y
        -- 'medicamentos' colisionen, igual que la validación del frontend.
        CONSTRAINT UQ_Categories_Name UNIQUE (name),
        CONSTRAINT CK_Categories_Name
            CHECK (LEN(LTRIM(RTRIM(name))) > 0)
    );
END
GO

/* ------------------------------------------------------------------ */
/* dbo.Products                                                       */
/* ------------------------------------------------------------------ */
IF OBJECT_ID(N'dbo.Products', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Products
    (
        product_id        UNIQUEIDENTIFIER NOT NULL
            CONSTRAINT DF_Products_ProductId DEFAULT NEWID(),
        code              NVARCHAR(40)     NOT NULL,
        name              NVARCHAR(160)    NOT NULL,
        description       NVARCHAR(1000)   NOT NULL,
        category_id       UNIQUEIDENTIFIER NOT NULL,
        unit              NVARCHAR(30)     NOT NULL,
        unit_price        DECIMAL(12,2)    NOT NULL,
        min_stock         INT              NOT NULL,
        tracks_expiration BIT              NOT NULL,
        expiration_date   DATE             NULL,
        active            BIT              NOT NULL
            CONSTRAINT DF_Products_Active DEFAULT 1,
        created_at        DATETIME2(0)     NOT NULL
            CONSTRAINT DF_Products_CreatedAt DEFAULT SYSDATETIME(),
        updated_at        DATETIME2(0)     NULL,
        CONSTRAINT PK_Products PRIMARY KEY (product_id),
        CONSTRAINT FK_Products_Categories
            FOREIGN KEY (category_id) REFERENCES dbo.Categories (category_id),
        -- Unicidad insensible a mayúsculas: impide códigos duplicados.
        CONSTRAINT UQ_Products_Code UNIQUE (code),
        CONSTRAINT CK_Products_Code CHECK (
            LEN(code) > 0
            AND code = LTRIM(RTRIM(code)) COLLATE Latin1_General_BIN2
            AND code = UPPER(code) COLLATE Latin1_General_BIN2
        ),
        CONSTRAINT CK_Products_Name
            CHECK (LEN(LTRIM(RTRIM(name))) > 0),
        CONSTRAINT CK_Products_Unit
            CHECK (LEN(LTRIM(RTRIM(unit))) > 0),
        CONSTRAINT CK_Products_UnitPrice
            CHECK (unit_price > 0),
        CONSTRAINT CK_Products_MinStock
            CHECK (min_stock >= 0),
        CONSTRAINT CK_Products_Expiration
            CHECK (
                (tracks_expiration = 1 AND expiration_date IS NOT NULL)
                OR (tracks_expiration = 0 AND expiration_date IS NULL)
            )
    );
END
GO

/* ------------------------------------------------------------------ */
/* dbo.HospitalAreas                                                  */
/* ------------------------------------------------------------------ */
IF OBJECT_ID(N'dbo.HospitalAreas', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.HospitalAreas
    (
        area_id    UNIQUEIDENTIFIER NOT NULL
            CONSTRAINT DF_HospitalAreas_AreaId DEFAULT NEWID(),
        name       NVARCHAR(100)    NOT NULL,
        created_at DATETIME2(0)     NOT NULL
            CONSTRAINT DF_HospitalAreas_CreatedAt DEFAULT SYSDATETIME(),
        CONSTRAINT PK_HospitalAreas PRIMARY KEY (area_id),
        CONSTRAINT UQ_HospitalAreas_Name UNIQUE (name),
        CONSTRAINT CK_HospitalAreas_Name
            CHECK (LEN(LTRIM(RTRIM(name))) > 0)
    );
END
GO

/* ------------------------------------------------------------------ */
/* dbo.Lots                                                           */
/* ------------------------------------------------------------------ */
IF OBJECT_ID(N'dbo.Lots', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Lots
    (
        lot_id          UNIQUEIDENTIFIER NOT NULL
            CONSTRAINT DF_Lots_LotId DEFAULT NEWID(),
        product_id      UNIQUEIDENTIFIER NOT NULL,
        number          NVARCHAR(50)     NOT NULL,
        expiration_date DATE             NULL,
        stock           INT              NOT NULL
            CONSTRAINT DF_Lots_Stock DEFAULT 0,
        created_at      DATETIME2(0)     NOT NULL
            CONSTRAINT DF_Lots_CreatedAt DEFAULT SYSDATETIME(),
        CONSTRAINT PK_Lots PRIMARY KEY (lot_id),
        CONSTRAINT FK_Lots_Products
            FOREIGN KEY (product_id) REFERENCES dbo.Products (product_id),
        -- El número de lote identifica un lote dentro de su producto.
        CONSTRAINT UQ_Lots_Product_Number UNIQUE (product_id, number),
        -- Necesaria para la FK compuesta de Movements.
        CONSTRAINT UQ_Lots_Lot_Product UNIQUE (lot_id, product_id),
        -- Última barrera de la base contra saldos negativos.
        CONSTRAINT CK_Lots_Stock CHECK (stock >= 0),
        CONSTRAINT CK_Lots_Number CHECK (
            LEN(number) > 0
            AND number = LTRIM(RTRIM(number)) COLLATE Latin1_General_BIN2
            AND number = UPPER(number) COLLATE Latin1_General_BIN2
        )
    );
END
GO

/* ------------------------------------------------------------------ */
/* dbo.Movements                                                      */
/* ------------------------------------------------------------------ */
IF OBJECT_ID(N'dbo.Movements', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Movements
    (
        movement_id       UNIQUEIDENTIFIER NOT NULL
            CONSTRAINT DF_Movements_MovementId DEFAULT NEWID(),
        -- Orden interno estable y determinista para el historial.
        -- Es monótono, pero puede tener huecos (ROLLBACK consume números)
        -- y no debe interpretarse como el orden global de COMMIT entre
        -- productos distintos. La consistencia de stockBefore/stockAfter
        -- se garantiza por producto en la transacción del procedimiento.
        movement_seq      BIGINT IDENTITY(1,1) NOT NULL,
        type              VARCHAR(5) COLLATE Latin1_General_BIN2 NOT NULL,
        product_id        UNIQUEIDENTIFIER NOT NULL,
        lot_id            UNIQUEIDENTIFIER NOT NULL,
        quantity          INT              NOT NULL,
        movement_date     DATE             NOT NULL,
        reason            NVARCHAR(200)    NOT NULL,
        stock_before      INT              NOT NULL,
        stock_after       INT              NOT NULL,
        area_id           UNIQUEIDENTIFIER NULL,
        created_by_user_id UNIQUEIDENTIFIER NULL,
        created_at        DATETIME2(3)     NOT NULL
            CONSTRAINT DF_Movements_CreatedAt DEFAULT SYSDATETIME(),

        CONSTRAINT PK_Movements PRIMARY KEY NONCLUSTERED (movement_id),
        -- Índice clustered: el historial se lee en orden de registro.
        CONSTRAINT UQ_Movements_Seq UNIQUE CLUSTERED (movement_seq),

        CONSTRAINT FK_Movements_Products
            FOREIGN KEY (product_id) REFERENCES dbo.Products (product_id),
        -- Garantiza que el lote pertenece al producto del movimiento.
        CONSTRAINT FK_Movements_Lots_Product
            FOREIGN KEY (lot_id, product_id)
            REFERENCES dbo.Lots (lot_id, product_id),
        CONSTRAINT FK_Movements_HospitalAreas
            FOREIGN KEY (area_id) REFERENCES dbo.HospitalAreas (area_id),
        CONSTRAINT FK_Movements_Users
            FOREIGN KEY (created_by_user_id) REFERENCES dbo.Users (user_id),

        -- Se almacenan los literales que espera el contrato JSON.
        CONSTRAINT CK_Movements_Type
            CHECK (type IN ('entry', 'exit')),
        CONSTRAINT CK_Movements_Quantity
            CHECK (quantity > 0),
        CONSTRAINT CK_Movements_Reason CHECK (
            (type = 'entry'
                AND reason COLLATE Latin1_General_BIN2
                    IN (N'Compra', N'Donación', N'Devolución'))
            OR (type = 'exit' AND LEN(LTRIM(RTRIM(reason))) > 0)
        ),
        -- Las entradas no llevan área; las salidas sí.
        CONSTRAINT CK_Movements_Area CHECK (
            (type = 'entry' AND area_id IS NULL)
            OR (type = 'exit' AND area_id IS NOT NULL)
        ),
        CONSTRAINT CK_Movements_StockBefore
            CHECK (stock_before >= 0),
        CONSTRAINT CK_Movements_StockAfter
            CHECK (stock_after >= 0),
        -- Relación algebraica entre cantidad y saldos históricos.
        CONSTRAINT CK_Movements_Balance CHECK (
            stock_after = stock_before
                + CASE WHEN type = 'entry' THEN quantity ELSE -quantity END
        )
    );
END
GO
