# Verificación del frontend e integración

**Estado comprobado (1 de noviembre de 2026):** `npm run build` terminó
correctamente y `npm test -- --watch=false` aprobó **140 pruebas en 17 archivos**
en la computadora del equipo, antes de añadir las dos pruebas de concurrencia
de `InventoryService`. Hay que repetirlas tras aplicar esta corrección. En Swagger se comprobaron las 11 rutas del backend,
y Angular mostró el inventario real de SQL Server. Los apartados de abajo
conservan como **historial** algunas verificaciones anteriores hechas en modo demo.
No equivalen por sí solos a una instalación limpia en otra computadora.

## Historial de pruebas del frontend
Verificaciones anteriores del 31 de octubre de 2026.

## Comprobaciones automatizadas

- `npm run build`: producción compilada correctamente, sin advertencias.
- `ng test --watch=false`: **17 archivos y 143 pruebas (registro histórico)**.
- Validaciones de Signal Forms: campos obligatorios, código único, precios, cantidades, fechas y categoría.
- Entradas y salidas: stock por lote, destino obligatorio, bloqueo de vencidos, saldos y conservación de historial.
- Persistencia: recarga de datos y fallo de almacenamiento sin modificar el estado.
- Consultas: límites de 730 días, fechas combinadas, datos actualizados y productos con mayores salidas.
- Respuestas HTTP simuladas: métodos y rutas del adaptador, errores de API y token limitado al servicio propio.
- Recuperación: reintento de formularios conservando sus valores; una consulta fallida tras un registro confirmado no induce a repetir el movimiento.

## Comprobaciones en navegador

Se revisaron escritorio (1440 × 1000), tableta (aproximadamente 710 píxeles de ancho) y móvil (390 × 844). Se comprobó la navegación, el menú móvil y el desplazamiento de tablas dentro de sus contenedores, sin desbordamiento horizontal de la página.

Recorrido real con datos de prueba:

1. Ingreso con las credenciales de demostración.
2. Cantidad decimal rechazada con explicación en el campo.
3. Entrada de 5 tabletas: stock total de 40 a 45.
4. Salida de 41 unidades rechazada para un lote con saldo de 40, aun cuando el producto sumaba 45.
5. Salida válida de 3 unidades: stock de 45 a 42; movimiento consultable con lote y destino en el historial.
6. Consulta de indicadores actualizados y restauración de la muestra pequeña después de verificar.

Este apartado corresponde a pruebas previas del modo local. La integración
real se comprobó posteriormente y se resume al comienzo del documento.

## Ampliación: paginación y búsqueda

Se conservan las 68 pruebas anteriores y se agregan pruebas de paginación, navegación y búsqueda. Verifican páginas sin omisiones ni duplicados, búsqueda en registros de otras páginas, reinicio al filtrar o cambiar tamaño, ajuste al reducir resultados, totales completos, estado vacío y continuidad de registro y desactivación. El historial conserva los enlaces de producto, fechas y movimiento seleccionado, y permite buscar por texto combinado con los filtros.

En una vista de prueba independiente se registraron dos categorías adicionales para comprobar la segunda página. Se verificaron Anterior/Siguiente, números de página, búsqueda desde la segunda página y cambio a 10 registros. La revisión incluyó panel estrecho en escritorio (1024 píxeles) y móvil (390 píxeles), sin desbordamiento horizontal. La muestra del código y los datos del origen habitual de la aplicación se conservan.

## Ampliación: selectores y confirmación de productos

Se agregan 31 pruebas a las 102 anteriores. Los controles compartidos verifican sincronización con Signal Forms, búsqueda sin distinguir tildes, opciones deshabilitadas, navegación por teclado, foco y estado de errores. El calendario comprueba fechas reales, años bisiestos, límites, cambio de mes y año, selección, limpieza y escritura manual. El formulario confirma únicamente el guardado exitoso, conserva el comportamiento de edición y no abre la alerta ante errores.

La revisión en navegador incluyó escritorio (1440 × 1000), pantalla intermedia (1024 × 900) y móvil (390 × 844). Se comprobó la búsqueda de categorías y productos, selección por teclado, mensaje al abandonar una categoría obligatoria vacía, bloqueo de lotes vencidos y fechas futuras de movimientos, filtros de historial con fechas escritas en español y cambio a 20 registros por página. Los paneles se mantienen dentro de la pantalla y no generan desbordamiento horizontal de la página.

En un origen local independiente se registró un producto de ejemplo y se verificó su confirmación con nombre y código, las acciones de la alerta, el foco del teclado dentro de ella y el cierre con Escape. Las pruebas visuales no modificaron los datos del origen habitual de la aplicación.

## Corrección: inicio de sesión y dos usuarios

Se agregan diez pruebas sobre los dos accesos locales: Hans Orellana y Jimmy Ricce. Cubren su identidad, restauración de sesión, rechazo de correos ajenos y del acceso anterior, selección de credenciales desde la pantalla y el mensaje exacto de correo inválido: «Ingresa un correo válido, por ejemplo: example@example.pe».

En navegador se comprobó el inicio y cierre de sesión de ambos usuarios y su nombre en la vista general. La pantalla de acceso se revisó en escritorio y móvil, sin desbordamiento horizontal. El modo demo mantiene un único perfil, Responsable de almacén; posteriormente se conectó el backend real.
