# Verificación de esta entrega

Verificado el 31 de octubre de 2026.

## Comprobaciones automatizadas

- `npm run build`: producción compilada correctamente, sin advertencias.
- `npm test -- --watch=false`: **12 archivos y 68 pruebas aprobadas**.
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

La integración con un servidor FastAPI y una base SQL Server queda pendiente de la futura fase de backend. Las respuestas HTTP de las pruebas usan el entorno de pruebas de Angular; no contactan una API real.
