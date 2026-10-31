# San Gabriel · Frontend de inventario hospitalario

Aplicación Angular para administrar productos y categorías, registrar entradas y salidas por lote, consultar el historial y revisar indicadores del almacén hospitalario. Incluye inicio de sesión con un perfil: **Responsable de almacén**.

Esta entrega funciona con un ejemplo local pequeño. El adaptador HTTP para la futura API FastAPI está preparado y permanece inactivo. La entrega no incluye servidor, archivos SQL ni una integración comprobada con una base de datos.

## Instalación y ejecución

Requisitos: Node.js 24 y npm. El proyecto utiliza Angular 22.2.x; `package-lock.json` fija las versiones reproducibles de las dependencias.

Desde la carpeta del repositorio:

```powershell
cd frontend
npm ci
npm start
```

Abrir [http://localhost:4200](http://localhost:4200).

| Acceso de demostración | Valor                  |
| ---------------------- | ---------------------- |
| Correo                 | `almacen@sgabriel.pe`  |
| Contraseña             | `SanGabriel2026!`      |
| Perfil                 | Responsable de almacén |

La sesión de ejemplo se conserva en `sessionStorage`. Cerrar sesión elimina esa sesión, mientras que los cambios del inventario permanecen en el navegador.

## Compilación y pruebas

Dentro de `frontend`:

```powershell
npm run build
npm test -- --watch=false
```

La compilación genera los archivos de distribución en `dist/frontend/`. Las pruebas usan Vitest y TestBed de Angular. Cubren formularios, autenticación local, reglas de movimientos, persistencia del ejemplo, filtros e indicadores; su ejecución no demuestra una conexión con FastAPI o SQL Server.

Para trabajar con las pruebas en modo observación:

```powershell
npm test
```

## Modo de demostración

Configuración actual en `src/environments/environment.ts`:

```typescript
export const environment = {
  useMock: true,
  apiUrl: 'http://localhost:8000/api',
  expirationWarningDays: 730,
} as const;
```

`useMock: true` selecciona `DemoInventory`. La aplicación no necesita iniciar ni contactar un backend. Los cambios del inventario se guardan en `localStorage` con la clave `san-gabriel.inventory.v1` y se recuperan al volver a consultar o recargar la aplicación en el mismo navegador y origen.

El ejemplo inicial contiene **3 productos, 4 categorías, 3 lotes, 4 áreas y 4 movimientos**. Incluye un producto próximo a vencer, existencias bajas y un lote vencido para comprobar las alertas. Las fechas se calculan respecto al día en que se genera o restablece el ejemplo; después de guardar cambios, las fechas persistidas se conservan.

Para volver al ejemplo inicial: **Ayuda y guía de uso → Restablecer datos de ejemplo → Sí, restablecer**. Esto reemplaza los cambios locales del inventario. La demo es para uso individual: no ofrece coordinación de operaciones concurrentes entre pestañas ni las garantías de una base de datos.

## Funcionalidades y decisiones

- Productos: registro, consulta, edición, búsqueda por código o nombre, filtros y desactivación conservando el historial.
- Categorías: listado y registro; las opciones de los productos provienen del servicio compartido, por lo que una categoría nueva aparece sin editar listas fijas en las pantallas.
- Movimientos: entradas por compra, donación o devolución; salidas con destino obligatorio y selección manual del lote.
- Trazabilidad: lotes ordenados primero por vencimiento, saldo por lote y saldos anterior/posterior por movimiento. La unidad y el control de vencimiento se conservan cuando existen movimientos, para mantener la interpretación del historial.
- Historial: filtros combinables por producto, tipo, área y fechas; incluye movimientos de productos desactivados.
- Consultas: productos activos, stock igual o inferior al mínimo, próximos a vencer, vencidos, valor referencial, actividad por periodo y mayores salidas.
- Diseño clínico adaptable a computadora, tableta y móvil; importes en soles peruanos y alertas de vencimiento a **730 días**, incluyendo el día límite.

Los indicadores de stock, vencimiento y valor se calculan para productos activos. El valor referencial es la suma de sus existencias por su precio unitario e incluye sus lotes con saldo, incluso si están vencidos. Los indicadores actuales de inventario no cambian por el filtro de periodo; el filtro afecta los movimientos y el ranking de salidas.

## Organización del código

El proyecto se creó con `ng new frontend` usando Angular CLI 22. Los componentes y servicios se generaron mediante `ng generate`; los contratos TypeScript se organizaron en subcarpetas `interface` por funcionalidad.

```text
src/app/
├── auth/         components, service, interface: acceso y sesión
├── products/     components, service, interface: catálogo y ficha
├── categories/   components, service, interface: categorías
├── movements/    components, service, interface: entradas y salidas
├── history/      components: consulta de movimientos
├── dashboard/    components, service, interface: consultas e indicadores
├── layout/       components: menú, cabecera, ayuda y estructura común
├── core/         service, interface: estado, contratos y adaptadores
└── shared/       components: iconos y mensajes de errores
```

Se crean subcarpetas según las necesidades de cada funcionalidad. Los formularios y filtros usan **Signal Forms** (`form`, `FormField`, `required`, `validate` y `submit` donde hay envío). Los servicios de funcionalidades delegan en `InventoryService`, que actualiza un estado compartido basado en señales después de cada operación.

## Recorrido de demostración

Puede ejecutarse después de restablecer el ejemplo. No necesita grandes conjuntos de datos.

| Comprobación              | Acción y resultado esperado                                                                                                                                                                                                |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Acceso                    | Entrar con las credenciales de ejemplo; probar antes una contraseña incorrecta y un correo inválido para ver los mensajes.                                                                                                 |
| RF01 · Productos          | Registrar `MED-004` con descripción, categoría, unidad, precio positivo y mínimo entero. Aparece con stock cero; editar el nombre y buscarlo por código y nombre.                                                          |
| RF01 · Validación         | Intentar el código `med-001`: debe advertir el duplicado. Probar precio vacío, cero y negativo; mínimo decimal; campos obligatorios vacíos y vencimiento requerido. No debe guardarse un formulario inválido.              |
| RF02 · Categorías         | Registrar una categoría nueva y comprobar que aparece en el formulario de producto. Intentar el mismo nombre con cambios de mayúsculas o espacios.                                                                         |
| RF03 · Entradas           | Registrar 3 unidades de `MED-004`, motivo Compra y lote `DEM-001`. Si tiene vencimiento, indicar una fecha válida. El saldo aumenta y la confirmación enlaza el movimiento. Repetir con Donación o Devolución si se desea. |
| RF04 · Salidas            | Seleccionar manualmente `DEM-001`, registrar 1 unidad hacia Emergencia y comprobar saldo final 2. Probar cantidad vacía, 0, negativa, decimal y superior al saldo del lote: deben rechazarse.                              |
| RF04 · Vencidos y destino | Intentar seleccionar el lote vencido de Alcohol al 70 % y consultar la explicación del bloqueo. Una salida sin área válida no puede registrarse.                                                                           |
| RF05 · Historial          | Filtrar por producto, tipo, área y rango de fechas. Consultar lote, motivo, cantidad, fecha, destino y saldos. Probar un rango invertido y corregirlo.                                                                     |
| RF01/RF05 · Desactivación | Desactivar un producto con movimientos, confirmar la acción y verlo con el filtro Inactivos. Su historial debe seguir disponible. Se puede reactivar.                                                                      |
| RF06 · Indicadores        | Revisar activos, mínimos, próximos a vencer, vencidos y valor; cambiar las fechas para observar actividad y mayores salidas. Registrar otro movimiento y comprobar el cambio al consultar y actualizar.                    |
| Persistencia local        | Recargar el navegador y confirmar que continúan los productos y movimientos registrados. Usar la ayuda para restablecer el ejemplo cuando termine la prueba.                                                               |
| Adaptación visual         | Revisar el menú móvil, los formularios y el desplazamiento horizontal de las tablas en una pantalla pequeña.                                                                                                               |

En la demo, stock e historial se guardan juntos como un único estado local. La transacción real, el control de concurrencia, los permisos y la persistencia en SQL Server pertenecen a la futura implementación del backend.

## Preparación para FastAPI

`HttpInventory` define las solicitudes HTTP y `AuthService` prepara el inicio de sesión remoto. La configuración de Angular selecciona el adaptador mediante `InventoryGateway`. El interceptor agrega el token Bearer únicamente a la URL de API configurada.

Cuando exista el backend, deberá acordarse y comprobarse el [contrato de API](docs/API-CONTRACT.md), configurar `apiUrl` y cambiar `useMock` a `false`. Será necesario reiniciar el servidor de desarrollo para aplicar la configuración. La presencia de ese adaptador no sustituye las pruebas de integración con la API real.

La [guía de sustentación](docs/SUSTENTACION.md) explica las decisiones y cómo seguir el recorrido de un dato por el código. La documentación de gestión Git se encuentra en el repositorio principal.
