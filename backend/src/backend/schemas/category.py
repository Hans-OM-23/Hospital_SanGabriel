"""Schemas de categorías.

La unicidad del nombre (sin distinguir mayúsculas ni espacios exteriores) la
garantiza la base de datos y la comprobará el servicio; aquí solo se valida la
forma de la entrada.
"""

from __future__ import annotations

from backend.schemas.common import ApiInput, ApiResponse, Identifier, texto, texto_obligatorio

CategoryName = texto_obligatorio(
    max_length=100,
    mensaje_requerido="Ingresa el nombre de la categoría.",
    mensaje_longitud="El nombre admite hasta 100 caracteres.",
)

CategoryDescription = texto(
    max_length=500,
    mensaje_longitud="La descripción admite hasta 500 caracteres.",
)


class CategoryCreate(ApiInput):
    """Cuerpo de ``POST /categories`` (``CategoryInput`` en Angular)."""

    name: CategoryName
    description: CategoryDescription


class CategoryResponse(ApiResponse):
    """Categoría tal como la espera la interfaz Angular."""

    id: Identifier
    name: str
    description: str
    active: bool


__all__ = [
    "CategoryCreate",
    "CategoryDescription",
    "CategoryName",
    "CategoryResponse",
]
