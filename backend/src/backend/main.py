"""Inicialización de FastAPI, CORS y registro de routers."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.apis.health_api import router as health_router
from backend.apis.router import api_router
from backend.core.config import get_settings
from backend.core.exceptions import DatabaseError, InventoryOperationError


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

    @app.exception_handler(DatabaseError)
    async def database_unavailable(_request: Request, _error: DatabaseError) -> JSONResponse:
        # No revelar nombres de cuentas, credenciales ni mensajes de pyodbc.
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "El servicio de inventario no está disponible en este momento."},
        )

    @app.exception_handler(InventoryOperationError)
    async def inventory_rejected(_request: Request, error: InventoryOperationError) -> JSONResponse:
        detail: str | dict[str, str] = str(error)
        if error.field:
            detail = {"field": error.field, "message": str(error)}
        return JSONResponse(status_code=error.status_code, content={"detail": detail})

    app.include_router(health_router)
    app.include_router(api_router)

    return app


app = create_app()


def run() -> None:
    """Arranca el servidor de desarrollo mediante `uv run backend`."""
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000)
