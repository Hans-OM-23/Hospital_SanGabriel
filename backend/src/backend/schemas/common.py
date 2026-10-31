"""Tipos y configuración compartidos por los modelos Pydantic de la API.

Los modelos exponen alias camelCase porque son los nombres que ya consume
Angular (ver ``frontend/docs/API-CONTRACT.md``). Internamente se usan nombres
snake_case, coherentes con las columnas de SQL Server.

Estas validaciones son de forma y de coherencia básica de la entrada. No
consultan la base de datos, no aplican reglas de inventario (saldo real,
vencimiento del lote, unicidad, producto activo) y no sustituyen a los
servicios ni a los procedimientos almacenados.

Los mensajes de error están en español porque el frontend los muestra
directamente en los formularios.
"""

from __future__ import annotations

import math
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict
from pydantic.alias_generators import to_camel
from pydantic_core import PydanticCustomError

# Límite de un INT de SQL Server, usado en cantidades y stock mínimo.
MAX_SQL_INT = 2_147_483_647

# Máximo de DECIMAL(12, 2) usado por Products.unit_price.
MAX_UNIT_PRICE = 9_999_999_999.99


def _fallar(codigo: str, mensaje: str) -> None:
    """Lanza un error de validación con un mensaje en español."""
    raise PydanticCustomError(codigo, mensaje)


def texto_obligatorio(
    *,
    max_length: int,
    mensaje_requerido: str,
    mensaje_longitud: str,
    mayusculas: bool = False,
) -> Any:
    """Texto obligatorio: recorta espacios exteriores y rechaza cadenas vacías.

    El recorte y las mayúsculas replican la normalización que ya hace Angular
    antes de enviar ``code`` y el número de lote. La normalización definitiva
    se repetirá en los procedimientos almacenados.
    """

    def _validar(value: Any) -> str:
        if not isinstance(value, str):
            _fallar("string_type", mensaje_requerido)

        limpio = value.strip()
        if not limpio:
            _fallar("required", mensaje_requerido)
        if len(limpio) > max_length:
            _fallar("max_length", mensaje_longitud)
        return limpio.upper() if mayusculas else limpio

    return Annotated[str, BeforeValidator(_validar)]


def texto(*, max_length: int, mensaje_longitud: str) -> Any:
    """Texto obligatorio en la clave, pero que puede quedar vacío.

    Se usa en ``CategoryInput.description``: el formulario siempre envía el
    campo, aunque el usuario lo deje en blanco.
    """

    def _validar(value: Any) -> str:
        if not isinstance(value, str):
            _fallar("string_type", "El valor debe ser texto.")

        limpio = value.strip()
        if len(limpio) > max_length:
            _fallar("max_length", mensaje_longitud)
        return limpio

    return Annotated[str, BeforeValidator(_validar)]


def entero(*, minimo: int, maximo: int, mensaje: str) -> Any:
    """Entero estricto dentro de un rango.

    Rechaza booleanos, decimales y cadenas numéricas: el contrato envía
    cantidades y mínimos como números enteros de JSON.
    """

    def _validar(value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            _fallar("int_type", mensaje)
        if value < minimo or value > maximo:
            _fallar("int_range", mensaje)
        return value

    return Annotated[int, BeforeValidator(_validar)]


def precio(*, mensaje: str, mensaje_decimales: str, mensaje_maximo: str) -> Any:
    """Precio numérico finito, mayor que cero y con dos decimales como máximo.

    El límite reproduce ``DECIMAL(12, 2)`` del esquema y evita que un valor
    válido en el formulario se redondee de forma silenciosa al persistirlo.
    """

    def _validar(value: Any) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            _fallar("float_type", mensaje)

        numero = float(value)
        if not math.isfinite(numero) or numero <= 0:
            _fallar("float_range", mensaje)
        if numero > MAX_UNIT_PRICE:
            _fallar("float_range", mensaje_maximo)
        if Decimal(str(numero)).as_tuple().exponent < -2:
            _fallar("decimal_places", mensaje_decimales)
        return numero

    return Annotated[float, BeforeValidator(_validar)]


_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _validar_fecha_iso(value: Any) -> date:
    """Acepta solo fechas de calendario en formato ``YYYY-MM-DD``.

    Rechaza marcas de tiempo y fechas inexistentes (por ejemplo 2026-02-30),
    igual que ``isDate`` en el frontend.
    """
    if isinstance(value, datetime):
        _fallar("date_format", "La fecha debe tener el formato YYYY-MM-DD.")
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        _fallar("date_format", "La fecha debe tener el formato YYYY-MM-DD.")

    texto_fecha = value.strip()
    if not _DATE_PATTERN.fullmatch(texto_fecha):
        _fallar("date_format", "La fecha debe tener el formato YYYY-MM-DD.")

    try:
        fecha = date.fromisoformat(texto_fecha)
    except ValueError:
        _fallar("date_invalid", "La fecha no existe en el calendario.")

    if fecha.isoformat() != texto_fecha:
        _fallar("date_format", "La fecha debe tener el formato YYYY-MM-DD.")
    return fecha


ISODate = Annotated[date, BeforeValidator(_validar_fecha_iso)]


def _validar_booleano(value: Any) -> bool:
    if not isinstance(value, bool):
        _fallar("bool_type", "El valor debe ser verdadero o falso.")
    return value


StrictBool = Annotated[bool, BeforeValidator(_validar_booleano)]


def _validar_identificador(value: Any) -> str:
    """Normaliza un identificador opaco a texto.

    El contrato exige ``string``. pyodbc devuelve las columnas
    ``UNIQUEIDENTIFIER`` como ``uuid.UUID``, por lo que los modelos de
    respuesta aceptan ambos y siempre serializan texto.
    """
    if isinstance(value, UUID):
        return str(value)
    if not isinstance(value, str):
        _fallar("identifier_type", "El identificador debe ser texto.")

    limpio = value.strip()
    if not limpio:
        _fallar("identifier", "El identificador no puede estar vacío.")
    if len(limpio) > 100:
        _fallar("identifier_length", "El identificador no es válido.")
    return limpio


Identifier = Annotated[str, BeforeValidator(_validar_identificador)]


class ApiModel(BaseModel):
    """Base común: alias camelCase y construcción desde atributos.

    ``serialize_by_alias`` hace que ``model_dump()`` ya use camelCase, de modo
    que el contrato no dependa de la configuración de serialización de FastAPI.
    ``from_attributes`` permitirá construir respuestas desde filas de pyodbc
    en la etapa de repositorios.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_alias=True,
        validate_by_name=True,
        serialize_by_alias=True,
        from_attributes=True,
        extra="ignore",
    )


class ApiInput(ApiModel):
    """Modelo de entrada: rechaza propiedades que no estén en el contrato."""

    model_config = ConfigDict(extra="forbid")


class ApiResponse(ApiModel):
    """Modelo de salida: tolera columnas adicionales de la base de datos."""

    model_config = ConfigDict(extra="ignore")


__all__ = [
    "ApiInput",
    "ApiModel",
    "ApiResponse",
    "Identifier",
    "ISODate",
    "MAX_SQL_INT",
    "MAX_UNIT_PRICE",
    "StrictBool",
    "entero",
    "precio",
    "texto",
    "texto_obligatorio",
]
