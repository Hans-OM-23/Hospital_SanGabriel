"""Errores de dominio con mensajes seguros para el cliente y los logs.

Los mensajes de estas excepciones están pensados para mostrarse al usuario o
registrarse en logs: no deben contener credenciales, cadenas de conexión,
tokens, hashes ni el mensaje bruto del controlador ODBC.
"""


class DatabaseError(RuntimeError):
    """Error base de la capa de datos.

    Los mensajes de estas excepciones están pensados para mostrarse al usuario
    o registrarse en logs: no deben contener credenciales, cadenas de conexión
    ni el mensaje bruto del controlador ODBC.
    """


class DatabaseConfigurationError(DatabaseError):
    """La configuración de conexión está incompleta o es inválida."""


class DatabaseConnectionError(DatabaseError):
    """No fue posible conectar o consultar SQL Server."""


class AuthConfigurationError(RuntimeError):
    """La configuración de seguridad falta, es insegura o no se puede usar.

    Se produce, por ejemplo, al intentar emitir un token sin una clave JWT
    propia. La API debe tratarla como un error del servidor (HTTP 500) y no
    exponer su detalle interno al cliente.
    """


class AccessTokenError(Exception):
    """El token de acceso falta, está alterado, caducó o no cumple el formato."""

    MENSAJE = "El token de acceso no es válido o ha expirado."

    def __init__(self, mensaje: str = MENSAJE) -> None:
        super().__init__(mensaje)


class InvalidCredentialsError(Exception):
    """El correo o la contraseña no son correctos o la cuenta está inactiva.

    Se usa un único error para ambos casos para no revelar si un correo está
    registrado. El mensaje coincide con el que muestra el frontend ante un 401.
    """

    MENSAJE = "El correo o la contraseña no son correctos."

    def __init__(self, mensaje: str = MENSAJE) -> None:
        super().__init__(mensaje)
