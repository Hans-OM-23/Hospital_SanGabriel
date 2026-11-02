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


class InventoryOperationError(Exception):
    """Regla de negocio rechazada, sin errores internos de SQL Server."""

    status_code: int = 409

    def __init__(self, message: str, *, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


class InventoryConflictError(InventoryOperationError):
    """Unicidad o cambio incompatible con el historial (409)."""

    status_code = 409


class InventoryNotFoundError(InventoryOperationError):
    """Recurso inexistente (404)."""

    status_code = 404


class InventoryInvalidReferenceError(InventoryOperationError):
    """Referencia o selección inválida (422)."""

    status_code = 422
