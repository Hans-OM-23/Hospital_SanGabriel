# Hospital San Gabriel

Frontend de inventario hospitalario desarrollado con **Angular 22 y Signal Forms**. Incluye inicio de sesión, productos, categorías, entradas, salidas, historial y consultas. La aplicación está en [`frontend`](frontend/).

```powershell
cd frontend
ng s
```

Abre [http://localhost:4200](http://localhost:4200). Accesos de demostración: `hans.orellana@sgabriel.pe` y `jimmy.ricce@sgabriel.pe`. Contraseña para ambos: `SanGabriel2026!`.

Utiliza tres productos de ejemplo y persistencia local. El consumo HTTP de FastAPI está preparado para la futura integración; esta entrega no incluye backend ni SQL. Alerta de vencimiento: **730 días**. Moneda: soles peruanos.

- [Instalación, arquitectura y recorrido funcional](frontend/README.md)
- [Contrato propuesto para FastAPI](frontend/docs/API-CONTRACT.md)
- [Guía para la sustentación](frontend/docs/SUSTENTACION.md)
- [Gestión y publicación desde Hans](frontend/docs/GIT-WORKFLOW.md)

Verificación desde `frontend`: `npm run build` y `npm test -- --watch=false`.
