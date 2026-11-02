# Backend FastAPI — Hospital San Gabriel

Backend de inventario hospitalario, desarrollado con Python 3.12, FastAPI,
Pydantic 2, uv, pyodbc y Microsoft SQL Server. **No utiliza ORM.**

## Iniciar

1. Revisar `backend/.env` y configurar el acceso a **HospitalSanGabriel**
   en el equipo del laboratorio. Se incluye de forma excepcional para
   el examen académico; **las credenciales que trae son locales al equipo
   de desarrollo y deben sustituirse si la instalación es diferente**.
2. Instalar ODBC Driver 18 for SQL Server y ejecutar los scripts de `db/`
   según `db/README.md` si la base todavía no está instalada.
3. Desde la carpeta `backend`:

```powershell
uv sync
uv run uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

- Swagger: http://127.0.0.1:8000/docs
- `GET /health` público: http://127.0.0.1:8000/health
- Operaciones de inventario protegidas por JWT Bearer: requieren iniciar
  sesión mediante `POST /api/auth/login`.

## Arquitectura

```text
src/backend/main.py
  └── apis/           # Rutas HTTP, dependencias, autenticación y errores
       └── services/ # Reglas de negocio, validaciones y orquestación
            └── repositories/ # EXEC parametrizados de procedimientos almacenados
                 └── core/database.py # pyodbc, conexiones, commit/rollback
  └── schemas/        # Modelos de entrada y salida Pydantic
```

Las 11 operaciones bajo `/api` corresponden a
`../frontend/docs/API-CONTRACT.md` (camelCase, fechas `YYYY-MM-DD`).
Los 12 procedimientos están en `db/10_*.sql` a `db/13_*.sql`.

## Pruebas

```powershell
uv run pytest -q
uv run python scripts/check_sql_readiness.py --connect
```

El primer comando ejecuta **pruebas unitarias y de contrato**; las pruebas que
necesitan acceso SQL se omiten sin activar el indicador. El segundo comando
comprueba objetos, permisos y conectividad de SQL Server de **solo lectura**.

Para incluir pruebas de integración de lectura en la base configurada:

```powershell
$env:RUN_DB_TESTS="1"
uv run pytest -q -m integration
Remove-Item Env:RUN_DB_TESTS
```

Los tests de integración requieren SQL Server accesible desde el equipo y
una cuenta autorizada. No se consideran superados hasta ejecutarlos con esa
instancia. La prueba de movimientos/concurrencia puede demostrarse desde
Swagger y SQL Server según `../frontend/docs/SUSTENTACION.md`.

## Seguridad y lógica del sistema

- SQL Authentication para la aplicación (`DB_USER`, `DB_PASSWORD` solo en `.env`).
- Argon2id para las contraseñas de `dbo.Users`. JWT HS256 para login.
- La clave `JWT_SECRET_KEY` debe ser **privada**, con al menos 32 caracteres.
  No reutilizar la clave del examen en otros entornos.
- Las escrituras usan `Database.transaction()` y procedimientos almacenados;
  se rechazan códigos duplicados, salidas de lotes vencidos, stock insuficiente
  y referencias inválidas.
- El stock por lote se calcula en `Lots.stock`; `Movements.stock_before/after`
  representa el **saldo total del producto**, y debe mantenerse consistente.
- El cliente no ejecuta SQL directo. Los errores SQL internos no se exponen
  al navegador.
