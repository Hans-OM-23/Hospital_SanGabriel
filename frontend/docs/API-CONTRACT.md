# Contrato propuesto para la futura API FastAPI

Este documento describe las solicitudes que ya prepara el frontend. **El backend no está implementado en esta entrega y el adaptador HTTP está inactivo con `useMock: true`.** Las rutas, autorización y garantías de persistencia deben acordarse y probarse al desarrollar FastAPI.

## Convenciones

- Base configurada: `http://localhost:8000/api` en `src/environments/environment.ts`.
- Cuerpos y respuestas JSON con nombres **camelCase**, tal como están definidos en las interfaces TypeScript. Si el backend usa nombres internos diferentes, deberá aplicar los alias correspondientes.
- Identificadores opacos de tipo `string`.
- Fechas de calendario en formato `YYYY-MM-DD`, sin conversión a UTC ni hora.
- Cantidades y mínimos enteros; precios numéricos mayores que cero. Moneda de presentación: PEN.
- Todas las rutas de inventario requerirán autorización del perfil Responsable de almacén. El frontend agrega `Authorization: Bearer <accessToken>` a solicitudes dirigidas a la API configurada.
- La API debe validar los datos, incluso cuando ya los haya validado el formulario.
- `GET /movements` devuelve el orden de registro ascendente. La interfaz muestra fecha descendente y, para empates del mismo día, invierte el orden de registro. Si cambia este contrato, conviene agregar una marca de creación o una secuencia para desempatar de forma explícita.

## Endpoints preparados

| Método | Ruta relativa           | Cuerpo                         | Respuesta esperada                                |
| ------ | ----------------------- | ------------------------------ | ------------------------------------------------- |
| POST   | `/auth/login`           | `LoginCredentials`             | `AuthResponse`                                    |
| GET    | `/products`             | —                              | `Product[]`                                       |
| POST   | `/products`             | `ProductInput`                 | `Product` creado                                  |
| PUT    | `/products/{id}`        | `ProductInput` completo        | `Product` actualizado                             |
| PATCH  | `/products/{id}/status` | `{ "active": false }` o `true` | Cualquier respuesta de éxito; el cuerpo se ignora |
| GET    | `/categories`           | —                              | `Category[]`                                      |
| POST   | `/categories`           | `CategoryInput`                | `Category` creada                                 |
| GET    | `/lots`                 | —                              | `Lot[]`                                           |
| GET    | `/areas`                | —                              | `HospitalArea[]`                                  |
| GET    | `/movements`            | —                              | `Movement[]`                                      |
| POST   | `/movements`            | `MovementInput`                | `Movement` confirmado                             |

El frontend acepta respuestas HTTP exitosas apropiadas, por ejemplo 200 para lecturas y actualizaciones, 201 para creación y 204 para el cambio de estado. No existen solicitudes de borrado físico, creación de lotes independiente, alta de usuarios ni cierre de sesión remoto. El lote se crea o actualiza como parte de una entrada válida.

Las consultas y filtros actuales se resuelven en el frontend a partir del estado cargado. Las rutas GET preparadas no envían parámetros de paginación, filtros ni un endpoint independiente de indicadores. Al trabajar con inventarios grandes deberá ampliarse el contrato y el adaptador para consultar y paginar desde el servidor.

Los listados de productos, categorías e historial paginan localmente con tamaños 5/10/20 después de filtrar el conjunto completo. Cambiar página no realiza solicitudes ni modifica existencias. En el historial, `busqueda` es un parámetro de navegación del frontend y se combina con los demás filtros; no es todavía un parámetro enviado a FastAPI.

## Autenticación

Solicitud `POST /auth/login`:

```json
{
  "email": "almacen@sgabriel.pe",
  "password": "contraseña"
}
```

Respuesta:

```json
{
  "accessToken": "token-emitido-por-el-backend",
  "user": {
    "id": "user-1",
    "name": "María Torres",
    "email": "almacen@sgabriel.pe",
    "role": "Responsable de almacén"
  }
}
```

El rol admite exactamente ese valor en la interfaz actual. `AuthService` valida la estructura, guarda la sesión en `sessionStorage` y mantiene el token en memoria. Un 401 durante el inicio de sesión se presenta como credenciales incorrectas. Otros errores del inicio de sesión se presentan como fallo al contactar el servicio. No se han implementado renovación ni revocación remota del token: su ciclo de vida debe definirse antes de integrar la autenticación real.

La cuenta y el token de demostración son exclusivos del modo local. El backend deberá administrar sus propias cuentas, contraseñas y permisos.

## Modelos de inventario

### Product y ProductInput

```typescript
interface Product {
  id: string;
  code: string;
  name: string;
  description: string;
  categoryId: string;
  unit: string;
  unitPrice: number;
  minStock: number;
  tracksExpiration: boolean;
  expirationDate: string | null;
  active: boolean;
}
type ProductInput = Omit<Product, 'id' | 'active'>;
```

`code` se normaliza en mayúsculas y sin espacios exteriores. Su unicidad debe garantizarse en la API y en la base de datos, también para productos inactivos. `categoryId` debe identificar una categoría disponible. `expirationDate` es una fecha de referencia de la ficha; el vencimiento usado en los movimientos corresponde al lote. Si `tracksExpiration` es `false`, la ficha envía `expirationDate: null`. Registrar un producto no crea existencias iniciales.

La demo impide cambiar `tracksExpiration` cuando existen movimientos para mantener consistente la trazabilidad. La política definitiva para cambios de ficha con movimientos deberá conservar la información histórica.

### Categorías, lotes y áreas

```typescript
interface Category {
  id: string;
  name: string;
  description: string;
  active: boolean;
}
type CategoryInput = Pick<Category, 'name' | 'description'>;

interface Lot {
  id: string;
  productId: string;
  number: string;
  expirationDate: string | null;
  stock: number;
}

interface HospitalArea {
  id: string;
  name: string;
}
```

La API debe devolver categorías y áreas disponibles, y los productos y lotes necesarios para interpretar el historial, incluidos productos inactivos. Se propone unicidad del nombre de categoría ignorando mayúsculas y espacios exteriores. El número de lote identifica un lote dentro de un producto; reutilizar ese número con otro vencimiento debe rechazarse. La selección del lote es manual y la interfaz ordena primero los vencimientos más cercanos, dejando al final los lotes sin vencimiento.

### Registro de movimientos

```typescript
interface MovementInput {
  type: 'entry' | 'exit';
  productId: string;
  quantity: number;
  date: string;
  reason: string;
  lotId?: string;
  lotNumber?: string;
  expirationDate?: string | null;
  areaId?: string | null;
}

interface Movement {
  id: string;
  type: 'entry' | 'exit';
  productId: string;
  quantity: number;
  date: string;
  reason: string;
  stockBefore: number;
  stockAfter: number;
  lotId: string;
  lotNumber: string;
  expirationDate: string | null;
  areaId: string | null;
}
```

Ejemplo de entrada:

```json
{
  "type": "entry",
  "productId": "p-1",
  "quantity": 3,
  "date": "2026-10-31",
  "reason": "Compra",
  "lotNumber": "PAR-027",
  "expirationDate": "2028-10-31"
}
```

Una entrada exige número de lote y motivo Compra, Donación o Devolución. Si el producto controla vencimiento, debe indicar una fecha válida que no sea anterior al ingreso. La demo también impide registrar movimientos con fecha futura.

Ejemplo de salida:

```json
{
  "type": "exit",
  "productId": "p-1",
  "quantity": 1,
  "date": "2026-10-31",
  "reason": "Reposición de insumos",
  "lotId": "l-1",
  "areaId": "emergencia"
}
```

Una salida exige producto activo, cantidad entera positiva, lote del producto y área válida. El servidor debe verificar el saldo real del lote y bloquear lotes vencidos tanto respecto al día actual como respecto a la fecha del movimiento. Un lote que vence hoy no se considera vencido por la interfaz actual.

`stockBefore` y `stockAfter` son los saldos totales del **producto** antes y después del movimiento, considerando todos sus lotes. `Lot.stock` informa el saldo individual del lote seleccionado. La API determina estos saldos; el cliente no los envía.

## Respuestas de error

El normalizador `explainError` admite las formas siguientes en respuestas de error de inventario:

```json
{ "detail": "No se pudo completar la operación." }
```

```json
{
  "detail": {
    "field": "code",
    "message": "El código del producto ya existe."
  }
}
```

```json
{
  "detail": [
    {
      "loc": ["body", "quantity"],
      "msg": "La cantidad debe ser un entero mayor que cero.",
      "type": "value_error"
    }
  ]
}
```

`field` y el último elemento de `loc` deben corresponder a nombres camelCase del modelo. La interfaz muestra el error de código duplicado junto a `code`, errores de nombre de categoría junto a `name` y errores de movimientos junto al campo cuando existe su correspondencia; los demás se presentan en un aviso del formulario. El inicio de sesión usa mensajes propios, según se explicó anteriormente.

Se proponen 401 para ausencia o invalidez de autenticación, 403 para permisos insuficientes, 404 para recursos inexistentes, 409 para conflictos como códigos duplicados o saldo cambiado y 422 para datos inválidos. Son decisiones del contrato futuro; el adaptador actual no implementa por sí mismo esas garantías ni una recuperación automática de sesión ante un 401 de inventario.

## Consistencia, transacciones y refresco

`HttpInventory.load()` ejecuta en paralelo cinco GET: productos, categorías, lotes, áreas y movimientos. `InventoryService.refresh()` reemplaza el estado visible cuando las cinco lecturas terminan correctamente. Si alguna falla, conserva el último estado válido y muestra un error.

Estas solicitudes paralelas no constituyen una transacción de lectura. El backend debe asegurar que sus respuestas describan un estado coherente o acordar una revisión común de datos. Una evolución recomendable es una lectura consolidada con versión/snapshot o lecturas ligadas a la misma revisión, adaptando el frontend cuando se decida.

Después de guardar un producto, categoría, estado o movimiento, `InventoryService` vuelve a cargar los datos. Los listados e indicadores se derivan del nuevo estado. La confirmación exige que la mutación haya respondido correctamente. Si falla la lectura posterior, se mantiene esa confirmación y un aviso distingue el fallo de actualización: el usuario debe actualizar la consulta sin repetir el registro. Si se pierde la respuesta del POST, el resultado es incierto y la futura API deberá resolverlo mediante idempotencia y consulta de la operación.

La futura operación `POST /movements` debe garantizar en una **misma transacción de SQL Server**:

1. Validar usuario, producto, lote, vencimiento, cantidad y destino.
2. Comprobar y modificar el saldo con control de concurrencia, evitando stock negativo.
3. Insertar el movimiento con sus saldos y referencias de trazabilidad.
4. Confirmar ambos cambios juntos o revertirlos por completo.

La prohibición de borrar productos con movimientos y las restricciones de unicidad deben sostenerse en el servidor y la base de datos. Para conservar la interpretación del historial, una ficha con movimientos no cambia su unidad ni su control de vencimiento; una conversión de unidades requeriría otro flujo acordado. Las validaciones y los guardas de rutas del frontend sirven para orientar al usuario y no sustituyen la autorización del servidor.

Conviene acordar **idempotencia de las mutaciones**, especialmente de los movimientos. Un POST podría confirmarse en el servidor y fallar después el refresco o la respuesta de red. Antes de permitir un reintento automático o manual que duplique existencias, se recomienda una clave de idempotencia y una forma de consultar el resultado de la operación. El frontend actual no envía esa clave ni realiza reintentos automáticos.

## Comprobaciones al integrar

- Crear y editar un producto real, volver a consultar y verificar que los cambios provienen de la API.
- Registrar categoría y comprobar su disponibilidad sin recargar listas fijas.
- Verificar un código duplicado y los errores 422 junto a los campos.
- Registrar entrada y salida; comprobar saldos y el mismo movimiento en historial tras una consulta nueva.
- Enviar salidas concurrentes sobre el mismo lote y demostrar que no se produce stock negativo.
- Simular una operación rechazada, una respuesta perdida y un fallo de refresco; comprobar que no hay duplicados ni confirmaciones falsas.
- Probar autorización, sesión inválida y perfil permitido en el servidor.
- Comprobar el rango de 730 días, lotes vencidos y consistencia de los cinco recursos leídos.

Estas son pruebas pendientes de la fase de integración; las pruebas de la demo no deben presentarse como evidencia de su ejecución contra una API o SQL Server.
