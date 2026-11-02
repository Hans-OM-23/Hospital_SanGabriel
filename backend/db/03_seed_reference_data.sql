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
