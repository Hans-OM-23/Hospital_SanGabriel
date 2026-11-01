# Gestión del proyecto

El frontend completo y actualizado está integrado en la rama **`Hans`**, incluyendo paginación, selectores, calendarios, confirmación de productos y los accesos de Hans Orellana y Jimmy Ricce. Por decisión del usuario, el trabajo posterior continúa en `Hans` y no se crean más ramas salvo petición expresa.

Las ramas locales `codex/*` se utilizaron para separar las funcionalidades durante el desarrollo. Todos sus commits se incorporaron a `Hans` antes de retirar esas ramas auxiliares. El historial se conserva y `main` permanece como la rama inicial del repositorio.

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
