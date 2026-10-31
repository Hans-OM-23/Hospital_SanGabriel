
# AGENTS.md — Backend Hospital San Gabriel

## Contexto del proyecto

Este backend forma parte del Sistema de Gestión de Inventario del Hospital San Gabriel.

- El frontend está desarrollado en Angular 22 con Signal Forms.
- El backend se desarrollará con Python y FastAPI.
- La base de datos será SQL Server.
- El proyecto Python utiliza `uv` como gestor de dependencias.
- El servidor ASGI será Uvicorn.
- El desarrollo se realiza en el repositorio compartido Hospital_SanGabriel.

Antes de implementar funcionalidades, revisar la documentación en `../frontend/docs/`, especialmente `API-CONTRACT.md`, y los servicios e interfaces del frontend.

## Arquitectura obligatoria

Respetar la arquitectura por capas enseñada en clase:

main.py → apis → services → repositories

Además, utilizar `schemas` para los modelos Pydantic y `core` para la configuración y conexión a la base de datos.

El código Python debe ubicarse dentro de `src/backend/`.

Responsabilidades:

- main.py: inicialización de FastAPI, CORS y registro de routers.
- apis/: endpoints HTTP, parámetros y respuestas.
- services/: lógica de negocio y validaciones.
- repositories/: acceso a SQL Server mediante procedimientos almacenados.
- schemas/: modelos Pydantic de entrada y salida.
- core/: configuración y conexión a SQL Server.

Mantener las responsabilidades separadas. No colocar consultas SQL ni lógica de inventario directamente en los endpoints.

## Base de datos

- Utilizar Microsoft SQL Server.
- Utilizar autenticación de SQL Server mediante usuario y contraseña.
- No utilizar autenticación integrada de Windows.
- Utilizar `pyodbc` para la conexión.
- No utilizar ORM.
- No utilizar SQLAlchemy ORM ni Entity Framework.
- Toda operación de persistencia y consulta a SQL Server debe realizarse mediante procedimientos almacenados.
- Desde Python ejecutar procedimientos almacenados con parámetros, evitando concatenar datos en SQL.
- Utilizar transacciones para las operaciones que modifican inventario.
- Garantizar que los movimientos y la actualización del stock sean atómicos.
- Crear scripts SQL reproducibles para tablas, restricciones, procedimientos almacenados y datos de prueba.

## Configuración

La conexión a SQL Server debe utilizar un archivo `.env` dentro de `backend/`.

Variables previstas:

- DB_SERVER
- DB_NAME
- DB_USER
- DB_PASSWORD
- DB_DRIVER
- DB_ENCRYPT
- DB_TRUST_SERVER_CERTIFICATE

No agregar variables DB_PORT ni PORT al archivo `.env`.

El nombre del servidor o instancia se especificará mediante DB_SERVER.

No colocar credenciales directamente en el código.

No subir `.env` al repositorio. Proporcionar `.env.example` sin credenciales reales.

## API e integración con Angular

- Respetar los endpoints definidos en `../frontend/docs/API-CONTRACT.md`.
- Mantener los nombres de propiedades JSON en camelCase.
- Respetar los identificadores de tipo string utilizados por Angular.
- Utilizar fechas en formato YYYY-MM-DD.
- Mantener los formatos de respuesta y error esperados por el frontend.
- Configurar CORS para permitir la comunicación con Angular.
- El frontend espera la API bajo `/api`.
- No modificar el frontend sin una necesidad justificada y previamente revisada.
- No cambiar los contratos de la API unilateralmente.

## Funcionalidades del inventario

Implementar las funcionalidades exigidas por el proyecto:

- Autenticación de usuarios.
- Gestión de productos.
- Gestión de categorías.
- Consulta y control de lotes.
- Consulta de áreas hospitalarias.
- Registro de entradas.
- Registro de salidas.
- Historial de movimientos.

Respetar las reglas de negocio descritas en `frontend/docs/`.

En particular:

- Impedir stock negativo.
- Impedir salidas de lotes vencidos.
- Registrar las entradas y salidas correctamente.
- Mantener la trazabilidad de los lotes.
- Validar los datos antes de ejecutar operaciones.
- Proteger las operaciones de inventario frente a accesos no autorizados.
- No almacenar contraseñas de usuarios de la aplicación en texto plano.

## Herramientas y ejecución

Utilizar `uv` para administrar las dependencias de Python.

El servidor FastAPI deberá poder ejecutarse desde la carpeta `backend/` mediante:

`uv run uvicorn backend.main:app --port 8000`

No asumir que el servidor puede ejecutarse hasta que exista la aplicación FastAPI correspondiente.

## Metodología de desarrollo

- Trabajar únicamente en la rama Jimmy.
- No modificar directamente main ni la rama Hans.
- Implementar funcionalidades por etapas.
- Utilizar OpenCode en modo Plan antes de implementar cambios importantes.
- Revisar el plan antes de utilizar Build.
- No generar todo el proyecto de una sola vez.
- Mantener el código organizado, legible y coherente con lo enseñado en clase.
- Crear pruebas para las reglas críticas del inventario.
- No afirmar que una funcionalidad está probada si no se ha ejecutado su verificación.
- Registrar los avances mediante commits descriptivos.
- Preparar la integración mediante Pull Requests.
