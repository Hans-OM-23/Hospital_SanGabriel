/*
  HOSPITAL SAN GABRIEL | INSTALACIÓN COMPLETA EN SQL SERVER
  Ejecute TODO ESTE ARCHIVO desde SSMS usando F5, una sola vez.
  Requisitos: SQL Server 2016+ y permiso para crear/alterar objetos.

  Incluye:
    - Base HospitalSanGabriel (solo si no existe)
    - 6 tablas, índices, restricciones, 4 categorías y 4 áreas
    - 3 productos, lotes y movimientos de ejemplo (solo si no existen)
    - 12 procedimientos almacenados
    - UNA cuenta de demostración si no existe (NO para uso real)
    - Comprobaciones de instalación al final

  ATENCIÓN:
  - Solo para desarrollo y exposición en una instancia de PRUEBAS.
  - No borra ni reinicia una base existente, no reemplaza contraseñas.
  - No instala ni configura FastAPI ni credenciales de conexión SQL.
  - Si SSMS informa algún error, no considere terminada la instalación.
  - Los separadores GO son obligatorios: abrir en SSMS, NO enviar por pyodbc.
*/

SET NOCOUNT ON;
GO


-- ======================================================================
-- 1 / 10 - Base de datos [00_create_database.sql]
-- ======================================================================
PRINT N'Instalando: 1 / 10 - Base de datos';
GO


/*
    Sistema de Gestión de Inventario - Hospital San Gabriel
    Etapa 4: creación reproducible de la base de datos.

    Archivo: 00_create_database.sql
    Propósito: crear la base HospitalSanGabriel si todavía no existe.

    Requisitos:
      - Ejecutar con una cuenta SQL que pueda crear bases de datos
        (por ejemplo, miembro de dbcreator o con CREATE ANY DATABASE).
      - Autenticación SQL Server; no se usa autenticación de Windows
        para la aplicación.
      - No contiene credenciales ni cadenas de conexión.

    Notas:
      - CREATE DATABASE se ejecuta en el contexto de master, pero este
        script NO crea ninguna tabla en master.
      - Si la base ya existe, el script no la modifica ni la elimina.
      - La colación CI (insensible a mayúsculas) permite que las claves
        naturales como el nombre de categoría sean únicas sin distinguir
        mayúsculas. Las columnas que deben ser exactas (código de producto
        y número de lote) se validan con COLLATE Latin1_General_BIN2 en
        01_create_tables.sql.
*/

USE [master];
GO

SET NOCOUNT ON;

IF DB_ID(N'HospitalSanGabriel') IS NULL
BEGIN
    PRINT N'Creando la base de datos HospitalSanGabriel...';

    -- CREATE DATABASE debe ejecutarse en un lote independiente; EXEC evita
    -- el error de compilación dentro de un bloque IF.
    EXEC(N'CREATE DATABASE [HospitalSanGabriel] COLLATE Modern_Spanish_100_CI_AS;');
END
ELSE
BEGIN
    PRINT N'La base HospitalSanGabriel ya existe. No se realizan cambios.';
END
GO


-- ======================================================================
-- 2 / 10 - Tablas y restricciones [01_create_tables.sql]
-- ======================================================================
PRINT N'Instalando: 2 / 10 - Tablas y restricciones';
GO


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


-- ======================================================================
-- 3 / 10 - Índices [02_create_indexes.sql]
-- ======================================================================
PRINT N'Instalando: 3 / 10 - Índices';
GO


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


-- ======================================================================
-- 4 / 10 - Categorías y áreas [03_seed_reference_data.sql]
-- ======================================================================
PRINT N'Instalando: 4 / 10 - Categorías y áreas';
GO


/*
    Sistema de Gestión de Inventario - Hospital San Gabriel
    Etapa 4: datos de catálogo (áreas y categorías).

    Archivo: 03_seed_reference_data.sql
    Requisito: ejecutar después de 01 y 02.

    Este script contiene SOLO catálogos estables y reproducibles:
      - 4 áreas hospitalarias.
      - 4 categorías de productos.
    No contiene usuarios, contraseñas, hashes ni movimientos. Los datos de
    demostración de inventario están separados en 04_seed_demo_inventory.sql.

    Los identificadores son fijos para que el seed sea reproducible y para
    que 04 pueda referenciarlos. Si ya existe una fila con el mismo id o el
    mismo nombre, no se inserta de nuevo.
*/

USE [HospitalSanGabriel];
GO

SET NOCOUNT ON;
SET XACT_ABORT ON;
GO

BEGIN TRY
    BEGIN TRANSACTION;

    /* ------------------------- Áreas hospitalarias ------------------------- */
    IF NOT EXISTS (
        SELECT 1 FROM dbo.HospitalAreas
        WHERE area_id = '11111111-1111-1111-1111-111111111101'
           OR name = N'Emergencia'
    )
    BEGIN
        INSERT INTO dbo.HospitalAreas (area_id, name)
        VALUES ('11111111-1111-1111-1111-111111111101', N'Emergencia');
    END;

    IF NOT EXISTS (
        SELECT 1 FROM dbo.HospitalAreas
        WHERE area_id = '11111111-1111-1111-1111-111111111102'
           OR name = N'Hospitalización'
    )
    BEGIN
        INSERT INTO dbo.HospitalAreas (area_id, name)
        VALUES ('11111111-1111-1111-1111-111111111102', N'Hospitalización');
    END;

    IF NOT EXISTS (
        SELECT 1 FROM dbo.HospitalAreas
        WHERE area_id = '11111111-1111-1111-1111-111111111103'
           OR name = N'Consultorios externos'
    )
    BEGIN
        INSERT INTO dbo.HospitalAreas (area_id, name)
        VALUES ('11111111-1111-1111-1111-111111111103', N'Consultorios externos');
    END;

    IF NOT EXISTS (
        SELECT 1 FROM dbo.HospitalAreas
        WHERE area_id = '11111111-1111-1111-1111-111111111104'
           OR name = N'Laboratorio'
    )
    BEGIN
        INSERT INTO dbo.HospitalAreas (area_id, name)
        VALUES ('11111111-1111-1111-1111-111111111104', N'Laboratorio');
    END;

    /* ----------------------------- Categorías ----------------------------- */
    IF NOT EXISTS (
        SELECT 1 FROM dbo.Categories
        WHERE category_id = '22222222-2222-2222-2222-222222222201'
           OR name = N'Medicamentos'
    )
    BEGIN
        INSERT INTO dbo.Categories (category_id, name, description)
        VALUES (
            '22222222-2222-2222-2222-222222222201',
            N'Medicamentos',
            N'Productos para tratamiento y atención clínica.'
        );
    END;

    IF NOT EXISTS (
        SELECT 1 FROM dbo.Categories
        WHERE category_id = '22222222-2222-2222-2222-222222222202'
           OR name = N'Material médico'
    )
    BEGIN
        INSERT INTO dbo.Categories (category_id, name, description)
        VALUES (
            '22222222-2222-2222-2222-222222222202',
            N'Material médico',
            N'Insumos para procedimientos y protección.'
        );
    END;

    IF NOT EXISTS (
        SELECT 1 FROM dbo.Categories
        WHERE category_id = '22222222-2222-2222-2222-222222222203'
           OR name = N'Material de laboratorio'
    )
    BEGIN
        INSERT INTO dbo.Categories (category_id, name, description)
        VALUES (
            '22222222-2222-2222-2222-222222222203',
            N'Material de laboratorio',
            N'Insumos para análisis y toma de muestras.'
        );
    END;

    IF NOT EXISTS (
        SELECT 1 FROM dbo.Categories
        WHERE category_id = '22222222-2222-2222-2222-222222222204'
           OR name = N'Limpieza hospitalaria'
    )
    BEGIN
        INSERT INTO dbo.Categories (category_id, name, description)
        VALUES (
            '22222222-2222-2222-2222-222222222204',
            N'Limpieza hospitalaria',
            N'Productos para higiene y desinfección.'
        );
    END;

    COMMIT TRANSACTION;
    PRINT N'Catálogos de referencia insertados o ya presentes.';
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    PRINT N'03_seed_reference_data.sql falló; se revirtieron los cambios.';
    THROW;
END CATCH;
GO


-- ======================================================================
-- 5 / 10 - Datos de demostración [04_seed_demo_inventory.sql]
-- ======================================================================
PRINT N'Instalando: 5 / 10 - Datos de demostración';
GO


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


-- ======================================================================
-- 6 / 10 - Procedimientos de consulta [10_procedures_read.sql]
-- ======================================================================
PRINT N'Instalando: 6 / 10 - Procedimientos de consulta';
GO


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


-- ======================================================================
-- 7 / 10 - Procedimientos de catálogo [11_procedures_catalog_write.sql]
-- ======================================================================
PRINT N'Instalando: 7 / 10 - Procedimientos de catálogo';
GO


/*
    Hospital San Gabriel — etapa 9: escrituras de categorías y productos.

    INSTRUCCIONES DE INSTALACIÓN: requiere 00_create_database.sql y 01_create_tables.sql.
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
    producto. Los procedimientos de movimientos bloquean la
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


-- ======================================================================
-- 8 / 10 - Procedimiento transaccional [12_procedures_movements.sql]
-- ======================================================================
PRINT N'Instalando: 8 / 10 - Procedimiento transaccional';
GO


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


-- ======================================================================
-- 9 / 10 - Procedimientos de usuarios [13_procedures_users.sql]
-- ======================================================================
PRINT N'Instalando: 9 / 10 - Procedimientos de usuarios';
GO


/*
    Hospital San Gabriel — etapa 11: lectura de usuarios para autenticación.

    Requiere 01_create_tables.sql. No crea cuentas, no guarda contraseñas, no
    concede permisos y no se ejecuta automáticamente desde Python.
    Las cuentas deben ser aprovisionadas posteriormente por un administrador,
    guardando exclusivamente hashes Argon2id en dbo.Users.password_hash.

    La cuenta SQL que utilice la aplicación debe tener EXECUTE sobre estos
    procedimientos y no necesita permisos SELECT directos sobre dbo.Users.
*/
USE [HospitalSanGabriel];
GO

SET ANSI_NULLS ON;
GO
SET QUOTED_IDENTIFIER ON;
GO

-- El correo se compara bajo la colación CI de la base; la cuenta inactiva se
-- devuelve igualmente para que AuthService pueda rechazarla sin revelar datos.
CREATE OR ALTER PROCEDURE dbo.usp_ObtenerUsuarioPorCorreo
    @email NVARCHAR(254)
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        CONVERT(VARCHAR(36), u.user_id) AS id,
        u.name,
        u.email,
        u.role,
        u.active,
        u.password_hash
    FROM dbo.Users AS u
    WHERE u.email = LOWER(LTRIM(RTRIM(@email)));
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_ObtenerUsuarioPorId
    @user_id UNIQUEIDENTIFIER
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        CONVERT(VARCHAR(36), u.user_id) AS id,
        u.name,
        u.email,
        u.role,
        u.active,
        u.password_hash
    FROM dbo.Users AS u
    WHERE u.user_id = @user_id;
END;
GO


-- ======================================================================
-- CUENTA DE DEMOSTRACIÓN LOCAL (NO USAR EN PRODUCCIÓN)
-- ======================================================================
USE [HospitalSanGabriel];
GO
SET NOCOUNT ON;
IF NOT EXISTS (SELECT 1 FROM dbo.Users WHERE email = N'admin@hospital.com')
BEGIN
    INSERT INTO dbo.Users (user_id, name, email, password_hash, role, active)
    VALUES (NEWID(), N'Administrador', N'admin@hospital.com',
            N'$argon2id$v=19$m=65536,t=3,p=4$4uYYboxQyX7JoqMf3xFymQ$bTgnL4BMixs+WFuizWddoFen9tpHhp0H6jkmIuUYrOw', N'Responsable de almacén', 1);
    PRINT N'Cuenta de demostración insertada: admin@hospital.com';
END
ELSE
    PRINT N'La cuenta de demostración ya existe. No se modifica.';
GO

-- ======================================================================
-- VERIFICACIÓN DE INSTALACIÓN
-- ======================================================================
PRINT N'Iniciando verificación del esquema...';
GO

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


-- ======================================================================
-- RESUMEN FINAL - comprueba objetos imprescindibles antes de declarar éxito
-- ======================================================================
USE [HospitalSanGabriel];
GO
IF (SELECT COUNT(*) FROM sys.tables WHERE schema_id = SCHEMA_ID('dbo')) <> 6
    THROW 51071, N'Instalación incompleta: deben existir 6 tablas.', 1;
IF (SELECT COUNT(*) FROM sys.procedures WHERE schema_id = SCHEMA_ID('dbo')
    AND name IN (N'usp_ListarProductos', N'usp_ListarCategorias',
                 N'usp_ListarLotes', N'usp_ListarAreas', N'usp_ListarMovimientos',
                 N'usp_CrearCategoria', N'usp_CrearProducto', N'usp_ActualizarProducto',
                 N'usp_CambiarEstadoProducto', N'usp_RegistrarMovimiento',
                 N'usp_ObtenerUsuarioPorCorreo', N'usp_ObtenerUsuarioPorId')) <> 12
    THROW 51072, N'Instalación incompleta: faltan procedimientos.', 1;
IF NOT EXISTS (SELECT 1 FROM dbo.Users WHERE email=N'admin@hospital.com' AND active=1)
    THROW 51073, N'La cuenta de demostración no está activa.', 1;

SELECT
    DB_NAME() AS BaseDatos,
    (SELECT COUNT(*) FROM sys.tables WHERE schema_id=SCHEMA_ID('dbo')) AS Tablas,
    (SELECT COUNT(*) FROM sys.procedures WHERE schema_id=SCHEMA_ID('dbo')) AS Procedimientos,
    (SELECT COUNT(*) FROM dbo.Categories) AS Categorias,
    (SELECT COUNT(*) FROM dbo.HospitalAreas) AS Areas,
    (SELECT COUNT(*) FROM dbo.Products) AS Productos,
    (SELECT COUNT(*) FROM dbo.Lots) AS Lotes,
    (SELECT COUNT(*) FROM dbo.Movements) AS Movimientos,
    (SELECT COUNT(*) FROM dbo.Users) AS Usuarios;
PRINT N'INSTALACIÓN COMPLETADA - compruebe las consultas de consistencia anteriores.';
GO
