"""Errores HTTP públicos y seguros, compatibles con el normalizador de Angular.

La validación de FastAPI incluye ``input`` y ``ctx`` en sus errores estándar.
Esos atributos pueden contener contraseñas, datos sanitarios u otros valores
privados del usuario. La respuesta HTTP solo expone ``loc``, ``msg`` y ``type``.

No modifica ni registra el cuerpo de la solicitud. La estructura ``detail``
continúa siendo compatible con ``frontend/.../api-error.ts``.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# Estos tipos proceden de los validadores definidos por el propio backend.
# Sus mensajes son estáticos y están redactados en español; no incorporan
# valores enviados por el cliente.
_CUSTOM_ERRORS = frozenset({
    "required", "max_length", "int_range", "float_range", "decimal_places",
    "date_format", "date_invalid", "identifier", "identifier_length",
    "date_future", "reason_entry", "lot_entry", "lot_required",
    "lot_number_required", "expiration_before_entry", "area_entry",
    "area_required", "unit", "expiration_required", "email", "password",
    "password_blank", "password_length",
})

# Para errores generados por Pydantic/FastAPI, los mensajes traducidos nunca
# interpolan el dato inválido, incluso si Pydantic cambia su redacción.
_GENERIC_MESSAGES = {
    "missing": "Este campo es obligatorio.",
    "extra_forbidden": "Este campo no está permitido.",
    "json_invalid": "El cuerpo JSON no tiene un formato válido.",
    "string_type": "El valor debe ser texto.",
    "int_type": "El valor debe ser un número entero.",
    "int_parsing": "El valor debe ser un número entero.",
    "float_type": "El valor debe ser un número válido.",
    "float_parsing": "El valor debe ser un número válido.",
    "bool_type": "El valor debe ser verdadero o falso.",
    "date_type": "La fecha no es válida.",
    "date_from_datetime_parsing": "La fecha no es válida.",
    "date_parsing": "La fecha no es válida.",
    "literal_error": "El valor no está permitido.",
    "enum": "El valor no está permitido.",
    "model_attributes_type": "El cuerpo de la solicitud no es válido.",
    "list_type": "El valor debe ser una lista.",
}

_MAX_PUBLIC_ERRORS = 30


def public_validation_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normaliza errores 422 sin exponer input, ctx ni URLs de Pydantic."""
    public: list[dict[str, Any]] = []
    for item in errors[:_MAX_PUBLIC_ERRORS]:
        error_type = str(item.get("type", "invalid"))
        raw_loc = item.get("loc", ())
        # Evitar incluir índices de análisis de JSON o nombres de estructura
        # desconocidos como si fueran campos de un formulario Angular.
        if error_type == "json_invalid":
            loc: list[str | int] = ["body"]
        else:
            loc = [value for value in raw_loc if isinstance(value, (str, int))]
            if not loc:
                loc = ["body"]
        if error_type in _CUSTOM_ERRORS:
            message = str(item["msg"])
        else:
            message = _GENERIC_MESSAGES.get(error_type, "El valor enviado no es válido.")

        public.append({"loc": loc, "msg": message, "type": error_type})
    return public


def register_error_handlers(app: FastAPI) -> None:
    """Registra los formatos HTTP 422/404/405 sin alterar otros errores."""

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        headers: dict[str, str] = {}
        if request.url.path == "/api/auth/login":
            headers.update({"Cache-Control": "no-store", "Pragma": "no-cache"})
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": public_validation_errors(exc.errors())},
            headers=headers,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        message = exc.detail
        if exc.status_code == status.HTTP_404_NOT_FOUND and message == "Not Found":
            message = "La ruta solicitada no existe."
        elif exc.status_code == status.HTTP_405_METHOD_NOT_ALLOWED and message == "Method Not Allowed":
            message = "El método HTTP no está permitido para esta ruta."
        headers = dict(exc.headers or {})
        if request.url.path == "/api/auth/login":
            headers.update({"Cache-Control": "no-store", "Pragma": "no-cache"})
        return JSONResponse(status_code=exc.status_code, content={"detail": message}, headers=headers)


__all__ = ["public_validation_errors", "register_error_handlers"]
