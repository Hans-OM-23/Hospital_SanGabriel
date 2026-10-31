"""Inicialización de FastAPI, CORS y registro de routers."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.apis.health_api import router as health_router
from backend.apis.router import api_router
from backend.core.config import get_settings


def create_app() -> FastAPI:
    """Crea la aplicación con su configuración y sus enrutadores."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Sistema de Gestión de Inventario del Hospital San Gabriel.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        # La autenticación se enviará con el encabezado Authorization, no con cookies.
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    app.include_router(health_router)
    app.include_router(api_router)

    return app


app = create_app()


def run() -> None:
    """Arranca el servidor de desarrollo mediante `uv run backend`."""
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000)
