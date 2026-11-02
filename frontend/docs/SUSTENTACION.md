# Guía de sustentación — Hospital San Gabriel

## Qué se entrega

Sistema integrado Angular 22 + FastAPI + SQL Server para el inventario del
Hospital San Gabriel, con acceso, productos, categorías, entradas, salidas,
historial e indicadores. En la evaluación usar `useMock: false` y el SQL unificado
de `backend/db/INSTALAR_HOSPITAL_SAN_GABRIEL.sql`.

El adaptador `HttpInventory` utiliza las rutas FastAPI del [contrato](API-CONTRACT.md).
El backend separa APIs, servicios, repositorios y esquemas; los repositorios
invocan procedimientos almacenados SQL. En la exposición hay que confirmar la
instalación local de SQL Server y el login con la cuenta del hospital.

## Decisiones que conviene justificar

| Decisión                                          | Explicación                                                                                                                                                           |
| ------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Organización por funcionalidades                  | Productos, categorías, movimientos, acceso y consultas reúnen sus componentes y, cuando se necesitan, servicios e interfaces. Facilita ubicar y explicar cada cambio. |
| Componentes standalone y rutas con carga diferida | Cada pantalla declara sus dependencias y Angular carga su componente cuando se navega a ella.                                                                         |
| Layout compartido                                 | Menú, cabecera, usuario, ayuda, actualización y mensajes generales se mantienen en `Shell`. Evita repetir la estructura en cada pantalla.                             |
| Signal Forms                                      | El modelo es una señal; las reglas declaran la validación y `FormField` enlaza cada control. Estado, errores y envío se consultan desde el árbol del formulario.      |
| Selectores compartidos                            | `SelectControl` y `DatePicker` implementan `FormValueControl<string>`: reutilizan presentación y teclado sin sustituir las validaciones de Signal Forms.              |
| Angular CDK                                       | Overlay posiciona los paneles fuera de contenedores que podrían recortarlos; A11y controla y restaura el foco en la confirmación de guardado.                         |
| Servicios de funcionalidades                      | Los componentes resuelven la interacción y delegan las operaciones. Los servicios permiten compartir el comportamiento sin duplicar el acceso a datos.                |
| `InventoryGateway`                                | Define el límite de acceso a datos. La configuración inyecta `HttpInventory` en modo real (`useMock: false`); `DemoInventory` queda como alternativa de pruebas.                               |
| Estado compartido                                 | `InventoryService` mantiene un snapshot con productos, categorías, lotes, áreas y movimientos. Las señales calculadas actualizan las vistas relacionadas.             |
| Un perfil de acceso                               | El requisito acordado es Responsable de almacén. Los guardas evitan acceder a las pantallas sin una sesión; los permisos definitivos deben validarse en el backend.   |
| Datos pequeños                                    | Tres productos bastan para mostrar inventario normal, stock bajo, vencimiento próximo, vencido y trazabilidad.                                                        |
| Moneda y vencimiento                              | Se presentan importes en soles peruanos. La ventana de alerta es de 730 días, según la última decisión del proyecto.                                                  |
| Lote manual con orden por vencimiento             | El usuario conserva la decisión del lote. El orden ayuda a elegir primero los vencimientos cercanos y los vencidos se bloquean.                                       |
| Desactivación                                     | Los productos conservan sus movimientos; no se ofrece borrado físico desde la interfaz.                                                                               |

## Cómo seguir el código

1. `app.routes.ts`: identificar `/login`, el layout protegido y las pantallas hijas.
2. `app.config.ts`: mostrar el proveedor de `InventoryGateway`, el `HttpClient`, el interceptor y el formato regional `es-PE`.
3. `auth/service/auth.ts`: explicar el acceso local, la sesión y la rama HTTP preparada.
4. `layout/components/shell`: mostrar estructura común, carga inicial, actualización y restablecimiento de la demo.
5. `products/components/product-form`: seguir un formulario Signal Forms desde su modelo hasta el guardado.
6. `movements/components/movement-form`: explicar producto, lote, saldo, cantidad y destino; después seguir su servicio.
7. `core/service/inventory.service.ts`: mostrar cómo la mutación va al gateway y luego se refrescan todos los recursos.
8. `core/service/demo-inventory.ts`: explicar la validación local y la persistencia del snapshot completo.
9. `core/service/http-inventory.ts`: mostrar las rutas implementadas y la lectura de cinco recursos en paralelo.
10. `history` y `dashboard`: explicar filtros, consultas e indicadores derivados del estado compartido.

## Explicar un formulario con Signal Forms

Ejemplo: `ProductForm`.

1. `model = signal(...)` contiene los valores de la ficha. Un precio vacío se representa inicialmente con `NaN`, que la regla `required` rechaza.
2. `form(model, schema)` construye el árbol del formulario y declara reglas: campos obligatorios, código único, precio mayor que cero, mínimo entero y fecha condicional.
3. `[formField]="productForm.code"` enlaza el input al campo. Los controles personalizados se enlazan igual: su `value` es un modelo y `FormValueControl<string>` comunica estado deshabilitado, requerido, inválido e interacción. No se usa `ngModel` ni un `FormGroup` tradicional.
4. `FieldErrors` recibe el estado del campo y muestra mensajes cuando está tocado e inválido. Las reglas están junto al modelo del formulario y no dispersas en el HTML.
5. El envío usa `submit(...)`. Angular marca los campos necesarios, impide ejecutar la acción si los datos son inválidos y expone `submitting()` para evitar envíos simultáneos del mismo formulario.
6. Antes de guardar se normalizan código y textos. El servicio conserva la responsabilidad del acceso a datos.
7. Si el servicio devuelve un código duplicado, el error se devuelve a `submit` con `fieldTree: productForm.code`; así aparece junto al input correspondiente.
8. Solo después de que el servicio resuelve el guardado se abre `SuccessAlert` con una copia del producto confirmado. Una ficha nueva queda lista para otro registro; al editar se conservan sus datos. Los errores y los envíos inválidos no abren la confirmación.

Una demostración útil es escribir `med-001`, un precio cero y un mínimo decimal. Corregir cada campo permite comprobar que los errores se actualizan con el modelo y orientan al usuario.

## Cómo demostrar los controles compartidos

En `shared/components/select-control`, mostrar cómo las opciones llegan desde la pantalla y sus servicios. Buscar un producto o categoría, recorrer las opciones con flechas y confirmar con Enter. Las opciones deshabilitadas, como un lote vencido para salida, siguen visibles con su motivo y no pueden seleccionarse. Escape cierra y devuelve el foco; Tab permite continuar el formulario.

En `shared/components/date-picker`, elegir una fecha en el calendario en español o escribirla como `dd/mm/aaaa`. Cambiar directamente mes y año; probar **Hoy**, **Limpiar** y el teclado. El control muestra fechas de forma local y entrega `aaaa-mm-dd` al modelo. Los límites mínimo/máximo configurados restringen la selección; las validaciones del formulario explican los datos inválidos.

Explicar que los paneles usan CDK Overlay para evitar que las tarjetas o tablas los recorten y para ajustar su posición al espacio disponible. La confirmación `shared/components/success-alert` usa CDK A11y: atrapa el foco, admite X/Escape, no desaparece automáticamente y restaura el foco y el desplazamiento al cerrarse. Probar **Ver productos**, **Seguir registrando** y **Entendido** tras una edición. Si la consulta posterior al guardado falla, el aviso general pide actualizar sin repetir el registro; confirmar la escritura y refrescar la información son resultados distintos.

## Recorrido de una entrada o salida

```text
Usuario completa formulario
  → Signal Forms valida
  → MovementsService delega
  → InventoryService registra mediante InventoryGateway
  → DemoInventory guarda el ejemplo local
    [HttpInventory solicita POST /movements con JWT]
  → InventoryService vuelve a cargar el estado
  → señales calculadas actualizan saldo, historial e indicadores
  → pantalla confirma y enlaza el movimiento
```

Para una salida, explicar la diferencia entre dos saldos:

- El saldo del lote seleccionado limita la cantidad que puede salir.
- `stockBefore` y `stockAfter` del historial muestran el saldo total del producto antes y después del movimiento.

El producto debe estar activo, la cantidad debe ser un entero positivo, el lote debe pertenecer al producto, no estar vencido y tener existencias suficientes, y el destino debe ser un área válida. El orden por vencimiento no selecciona automáticamente un lote.

En la demo, saldo e historial se incorporan a un snapshot y se guardan juntos. En la versión integrada, la transacción atómica y el control de concurrencia pertenecen a FastAPI y SQL Server; el navegador no puede garantizarlos.

## Mapa de requisitos funcionales

| Requisito         | Pantalla y archivos principales                                                    | Evidencia que se puede mostrar                                                                |
| ----------------- | ---------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| RF01 · Productos  | `products/components/product-list`, `product-form`, `products/service/products.ts` | Ficha, validación, búsqueda, filtros, lotes, edición, desactivación y reactivación.           |
| RF02 · Categorías | `categories/components/category-list`, `categories/service/categories.ts`          | Crear categoría y verla disponible inmediatamente al registrar un producto.                   |
| RF03 · Entradas   | `movements/components/movement-form`, `movements/service/movements.ts`             | Compra/donación/devolución, lote, vencimiento, nuevo saldo y enlace al historial.             |
| RF04 · Salidas    | La misma pantalla en modo salida                                                   | Área obligatoria, lote manual, saldo disponible, bloqueo por vencimiento y cantidad excesiva. |
| RF05 · Historial  | `history/components/history`                                                       | Filtros combinados, rango de fechas, producto, lote, motivo, destino y saldos.                |
| RF06 · Consultas  | `dashboard/components/dashboard`, `dashboard/service/dashboard.ts`                 | Métricas actuales, vencidos, actividad por fechas y ranking de salidas.                       |
| Inicio de sesión  | `auth/components/login`, `auth/service/auth.ts`, `auth-guard.ts`                   | Acceso correcto/incorrecto, rutas protegidas y cierre de sesión.                              |

## Mapa de las doce reglas

| N.º | Cómo se demuestra                                                                                                     | Límite de esta entrega                                                                |
| --- | --------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| 1   | Código único normalizado en formulario y rechazo local por duplicado; preparado el error del servicio junto a `code`. | La restricción de unicidad en API/BD se implementará después.                         |
| 2   | Precio vacío, cero o negativo mantiene inválida la ficha.                                                             | El backend también deberá validar.                                                    |
| 3   | Entradas y salidas rechazan cantidades vacías, cero, negativas y decimales.                                           | Se repite validación en la demo; deberá existir en la API.                            |
| 4   | Se muestra saldo por lote y se bloquea cantidad superior a ese saldo.                                                 | La concurrencia real debe resolverse en la transacción del servidor.                  |
| 5   | El registro válido confirma y enlaza su movimiento con saldos.                                                        | La demo genera el historial local.                                                    |
| 6   | El ejemplo guarda stock e historial juntos e intenta refrescar; un fallo de consulta no borra el éxito ya confirmado. | El procedimiento `usp_RegistrarMovimiento` usa transacción SQL; el rollback ante fallos debe demostrarse por separado.                                     |
| 7   | Se desactiva el producto; su historial sigue consultable.                                                             | El servidor debe conservar la misma política.                                         |
| 8   | Mensajes junto a campos y envío inválido bloqueado.                                                                   | La validación del cliente es orientativa, no una barrera de seguridad.                |
| 9   | Lote vencido deshabilitado para salida y explicación visible.                                                         | La API deberá comprobar fecha y vencimiento nuevamente.                               |
| 10  | Producto, lote, vencimiento y saldo visibles en las pantallas pertinentes.                                            | La integridad de relaciones deberá protegerse en la BD.                               |
| 11  | La salida exige un área del catálogo disponible.                                                                      | El servidor debe validar referencia y autorización.                                   |
| 12  | Guardar y actualizar vuelve a leer el origen configurado; indicadores derivan del estado recibido.                    | Actualmente se consulta FastAPI/SQL Server con `useMock: false`. |

## Cómo explicar las consultas

- Activos: cantidad de productos con `active: true`.
- Stock bajo: productos activos cuya suma de lotes es menor o igual que `minStock`.
- Próximos a vencer: productos activos con al menos un lote con saldo cuyo vencimiento está entre hoy y hoy + 730 días, ambos incluidos.
- Vencidos: productos activos con al menos un lote con saldo que venció antes de hoy. Un producto puede aparecer en ambos grupos si tiene distintos lotes.
- Valor referencial: suma del saldo de cada producto activo multiplicado por su precio unitario. La pantalla aclara este alcance; incluye existencias vencidas mientras tengan saldo.
- Periodo: filtra movimientos entre las fechas seleccionadas, incluyéndolas. El rango no altera las métricas del inventario actual.
- Mayores salidas: suma las cantidades de salida por producto dentro del periodo y presenta la unidad propia de cada producto.

## Pruebas y exposición

Ejecutar `npm run build` y `npm test -- --watch=false` dentro de `frontend`. Explicar por qué las pruebas revisan resultados y reglas: no permitir una salida mayor que el lote, no modificar el estado si falla la persistencia, guardar historial con saldos, rechazar duplicados y detectar el límite de 730 días.

Para la exposición puede seguirse el recorrido manual del [README](../README.md): iniciar sesión, crear una categoría y producto, registrar una entrada, intentar salidas inválidas, registrar una salida válida, revisar historial, desactivar el producto y volver a consultar los indicadores. Recargar permite demostrar persistencia local.

Para sustentar la integración se pueden mostrar las respuestas reales de FastAPI, el stock y el historial después de una entrada y salida, junto con la ejecución de los scripts SQL. Las pruebas unitarias no reemplazan estas comprobaciones; la instalación limpia en el laboratorio todavía debe demostrarse.

## Preguntas que cada integrante debe poder responder

1. ¿Dónde está el modelo de un formulario, dónde se declaran sus reglas y cómo llega el error a un campo?
2. ¿Qué hace el componente, qué hace su servicio y qué concentra `InventoryService`?
3. ¿Cómo se cambia el origen de datos y por qué las pantallas no contienen llamadas HTTP directas?
4. ¿Por qué una salida se limita por lote y dónde se calcula el saldo total del producto?
5. ¿Cómo se mantienen disponibles los movimientos de un producto desactivado?
6. ¿Qué cambia al registrar una categoría y por qué aparece en otros formularios?
7. ¿Qué significa el umbral de 730 días y qué ocurre con un lote que vence hoy?
8. ¿Qué garantías demuestra la demo y cuáles deben implementar FastAPI y SQL Server?
9. ¿Qué sucede si el servidor confirma un movimiento y después falla el refresco? ¿Cómo ayudaría la idempotencia?
10. ¿Por qué cinco GET paralelos requieren una estrategia de coherencia en el backend?

Preparar las respuestas recorriendo los archivos y ejecutando una operación concreta permite explicar las decisiones con evidencia del código.

## Cómo explicar la paginación

Primero se obtiene el conjunto completo que coincide con la búsqueda y los filtros. `PaginationState` calcula cuántas páginas existen y entrega solo el tramo de registros de la página elegida. Los conteos y los indicadores se calculan antes de recortar la lista.

`Pagination` muestra rango, tamaño y botones; recibe valores del listado y emite la página o el tamaño seleccionado. Cada listado conserva una instancia independiente del estado. Al cambiar la búsqueda o el tamaño se vuelve a la primera página; si se reducen los datos, se ajusta la página al nuevo límite. La paginación actual utiliza datos cargados en el frontend y deja la integración con paginación de servidor para una fase futura.
