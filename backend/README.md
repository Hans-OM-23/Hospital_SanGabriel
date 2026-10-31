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

### Autenticación implementada en la etapa 11

- `POST /api/auth/login` acepta `LoginRequest` y devuelve `AuthResponse` (`accessToken` + `user`).
- `apis/auth_api.py` es público, independiente de los endpoints protegidos.
- `services/auth_service.py` valida Argon2id y emite JWT únicamente si la cuenta está activa.
- `repositories/users.py` implementa `SqlServerUserRepository`, que ejecuta solo
  `dbo.usp_ObtenerUsuarioPorCorreo` y `dbo.usp_ObtenerUsuarioPorId` (archivo
  `db/13_procedures_users.sql`) con parámetros ODBC; no accede a tablas directamente.
- Devuelve 401 genérico para credenciales incorrectas, 503 ante fallos de SQL y
  500 si falta la configuración JWT, sin revelar hashes, contraseñas o errores ODBC.
- La respuesta exitosa incluye `Cache-Control: no-store`.
- Las pruebas funcionan con repositorios falsos; no contienen cuentas ni claves reales.

### Pendientes de integración real

- Instalar la base `HospitalSanGabriel` y `db/13_procedures_users.sql`.
- Aprovisionar al menos un usuario en `dbo.Users` con hash Argon2id generado
  localmente y sin guardar la contraseña en Git. El proyecto no incluye cuentas
  de demostración en producción.
- Actualización del hash cuando cambien los parámetros de Argon2id.
- Renovación o revocación de tokens.
- Verificación de que un usuario no ha sido desactivado después de emitirle
  el token (pendiente del repositorio real de usuarios).

No se ha conectado ni ejecutado SQL Server en esta etapa.

## Consultas HTTP de inventario (etapa 8)

La API publica cinco endpoints de **lectura**, bajo `/api`, que respetan
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
usuarios ni inventarios falsos en producción. El inicio de sesión se implementó en la etapa 11, pero depende de usuarios persistidos y procedimientos instalados.

Las pruebas de las rutas inyectan un servicio aislado únicamente en los tests;
para ejecutarlas desde `backend/`:

```bash
uv run pytest -q
```


## Etapa 9 — Escritura de categorías y fichas de productos

Se implementan cuatro operaciones adicionales del contrato Angular:

| Ruta | Respuesta |
| --- | --- |
| `POST /api/categories` | `201` con `Category` creada |
| `POST /api/products` | `201` con `Product` creado, sin stock inicial |
| `PUT /api/products/{id}` | `200` con ficha `Product` actualizada |
| `PATCH /api/products/{id}/status` | `204` sin cuerpo |

Las rutas requieren un JWT válido del perfil `Responsable de almacén`.
Los errores se devuelven con `detail` compatible con Angular: `409` para
categoría/código duplicados y cambios incompatibles con movimientos, `404`
para producto inexistente, `422` para categoría inválida y `503` ante errores
de SQL Server, sin filtrar mensajes del controlador.

La cadena de escritura es `apis/inventory_api.py` →
`services/inventory_write_service.py` → `repositories/inventory_write.py` →
`dbo.usp_*` de `db/11_procedures_catalog_write.sql`.
`Database.transaction()` asegura commit/rollback y todos los valores de
entrada se pasan a procedimientos parametrizados. No hay DML directo desde
Python ni usuarios de demostración en producción.

**Estado:** código y procedimientos preparados, **NO instalados ni probados
contra SQL Server**. Las pruebas automatizadas usan dependencias/cursor
simulados; la instalación SQL, permisos de la cuenta de aplicación y las
pruebas de concurrencia reales siguen pendientes. El inicio de sesión se incorporó en la etapa 11. El registro de entradas/salidas
está preparado en la etapa 10, pero aún no instalado en SQL Server.


## Etapa 10 — Registrar movimientos

`POST /api/movements` recibe `MovementInput` y devuelve `Movement` (201) con
JSON camelCase. El endpoint requiere un JWT del perfil Responsable de almacén.
El servicio convierte identificadores a UUID; el repositorio invoca únicamente
`dbo.usp_RegistrarMovimiento` por parámetros y administra commit/rollback.
El script correspondiente es `db/12_procedures_movements.sql`.

La lógica de SQL gestiona entradas (lote nuevo o existente), salidas por lote
con área hospitalaria, vencimientos, stock insuficiente y saldos históricos
del **producto** en una sola transacción. Las operaciones sobre un mismo
producto se serializan mediante bloqueo de su fila. Los errores previstos
regresan como 409 o 422 con `detail` compatible con Angular; fallos no
identificados de SQL Server responden 503 sin revelar el controlador.

**Límite actual:** los procedimientos no se han instalado ni ejecutado
contra SQL Server. Las pruebas automatizadas usan servicios/cursores
simulados. Falta probar transacciones concurrentes reales y resolver la
idempotencia del POST cuando se pierde una respuesta (el frontend aún no envía
una clave de operación). La ruta `/api/auth/login` está implementada en la etapa 11, pero requiere
instalar los procedimientos y crear usuarios reales.

## Etapa 12 — Contrato HTTP y errores de validación seguros

Se añade `apis/error_handlers.py` y su registro en `main.py`, sin alterar
las rutas existentes ni el contrato JSON del frontend.

- Los errores de entrada HTTP 422 devuelven `detail` como lista de objetos
  `{ "loc": ["body", "campoCamelCase"], "msg": "...", "type": "..." }`.
  Mantienen los alias `camelCase` para que `explainError` de Angular identifique
  el campo correspondiente.
- **Nunca se devuelven** `input`, `ctx`, `url` ni valores enviados por el usuario
  dentro de los errores de validación. Esto es especialmente importante para
  no devolver contraseñas introducidas incorrectamente en `/api/auth/login`.
  Los mensajes genéricos se proporcionan en español sin interpolar entradas.
- Se limita a 30 el número de errores de validación públicos por petición.
- Los errores 404 (ruta inexistente) y 405 (método no permitido) mantienen
  `detail` con mensajes en español; en 405 se conserva el encabezado `Allow`.
- Los errores de `POST /api/auth/login` gestionados por los nuevos handlers
  llevan `Cache-Control: no-store` y `Pragma: no-cache`.
- Se conservan los estados y formatos anteriores para 401 (token ausente o
  inválido), 403 (rol no autorizado), 404/409/422 de negocio y 503 (BD no
  disponible), sin mostrar mensajes técnicos de `pyodbc`.
- Las pruebas `tests/test_http_error_contract.py` comprueban los **11
  métodos y rutas** de `frontend/docs/API-CONTRACT.md`, JWT de inventario,
  errores sin filtraciones, CORS y compatibilidad de los campos con Angular.

**Limitación:** las pruebas de la etapa 12 se ejecutan sin SQL Server mediante
sustitución de dependencias. Los procedimientos SQL todavía deben instalarse y
verificarse contra la base real. No se modifica el frontend, `.env`, ni la
configuración de puertos.

Desde `backend/`:

```powershell
uv run pytest -q
```

## Etapa 13 — Diagnóstico y pruebas de integración SQL (sin ejecutar SQL)

Se incorporan herramientas y pruebas para comprobar **más adelante** la instalación
real. Prepararlas no crea ni modifica bases de datos. Los repositorios de
negocio siguen usando exclusivamente procedimientos almacenados.

Desde `backend/`, **sin tocar SQL Server**:

```powershell
uv run python scripts/check_sql_readiness.py
uv run pytest -q
```

El primer comando solo comprueba la disponibilidad del controlador ODBC y si
existen los valores de configuración; **no imprime contraseñas ni claves JWT**.
El segundo ejecuta las pruebas sin conexión. `test_sql_object_contract.py`
verifica que los 12 procedimientos declarados en los scripts correspondan a
los `EXEC` de repositorios Python, incluyendo nombres y orden de parámetros.

**Solo cuando esté instalada** la base `HospitalSanGabriel`, exista un login SQL
de aplicación autorizado y hayas cambiado `DB_NAME` de `master` a
`HospitalSanGabriel` en tu `.env` local, podrás hacer el diagnóstico explícito:

```powershell
uv run python scripts/check_sql_readiness.py --connect
$env:RUN_DB_TESTS="1"
uv run pytest -q -m integration
Remove-Item Env:RUN_DB_TESTS
```

- `--connect` **rechaza master** y solo consulta `sys.tables`, `sys.procedures`,
  restricciones, FK compuesta y permisos `EXECUTE`; no escribe datos.
- Las pruebas de integración comprueban los 12 procedimientos, 6 tablas,
  restricciones críticas y las cinco consultas de inventario contra SQL real,
  sin realizar movimientos ni insertar usuarios.
- Un procedimiento ausente, permiso `EXECUTE` insuficiente o una forma de
  respuesta incompatible hará fallar las pruebas (es útil para el diagnóstico).
- Si la cuenta SQL no puede ver determinados metadatos, el diagnóstico puede
  indicar "ausente/no visible"; confirma los permisos antes de asumir que el
  objeto no existe.
- Las pruebas existentes de conexión (dos pruebas de la etapa 3) también se
  ejecutarán al activar `RUN_DB_TESTS=1`.

**Pendiente:** creación de la base, ejecución real de los scripts `00` a `13`,
cuenta SQL de aplicación, datos de usuarios y pruebas transaccionales con
concurrencia. Ninguno se ejecutó durante esta etapa.
