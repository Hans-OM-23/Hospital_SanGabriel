# Hospital San Gabriel — inventario hospitalario

Sistema web desarrollado con **Angular 22 + Signal Forms**, **FastAPI** y **SQL Server**.
Incluye inicio de sesión, productos, categorías, entradas/salidas por lote, historial,
alertas por stock bajo/vencimientos e indicadores. Las operaciones SQL del backend
se realizan mediante **procedimientos almacenados**.

## Puesta en marcha local

1. Instalar **Python 3.12**, `uv`, **Node.js 24.15 o superior** y SQL Server con **ODBC Driver 18**.
2. En SQL Server Management Studio, abrir `backend/db/INSTALAR_HOSPITAL_SAN_GABRIEL.sql`
   y ejecutar todo el archivo con **F5**, en una base de **pruebas**. Si ya está instalada,
   no es necesario ejecutar nuevamente el instalador.
3. Ajustar el archivo `backend/.env` para **la computadora del laboratorio**:
   `DB_SERVER`, `DB_NAME=HospitalSanGabriel`, `DB_USER`, `DB_PASSWORD` y
   `JWT_SECRET_KEY`. Este archivo se incluye **excepcionalmente para la
   evaluación académica**; contiene las credenciales locales del equipo de
   desarrollo, que pueden no funcionar en el laboratorio. Usar credenciales
   exclusivas de pruebas y cambiarlas antes de cualquier uso externo.
4. En una terminal, desde `backend/`, ejecutar:

   ```powershell
   uv sync
   uv run uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
   ```
5. En otra terminal, desde `frontend/`, ejecutar:

   ```powershell
   npm ci
   npm start
   ```

Abrir **http://localhost:4200/**. La API de pruebas está en
**http://127.0.0.1:8000/docs**. `frontend/src/environments/environment.ts`
debe tener `useMock: false` para consultar SQL Server; **no cambiarlo** a `true` durante
la demostración integrada. La documentación histórica dentro de `frontend/`
describe también el modo de demostración de Hans; para instalar la versión
integrada, usar las instrucciones de este README.

**Cuenta de prueba:** el instalador crea `admin@hospital.com` solo cuando no existe.
Su contraseña es `HospitalDemo2026!` **exclusivamente para demostración local**.
Cambiarla si se usa fuera de un entorno de pruebas. Las credenciales de SQL Server
son **independientes** de esa cuenta del hospital.

## Organización

- `frontend/`: pantallas Angular, Signal Forms, servicios HTTP, pruebas unitarias.
- `backend/src/backend/apis/`: endpoints y manejo HTTP.
- `backend/src/backend/services/`: reglas de negocio.
- `backend/src/backend/repositories/`: invocación de procedimientos SQL.
- `backend/src/backend/schemas/`: modelos y validaciones Pydantic.
- `backend/db/`: tablas, índices, datos semilla, procedimientos y verificación.

## Verificar

- Backend: desde `backend/`, `uv run pytest -q`.
- Base: ejecutar `backend/db/99_verify_schema.sql` en SSMS y comprobar que
  las consultas de inconsistencias no devuelvan filas.
- Frontend: desde `frontend/`, `npm run build` y `npm test -- --watch=false`.
- Integración: iniciar sesión, crear y editar un producto, registrar una entrada
  y una salida, y revisar los saldos en Angular y SSMS.
- Git: realizar commits en ramas de trabajo y **abrir un Pull Request** para integrar.

El backend requiere una base SQL Server activa. Las pruebas unitarias sin SQL
**no sustituyen** las verificaciones de integración en la computadora de entrega.
