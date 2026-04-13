# Generador de Facturas - Zoo Picasso

Aplicacion para generar facturas en formato `.xlsx` en dos modos:

- Escritorio con Flet (`main.py`)
- Web con FastAPI (`web/app.py`)

## Funcionalidades actuales

- Login de acceso.
- Creacion de facturas por lineas (concepto, cantidad, precio unitario).
- Guardado de archivo Calc/Excel (`.xlsx`) con selector de ruta.
- Limpieza automatica del formulario tras guardado correcto.
- Acumulado diario de importes en la sesion.
- Contador de facturas del dia en la sesion.
- Ajuste manual del acumulado (resta), por Enter o boton.
- Confirmaciones para evitar cierres/salidas por error.

## Estructura principal

- `main.py`: app de escritorio (Flet).
- `web/app.py`: backend web (FastAPI).
- `web/templates/index.html`: interfaz web.
- `src/`: logica de modelo, contador, writer y settings.
- `deploy/install_vps.sh`: instalacion y configuracion en VPS.

## Requisitos

- Python 3.11+ (el proyecto corre con entornos mas nuevos tambien).
- `uv` para gestionar dependencias.

## Datos del emisor (ticket web)

Para evitar hardcodear datos del negocio, el modo web usa variables de entorno
con estos valores por defecto:

- `EMISOR_NIF` (default: `Y3806548Q`)
- `EMISOR_NOMBRE` (default: `Gisselle Marin Tabares`)
- `EMISOR_DIRECCION` (default: `Calle de Pablo Picasso 59`)
- `EMISOR_TELEFONO` (default: `642 342 110`)
- `EMISOR_EMAIL` (default: `zoopicasso07@gmail.com`)
- `EMISOR_NEGOCIO` (default: `Zoo Picasso`)

Ejemplo en `.env`:

```bash
EMISOR_NIF=Y3806548Q
EMISOR_NOMBRE=Gisselle Marin Tabares
EMISOR_DIRECCION=Calle de Pablo Picasso 59
EMISOR_TELEFONO=642 342 110
EMISOR_EMAIL=zoopicasso07@gmail.com
EMISOR_NEGOCIO=Zoo Picasso
```

## Ejecutar en local

Desde la carpeta del proyecto:

```bash
uv sync
uv run main.py
```

## Ejecutar modo web

```bash
uv sync
uv run uvicorn web.app:app --host 0.0.0.0 --port 8081 --reload
```

## Simulacro de deploy (obligatorio antes de push de cambios de infraestructura)

Este comando no ejecuta cambios reales y muestra las acciones:

```bash
DRY_RUN=1 bash deploy/install_vps.sh NO_DOMAIN /ruta/del/proyecto_padre
```

Ejemplo para este repo:

```bash
DRY_RUN=1 bash deploy/install_vps.sh NO_DOMAIN /home/ibardev/Development/zoo_picasso
```

Notas:

- El script espera que exista `generar_para_email` dentro de la ruta padre indicada.
- En `DRY_RUN=1` no se ejecutan `sudo`, ni cambios en systemd/nginx.

## Tests

La documentacion completa de pruebas esta en `TESTING.md`.

Comando rapido:

```bash
./.venv/bin/python -m pytest tests/ -q
```
