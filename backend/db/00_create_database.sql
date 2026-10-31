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

    CREATE DATABASE [HospitalSanGabriel]
        COLLATE Modern_Spanish_100_CI_AS;
END
ELSE
BEGIN
    PRINT N'La base HospitalSanGabriel ya existe. No se realizan cambios.';
END
GO
