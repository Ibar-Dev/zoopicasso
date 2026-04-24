# Facturación Web — Zoo Picasso

Esta carpeta contiene la aplicación web de facturación para Zoo Picasso (antes generar_para_email).

## Estructura
- web/: Backend FastAPI y frontend (plantillas, estáticos)
- src/: Lógica de negocio, modelos, persistencia
- data/: Archivos de datos y base de datos
- deploy/: Scripts de despliegue y configuración
- logs/: Logs de aplicación
- tests/: Pruebas automáticas

## Despliegue en Render
- El rootDir para Render debe ser facturacion_web
- El startCommand y buildCommand deben apuntar a web/app.py

## Ejecución local

```bash
uv sync
uv run uvicorn web.app:app --host 0.0.0.0 --port 8081 --reload
```

## Migración
- Esta carpeta reemplaza a generar_para_email
- Revisar rutas relativas y variables de entorno si se personalizan
