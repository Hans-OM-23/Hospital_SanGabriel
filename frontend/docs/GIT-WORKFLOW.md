# Gestión del proyecto — ramas actuales

El frontend nació en la rama `Hans`. La integración FastAPI/SQL Server y sus
correcciones se prepararon en la rama `Jimmy`, desde la que se abrirá un
**Pull Request** hacia `main` cuando el equipo lo apruebe. El remoto ya está
configurado. Verificar en GitHub Desktop que el commit y el push estén hechos
antes del PR. Las instrucciones históricas de abajo describen la fase anterior
del frontend y **no representan el estado actual del repositorio**.

## Historial del trabajo inicial en el frontend


El frontend completo y actualizado está integrado en la rama **`Hans`**, incluyendo paginación, selectores, calendarios, confirmación de productos y los accesos de Hans Orellana y Jimmy Ricce. Por decisión del usuario, el trabajo posterior continúa en `Hans` y no se crean más ramas salvo petición expresa.

Las ramas locales `codex/*` se utilizaron para separar las funcionalidades durante el desarrollo. Todos sus commits se incorporaron a `Hans` antes de retirar esas ramas auxiliares. El historial se conserva. `main` también se sincronizó con la entrega completa para que ambas ramas incluyan el frontend y sus archivos `.gitignore`; el trabajo continúa en `Hans`.

El panel **Changes** de GitHub Desktop muestra cambios pendientes, no los archivos ya guardados de una rama. Las carpetas generadas por Angular permanecen en el disco al cambiar de rama; `.gitignore` evita incluirlas en los commits. Por ello, comprobar el proyecto en **History** o en el explorador de archivos es distinto de consultar **Changes**.

## Publicar desde GitHub Desktop

1. Seleccionar este repositorio y comprobar que **Current branch** muestre **Hans**.
2. Si aún no existe un repositorio en GitHub, usar **Publish repository** y seleccionar la cuenta, el nombre y la visibilidad deseados. Si ya existe, configurar su URL en **Repository → Repository settings → Remote**.
3. Publicar `Hans` con **Publish branch** o enviar los commits con **Push origin**, según el estado mostrado por GitHub Desktop.

Actualmente no hay un remoto configurado y no se ha realizado una publicación. Se necesita el repositorio de destino para enviar los cambios. No hace falta publicar las antiguas ramas auxiliares.

## Continuar el trabajo

- Hacer commits descriptivos sobre `Hans` y revisar los archivos incluidos antes de enviarlos.
- Usar `ng s` desde `frontend` para abrir la aplicación.
- Ejecutar `npm run build` y `npm test -- --watch=false` para verificar cambios que afecten al código.
- Mantener las exclusiones de `.gitignore`: dependencias, compilaciones, cachés y vistas de prueba permanecen locales.

Cuando se trabaje con revisiones en equipo, un pull request puede partir de `Hans` hacia la rama de integración acordada. Cada integrante debe poder explicar sus cambios; la [guía de sustentación](SUSTENTACION.md) propone el recorrido de un dato y las preguntas de revisión.
