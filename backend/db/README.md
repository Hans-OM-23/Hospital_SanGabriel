# SQL Server — HospitalSanGabriel

Scripts de instalación reproducible para la base de datos hospitalaria. El
modelo incluye **6 tablas**, claves GUID, relaciones, restricciones, índices,
**12 procedimientos almacenados** y transacciones para entradas/salidas.

## Instalación rápida para la exposición (un solo archivo)

En una instancia **de pruebas** de SQL Server **2016 SP1 o posterior**, abrir
`INSTALAR_HOSPITAL_SAN_GABRIEL.sql` desde SSMS y ejecutar **F5 una vez**.
El archivo integra los scripts en el orden correcto, crea una cuenta de
**demostración** (`admin@hospital.com`, contraseña `HospitalDemo2026!`) si
no existe y termina con las verificaciones. La cuenta es pública para la demo:
**no usarla para información real ni publicar el sistema con esa contraseña**.
El instalador no borra el inventario existente y no restablece contraseñas
anteriores. Si hubo un error, corregirlo antes de reintentar; este archivo
**no es un sistema de migraciones**. El último bloque verifica los objetos,
los datos de demostración y los saldos, y muestra un error explícito si fallan.

Para una instalación real, ejecutar los scripts individuales sin crear la
cuenta compartida de demostración y usar credenciales propias.

## Conexión de FastAPI en la computadora de la universidad

**Son dos cuentas distintas:** el instalador crea `admin@hospital.com` dentro de
`dbo.Users` para iniciar sesión en la **web**. No crea el login SQL Server
identificado por `DB_USER` para que el **backend** se conecte al motor.

1. Preguntar qué instancia y usuario de autenticación SQL proporciona el laboratorio.
2. Abrir SSMS con una cuenta autorizada, ejecutar el instalador general y verificar
   el mensaje `INSTALACIÓN VERIFICADA` sin errores en la pestaña Mensajes.
3. Si la cuenta de `DB_USER` ya puede conectarse a `HospitalSanGabriel` y ejecutar
   procedimientos, **no hay que crearla ni darle privilegios adicionales**.
4. Si el login SQL existe pero aún no tiene acceso a la base, un administrador
   puede ejecutar el siguiente bloque, reemplazando `LOGIN_DE_LABORATORIO` por
   el **nombre real** de ese login. Nunca pegar contraseñas aquí:

   ```sql
   USE HospitalSanGabriel;
   GO
   IF DATABASE_PRINCIPAL_ID(N'LOGIN_DE_LABORATORIO') IS NULL
       CREATE USER [LOGIN_DE_LABORATORIO] FOR LOGIN [LOGIN_DE_LABORATORIO];
   GO
   GRANT EXECUTE ON SCHEMA::dbo TO [LOGIN_DE_LABORATORIO];
   GO
   ```

   Este bloque requiere que el login exista y que quien lo ejecute tenga permiso
   para crear el usuario de base de datos y asignar permisos. Si no existe el
   login, debe habilitarlo el responsable de la instancia. **No es necesario
   conceder `sysadmin` ni `db_owner` a la aplicación**.
5. Editar `backend/.env` con `DB_SERVER`, `DB_NAME=HospitalSanGabriel`,
   `DB_USER` y `DB_PASSWORD` de **esa computadora**, conservando la clave JWT
   requerida por el login web. No cambiar `DB_NAME` a `master`.
6. Verificar el acceso iniciando FastAPI y probando `GET /api/products` en
   Swagger después de iniciar sesión en `POST /api/auth/login`.

El instalador general sigue siendo **un solo archivo SQL**. El bloque de permisos
solo hace falta si la cuenta de SQL Server del laboratorio carece de acceso.

## Orden exacto en SSMS

Abrir **cada archivo completo** en SQL Server Management Studio y ejecutar
con **F5**, en este orden:

| Orden | Archivo | Propósito |
|---|---|---|
| 1 | `00_create_database.sql` | Crea la base si no existe |
| 2 | `01_create_tables.sql` | 6 tablas y sus restricciones |
| 3 | `02_create_indexes.sql` | Índices de consultas |
| 4 | `03_seed_reference_data.sql` | 4 categorías y 4 áreas |
| 5 | `04_seed_demo_inventory.sql` | 3 productos, 3 lotes, 4 movimientos (demo) |
| 6 | `10_procedures_read.sql` | 5 consultas |
| 7 | `11_procedures_catalog_write.sql` | 4 operaciones de catálogo |
| 8 | `12_procedures_movements.sql` | 1 operación transaccional de movimientos |
| 9 | `13_procedures_users.sql` | 2 consultas para autenticación |
| 10 | `99_verify_schema.sql` | Diagnóstico de solo lectura al final |

Si el sistema **ya está instalado en tu SQL Server**, no es necesario volver
a ejecutar los scripts. El script `04` es solo para una base de demostración.
Los scripts no incluyen credenciales personales ni usuarios de aplicación.

## Comprobar la instalación

```sql
USE HospitalSanGabriel;
GO
SELECT (SELECT COUNT(*) FROM sys.tables WHERE schema_id = SCHEMA_ID('dbo')) AS Tablas,
       (SELECT COUNT(*) FROM sys.procedures WHERE schema_id = SCHEMA_ID('dbo')) AS Procedimientos,
       (SELECT COUNT(*) FROM dbo.Categories) AS Categorias,
       (SELECT COUNT(*) FROM dbo.HospitalAreas) AS Areas;
EXEC dbo.usp_ListarProductos;
```

Se esperan 6 tablas, 12 procedimientos, 4 categorías y 4 áreas al instalar
los datos iniciales. El número de productos/movimientos puede ser mayor si
ya se hicieron pruebas desde Swagger. Ejecutar `99_verify_schema.sql` para
comprobar claves, índices, relaciones y conciliación de saldos; las consultas
marcadas «Esperado: 0 filas» no deberían devolver inconsistencias.

## Integridad

- `Products.code` es único también para productos inactivos.
- El número del lote es único dentro de cada producto y conserva vencimiento.
- `usp_RegistrarMovimiento` bloquea la ficha de producto mientras calcula y
  actualiza lotes, y registra el movimiento en una transacción atómica.
- Salidas requieren lote, área, cantidad disponible y lote no vencido.
- `stock_before` y `stock_after` del movimiento son del producto completo.
- No hay borrado físico; el producto se desactiva para preservar su historial.

Las contraseñas de aplicación van como hashes Argon2id en `dbo.Users`.
FastAPI lee los datos de conexión desde `backend/.env`; el instalador SQL no
contiene contraseñas de SQL Server. Usar un login del laboratorio con permisos
limitados a ejecutar los procedimientos.
