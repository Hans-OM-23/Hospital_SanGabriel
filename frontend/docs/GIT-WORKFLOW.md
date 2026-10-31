# Gestión del proyecto

El trabajo local se integra en `codex/frontend-inventario`. Las pruebas se mantienen en `codex/frontend-pruebas` y la documentación en `codex/frontend-documentacion`, con commits descriptivos e integración local mediante merges. La rama original `Hans` se conserva. El repositorio no tiene un remoto configurado; por ello no se ha publicado ni abierto un pull request externo.

La ampliación de paginación y búsqueda se desarrolla en `codex/paginacion-listados`, con commits separados para el componente compartido, los listados y la documentación. La implementación anterior queda disponible en `codex/frontend-inventario`.

La mejora de selectores y confirmaciones se desarrolla en `codex/selectores-alertas`, a partir de la ampliación anterior. Se separan los controles compartidos con sus pruebas, la integración en las pantallas y la documentación.

La corrección del mensaje del correo y los dos usuarios de demostración se desarrolla en `codex/usuarios-inicio-sesion`, conservando el único perfil de acceso y la integración anterior.

## Flujo para las siguientes funcionalidades

1. Partir de la rama de integración actualizada y crear una rama con un nombre descriptivo, por ejemplo `codex/productos` o `codex/movimientos`.
2. Hacer commits pequeños que expliquen el resultado: `feat(productos): validar código único` o `fix(movimientos): bloquear lotes vencidos`.
3. Ejecutar `npm run build` y `npm test -- --watch=false` desde `frontend`.
4. Publicar la rama en el remoto del equipo y abrir un pull request hacia su rama de integración. Utilizar la plantilla del repositorio, describir el comportamiento y añadir la evidencia de verificación.
5. Revisar el cambio, resolver observaciones e integrar. Conservar el historial; no incluir `node_modules`, `.angular`, `dist` ni datos de ejecución.

Configurar el remoto exige conocer la URL real del repositorio del equipo. No se ha inventado una URL ni se han enviado los cambios a un servicio externo.

## Pull request preparado

Título: `feat: crear frontend del inventario hospitalario San Gabriel`

Descripción sugerida:

> Implementa el frontend Angular 22 con Signal Forms para acceso, productos, categorías, entradas y salidas por lote, historial y consultas. Una muestra de tres productos permite demostrar validaciones, persistencia local y actualización de existencias e indicadores. Incluye adaptador HTTP inactivo y contrato propuesto para la futura API FastAPI.
>
> Verificado con compilación de producción, pruebas automatizadas de reglas de negocio y formularios, y revisión visual en escritorio, tableta y móvil. La integración con FastAPI y SQL Server corresponde a una fase posterior.

Cada integrante debe poder explicar los archivos que cambia. La [guía de sustentación](SUSTENTACION.md) propone el recorrido de un dato y las preguntas de revisión.
