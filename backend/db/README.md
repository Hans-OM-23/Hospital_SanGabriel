# Base de datos `HospitalSanGabriel` — scripts de la etapa 4

Scripts reproducibles para crear el esquema inicial del Sistema de Gestión de
Inventario del Hospital San Gabriel en SQL Server, con autenticación SQL.

**Estos archivos se entregan sin ejecutar.** Ningún script ha sido lanzado
contra SQL Server durante su creación. La conexión real y la creación de la
base quedan a cargo del equipo, con sus cuentas locales.

## Alcance

Incluye:

- Creación de la base `HospitalSanGabriel` si no existe.
- Tablas `Users`, `Categories`, `Products`, `HospitalAreas`, `Lots` y
  `Movements`, con claves primarias, foráneas, `UNIQUE`, `CHECK` y valores por
  defecto.
- Índices de apoyo para historial, lotes y catálogos.
- Catálogos de referencia (áreas y categorías).
- Datos de demostración opcionales y separados.
- Consultas de verificación de solo lectura.

No incluye todavía:

- Procedimientos almacenados ni lógica de inventario.
- Endpoints FastAPI ni repositorios.
- Creación de logins, usuarios de base de datos o permisos. Se hará después de
  comprobar qué cuentas existen y qué permisos tienen realmente.

## Archivos

| Orden | Archivo | Contenido | Ejecución |
| ----- | ------- | --------- | --------- |
| 1 | `00_create_database.sql` | Crea `HospitalSanGabriel` con colación `Modern_Spanish_100_CI_AS` si no existe. No crea tablas en `master`. | Obligatorio |
| 2 | `01_create_tables.sql` | Tablas, PK, FK, CHECK, UNIQUE y defaults. | Obligatorio |
| 3 | `02_create_indexes.sql` | Índices no clusterizados. | Obligatorio |
| 4 | `03_seed_reference_data.sql` | 4 áreas y 4 categorías con identificadores fijos. Sin usuarios ni contraseñas. | Recomendado |
| 5 | `04_seed_demo_inventory.sql` | 3 productos, 3 lotes y 4 movimientos coherentes para la demo. | **Opcional**, solo demostración |
| 6 | `99_verify_schema.sql` | Verificación de solo lectura: tablas, FK, CHECK, índices, huérfanos y conciliación de saldos. | Verificación |

## Requisitos de permisos

- **Cuenta administradora**: debe poder crear bases de datos (por ejemplo,
  miembro del rol de servidor `dbcreator` o con `CREATE ANY DATABASE`) y ser
  `db_owner` de `HospitalSanGabriel` para ejecutar `01`–`03`.
- **Cuenta de aplicación**: se definirá en una etapa posterior. Será la que
  use FastAPI mediante `DB_USER` y `DB_PASSWORD` del archivo `backend/.env`, y
  solo tendrá permiso de ejecución sobre los procedimientos almacenados.
- **No se asume que `Auditor1` sea administradora.** Antes de usarla, se debe
  comprobar su identidad y permisos con consultas de solo lectura:

  ```sql
  SELECT
      SUSER_SNAME()                 AS cuenta_actual,
      IS_SRVROLEMEMBER('sysadmin')  AS es_sysadmin,
      IS_SRVROLEMEMBER('dbcreator') AS es_dbcreator;

  SELECT * FROM fn_my_permissions(NULL, 'SERVER');
  ```

  Si no cuenta con permisos suficientes, se debe usar otra cuenta
  administradora proporcionada por el responsable del servidor.
- **No se usa `sa`** ni autenticación integrada de Windows para la aplicación.
- Este directorio **no** contiene scripts de `CREATE LOGIN` ni `GRANT`, ni
  contraseñas, ni cadenas de conexión.

## Orden de ejecución

Desde la raíz del repositorio, con `sqlcmd` (la contraseña se escribe en el
momento; no se guarda en el repositorio ni en el historial de comandos):

```powershell
sqlcmd -S <servidor> -U <cuenta_administradora> -d master -i backend/db/00_create_database.sql -b -f 65001
sqlcmd -S <servidor> -U <cuenta_administradora> -d HospitalSanGabriel -i backend/db/01_create_tables.sql -b -f 65001
sqlcmd -S <servidor> -U <cuenta_administradora> -d HospitalSanGabriel -i backend/db/02_create_indexes.sql -b -f 65001
sqlcmd -S <servidor> -U <cuenta_administradora> -d HospitalSanGabriel -i backend/db/03_seed_reference_data.sql -b -f 65001
sqlcmd -S <servidor> -U <cuenta_administradora> -d HospitalSanGabriel -i backend/db/04_seed_demo_inventory.sql -b -f 65001   # opcional
sqlcmd -S <servidor> -U <cuenta_administradora> -d HospitalSanGabriel -i backend/db/99_verify_schema.sql -b -f 65001
```

`-b` hace que `sqlcmd` termine con código de error si un script falla.
`-f 65001` indica que los archivos están en UTF-8; es necesario para que los
acentos y la `ñ` (`Donación`, `Hospitalización`, `almacén`, `Reposición`) se
lean correctamente, porque los `.sql` se guardan en UTF-8 sin BOM. Con SSMS no
hace falta el parámetro, porque detecta la codificación.

También se pueden abrir los archivos en SQL Server Management Studio y
ejecutarlos en ese orden.

Los scripts usan `GO`, por lo que deben ejecutarse con `sqlcmd` o SSMS, no
desde una única llamada de Python.

## Seguridad

- No se versionan contraseñas, cadenas de conexión ni el archivo `.env`.
- `DB_USER` y `DB_PASSWORD` se configurarán solo cuando exista la cuenta de
  aplicación y sus permisos.
- No se agregan variables `PORT` ni `DB_PORT`. Si se necesita TCP, el puerto
  forma parte de `DB_SERVER` (`localhost,1433`).
- `Users.password_hash` solo admite un hash (bcrypt/argon2id u otro), nunca
  texto plano.

## Idempotencia y seguridad de los scripts

- `00` crea la base solo si no existe y **no la elimina ni la sobrescribe**.
- `01` y `02` usan `IF OBJECT_ID` / `IF NOT EXISTS` sobre `sys.indexes`.
- `03` inserta cada fila solo si no existe por id o por nombre.
- `04` no inserta nada si ya existe cualquiera de los códigos `MED-001`,
  `MAT-001` o `LIM-001`, para evitar seeds parciales.
- `99` es de solo lectura.
- No existe un script destructivo de reinicio. Si se necesita recrear la
  base, debe hacerse manualmente y con respaldo previo.

## Normalización y colación

La base usa una colación CI (insensible a mayúsculas), necesaria para que
nombres como `Medicamentos` sean únicos sin distinguir mayúsculas, igual que
la validación del frontend.

Para las claves que deben ser exactas, `01_create_tables.sql` no confía en la
colación CI:

- `Products.code` y `Lots.number` se validan con
  `COLLATE Latin1_General_BIN2` para exigir mayúsculas y comparación exacta.
- Las restricciones `UNIQUE` siguen siendo CI para impedir duplicados escritos
  con distinta capitalización.
- La normalización definitiva (`TRIM` + `UPPER`) se completará en los
  procedimientos almacenados antes de insertar o actualizar, tal como exige
  el contrato de la API.

## Orden de los movimientos y saldos

- `movement_seq BIGINT IDENTITY` ofrece un orden interno estable y
  determinista para el historial y para desempatar fechas iguales.
- Es monótono, pero **puede tener huecos**: un `ROLLBACK` consume números.
  Los huecos no afectan a ningún cálculo.
- **No representa el orden global exacto de `COMMIT` entre productos
  distintos.** Lo que debe ser consistente es la cadena de
  `stockBefore`/`stockAfter` **dentro de cada producto**.
- Esa consistencia se garantizará en la etapa de procedimientos almacenados
  serializando las operaciones por producto (bloqueo de la fila del producto
  dentro de la transacción) y calculando los saldos antes y después del
  cambio. `movement_seq` se asigna mientras se mantiene ese bloqueo, por lo
  que el orden dentro del producto coincide con el orden de confirmación.
- `CK_Movements_Balance` obliga a que
  `stock_after = stock_before ± quantity`; los procedimientos deberán además
  respetar la cadena entre movimientos consecutivos del mismo producto.

## Consistencia de los datos de demostración

`04_seed_demo_inventory.sql` inserta:

| Producto | Lote | Entradas | Salidas | Stock del lote | Último `stock_after` |
| -------- | ---- | -------- | ------- | -------------- | -------------------- |
| `MED-001` | `PAR-026` | 50 | 10 | 40 | 40 |
| `MAT-001` | `GUA-026` | 4 | 0 | 4 | 4 |
| `LIM-001` | `ALC-025` | 2 | 0 | 2 | 2 |

Las fechas son relativas al día de ejecución: `PAR-026` vence en 180 días,
`GUA-026` en 900 días y `ALC-025` ya está vencido (5 días atrás), para que la
demo muestre vencimientos próximos y vencidos.

## Verificación

1. Ejecutar `99_verify_schema.sql` y revisar:
   - Las 6 tablas existen.
   - `FK_Movements_Lots_Product` tiene dos columnas (`lot_id`, `product_id`).
   - Las restricciones `CHECK`, `UNIQUE` e índices esperados aparecen.
   - Todas las consultas marcadas “Esperado: 0 filas” devuelven 0 filas.
2. Con la cuenta administradora, dentro de una transacción revertida, probar
   que la base rechaza datos inválidos (código duplicado, stock negativo,
   salida sin área, movimiento con lote de otro producto, saldo incoherente).
3. Cuando exista la cuenta de aplicación, comprobar que puede conectarse con
   `Database.test_connection()` y que **no** puede ejecutar DDL ni modificar
   tablas directamente.
4. Las pruebas unitarias de la capa de datos no sustituyen esta verificación:
   la conexión real solo se afirmará cuando se ejecute con credenciales
   locales válidas.

## Etapas siguientes

- Crear la cuenta administradora y la cuenta de aplicación, y verificar sus
  permisos antes de otorgar accesos.
- Implementar los procedimientos almacenados parametrizados (altas, consultas,
  entradas y salidas) con transacciones y control de concurrencia por
  producto.
- Implementar repositorios, servicios y endpoints respetando
  `main.py → apis → services → repositories`, el contrato camelCase y las
  fechas `YYYY-MM-DD`.
