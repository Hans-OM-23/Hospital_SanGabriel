"""Configuración JWT: nunca hay secreto de respaldo ni fugas de claves."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.core.config import Settings
from backend.core.exceptions import AuthConfigurationError


def test_no_hay_secret_predeterminado_de_jwt() -> None:
    settings = Settings(_env_file=None, jwt_secret_key="")
    assert settings.jwt_configured is False
    with pytest.raises(AuthConfigurationError):
        settings.require_jwt_secret()


def test_secret_propio_se_conserva_oculto_en_representaciones() -> None:
    secret = "seguro-solo-para-pruebas-" + "Z" * 48
    settings = Settings(_env_file=None, jwt_secret_key=secret, jwt_access_token_expire_minutes=15)
    assert settings.jwt_configured is True
    assert settings.require_jwt_secret() == secret
    assert settings.jwt_access_token_expire_minutes == 15
    assert secret not in repr(settings)
    assert secret not in str(settings.model_dump(mode="json"))


@pytest.mark.parametrize("secret", ["corta", "1234567890123456789012345678901"])
def test_secret_corto_se_rechaza_al_crear_configuracion(secret: str) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, jwt_secret_key=secret)


def test_secret_publico_de_ejemplo_no_se_puede_usar() -> None:
    settings = Settings(_env_file=None, jwt_secret_key="ejemplo-publico-no-usar-en-produccion-0123456789abcdef")
    assert settings.jwt_configured is False
    with pytest.raises(AuthConfigurationError):
        settings.require_jwt_secret()


@pytest.mark.parametrize("minutes", [0, -1, 10081])
def test_vigencia_fuera_de_rango_es_invalida(minutes: int) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, jwt_access_token_expire_minutes=minutes)
