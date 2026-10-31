"""Errores de la capa de datos con mensajes seguros para mostrar."""


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
