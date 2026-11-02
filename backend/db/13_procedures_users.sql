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
