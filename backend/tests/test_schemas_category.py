"""Pruebas de los schemas de categorías."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.schemas.category import CategoryCreate, CategoryResponse


def test_categoria_valida_recorta_textos() -> None:
    categoria = CategoryCreate.model_validate(
        {"name": "  Medicamentos  ", "description": "  Uso clínico.  "}
    )

    assert categoria.name == "Medicamentos"
    assert categoria.description == "Uso clínico."


def test_descripcion_vacia_es_admisible() -> None:
    categoria = CategoryCreate.model_validate({"name": "Insumos", "description": "   "})

    assert categoria.description == ""


def test_descripcion_es_obligatoria_en_el_cuerpo() -> None:
    with pytest.raises(ValidationError) as excinfo:
        CategoryCreate.model_validate({"name": "Insumos"})

    assert excinfo.value.errors()[0]["loc"] == ("description",)
    assert excinfo.value.errors()[0]["type"] == "missing"


def test_nombre_vacio_se_rechaza() -> None:
    with pytest.raises(ValidationError) as excinfo:
        CategoryCreate.model_validate({"name": "   ", "description": ""})

    assert "nombre de la categoría" in excinfo.value.errors()[0]["msg"]


def test_longitudes_maximas_de_categoria() -> None:
    assert (
        CategoryCreate.model_validate({"name": "A" * 100, "description": "B" * 500}).name
        == "A" * 100
    )

    with pytest.raises(ValidationError):
        CategoryCreate.model_validate({"name": "A" * 101, "description": ""})
    with pytest.raises(ValidationError):
        CategoryCreate.model_validate({"name": "A", "description": "B" * 501})


def test_categoria_rechaza_campos_extra() -> None:
    with pytest.raises(ValidationError) as excinfo:
        CategoryCreate.model_validate({"name": "A", "description": "", "active": False})

    assert excinfo.value.errors()[0]["type"] == "extra_forbidden"


def test_categoria_respuesta_camel_case() -> None:
    respuesta = CategoryResponse(
        id="cat-med", name="Medicamentos", description="Uso clínico.", active=True
    )

    assert respuesta.model_dump() == {
        "id": "cat-med",
        "name": "Medicamentos",
        "description": "Uso clínico.",
        "active": True,
    }
