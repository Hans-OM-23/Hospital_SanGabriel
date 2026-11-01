# SQL Server — HospitalSanGabriel

Scripts de instalación reproducible para la base de datos hospitalaria. El
modelo incluye **6 tablas**, claves GUID, relaciones, restricciones, índices,
**12 procedimientos almacenados** y transacciones para entradas/salidas.

## Instalación rápida para la exposición (un solo archivo)

En una instancia **de pruebas** de SQL Server, abrir
`INSTALAR_HOSPITAL_SAN_GABRIEL.sql` desde SSMS y ejecutar **F5 una vez**.
El archivo integra los scripts en el orden correcto, crea una cuenta de
**demostración** (`admin@hospital.com`, contraseña `HospitalDemo2026!`) si
no existe y termina con las verificaciones. La cuenta es pública para la demo:
**no usarla para información real ni publicar el sistema con esa contraseña**.
El instalador se puede volver a ejecutar sin borrar el inventario existente;
no restablece la contraseña de usuarios previamente creados.

Para una instalación real, ejecutar los scripts individuales sin crear la
cuenta compartida de demostración y usar credenciales propias.

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
La conexión desde FastAPI usa credenciales SQL guardadas **solo en el `.env`
local**, nunca en estos archivos. No asignar al usuario de aplicación permisos
más altos de los necesarios.
