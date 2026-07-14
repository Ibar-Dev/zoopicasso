# Docker — Desarrollo y Pruebas

Ejecuta el servidor web localmente en un contenedor Docker. Ideal para pruebas de UX/UI sin compatibilidades de entorno.

## Quick Start

### Primera vez (o cuando cambies código)
```bash
docker compose up --build
```

### Siguientes veces (imagen ya construida)
```bash
docker compose up
```

### En segundo plano
```bash
docker compose up -d
```

### Parar
```bash
docker compose down
```

### Ver logs en tiempo real
```bash
docker compose logs -f
```

## Características

- **Python 3.11-slim**: Mismo que Render (producción), evita incompatibilidades locales
- **Solo dependencias web**: Sin `flet`, `escpos`, `libusb-package`, `pyusb`, `pywin32`
- **Volúmenes persistentes**: `./data`, `./facturas`, `./logs` sobreviven reinicios del contenedor
- **Variables de entorno de dev**: `WEB_SESSION_HTTPS_ONLY=false`, `LOG_LEVEL=INFO`
- **Puerto 8000**: Accesible en `http://localhost:8000`

## Acceso a la aplicación

Una vez levantado el contenedor:
- **UI web**: http://localhost:8000
- **API Health**: http://localhost:8000/api/health

## Soluciona

| Problema | Solución |
|---------|---------|
| Python 3.14 local → bug Content-Length | Contenedor usa Python 3.11 |
| Falta de `flet`, `escpos`, `libusb` | `requirements-web.txt` mínimo |
| Datos se pierden entre reinicios | Volúmenes Docker persisten datos |
| Diferencias dev ↔ producción | Mismo Python, mismas deps, mismo CMD |

## Archivos

- `Dockerfile` — Imagen Python 3.11 + dependencias web + código
- `docker-compose.yml` — Servicio, volúmenes, variables de entorno
- `requirements-web.txt` — Dependencias (sin desktop/impresora)
- `.dockerignore` — Excluye `.venv`, tests, backups, etc.

## Debugging

```bash
# Shell interactivo del contenedor
docker compose exec web bash

# Ver estado actual
docker compose ps

# Logs solo del último cambio
docker compose logs --tail=50

# Reconstruir sin caché
docker compose build --no-cache
```

## Notas

- Los datos en `./data`, `./facturas`, `./logs` persisten en el host
- Para cambios en código, usa `docker compose up --build`
- Las credenciales en `.env` se ignorarán; usa las del contenedor en env vars
