# Backend — API Inventario Hospital San Gabriel

Backend del Sistema de Gestión de Inventario, construido con FastAPI,
Pydantic v2 y `uv`. La arquitectura es `main.py → apis → services →
repositories`, con `schemas` para los modelos HTTP y `core` para configuración,
seguridad y acceso a SQL Server.

## Comandos

Desde `backend/`:

```bash
uv sync
uv run uvicorn backend.main:app --port 8000
uv run pytest -q
```

## Seguridad de autenticación (etapa 6)

Dependencias añadidas con `uv`:

| Dependencia | Uso |
| ----------- | --- |
| `argon2-cffi` | Hash y verificación de contraseñas con Argon2id, con sal aleatoria por hash. No se guarda ni registra la contraseña en texto plano. |
| `PyJWT` | Firma y validación de tokens JWT HS256. Se valida firma, algoritmo, `exp`, `iat` y los claims obligatorios sin implementar criptografía manual. |

Componentes:

- `core/security.py`: `hash_password`, `verify_password`,
  `create_access_token` y `decode_access_token`. No depende de FastAPI ni de
  la base de datos.
- `core/config.py`: `JWT_SECRET_KEY` (mínimo 32 caracteres) y
  `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` (1 a 10080). Sin una clave propia y segura
  no se emiten tokens; no existe una clave fija de respaldo.
- `apis/dependencies.py`: autenticación Bearer con `HTTPBearer` y autorización
  por rol. Responde 401 ante token ausente o inválido, 403 ante permisos
  insuficientes y 500 si falta configuración.
- `repositories/users.py`: interfaz `UserRepository` para consultar
  `dbo.Users`; todavía no tiene implementación ni ejecuta SQL.
- `services/auth_service.py`: verifica credenciales contra la interfaz del
  repositorio y emite el JWT. Se prueba con repositorios falsos en tests.

Configuración en `backend/.env` (ver `.env.example`). Genera la clave con:

```bash
uv run python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Pendiente hasta implementar la persistencia

- Procedimiento almacenado e implementación real de `UserRepository`.
- Endpoint `POST /api/auth/login` y su router; no existe todavía.
- Actualización del hash cuando cambien los parámetros de Argon2id.
- Renovación o revocación de tokens.
- Verificación de que un usuario no ha sido desactivado después de emitirle
  el token (pendiente del repositorio real de usuarios).

No se ha conectado ni ejecutado SQL Server en esta etapa.

## Consultas HTTP de inventario (etapa 8)

La API publica cinco endpoints de **solo lectura**, bajo `/api`, que respetan
`frontend/docs/API-CONTRACT.md`:

| Ruta | Respuesta |
| --- | --- |
| `GET /api/products` | `Product[]` (incluye inactivos) |
| `GET /api/categories` | `Category[]` |
| `GET /api/lots` | `Lot[]` |
| `GET /api/areas` | `HospitalArea[]` |
| `GET /api/movements` | `Movement[]`, en orden de registro ascendente |

Todos exigen `Authorization: Bearer <JWT>` con rol `Responsable de almacén`.
Devuelven 401 para token ausente o inválido, 403 para rol insuficiente, 503 si
SQL Server o su configuración no están disponibles, sin incluir credenciales
en el mensaje. `/health` permanece público.

La cadena es `main.py → apis/inventory_api.py →
services/inventory_read_service.py → repositories/inventory_read.py →
procedimientos almacenados`. El servicio y la API no ejecutan SQL directo.

**IMPORTANTE**: Las rutas son reales, pero no tendrán lecturas exitosas de la
base del hospital hasta que `HospitalSanGabriel` y el archivo
`db/10_procedures_read.sql` estén instalados, y exista una cuenta de aplicación
con permisos `EXECUTE`. Un token de prueba se usa solamente en tests; no hay
usuarios ni inventarios falsos en producción. El endpoint de login y las
operaciones de escritura continúan pendientes.

Las pruebas de las rutas inyectan un servicio aislado únicamente en los tests;
para ejecutarlas desde `backend/`:

```bash
uv run pytest -q
```
