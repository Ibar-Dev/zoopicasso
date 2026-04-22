# Generador de Facturas - Zoo Picasso

Aplicacion para generar facturas en formato .xlsx en dos modos:

- Escritorio con Flet (main.py)
- Web con FastAPI (web/app.py)

Este README cumple dos funciones:

- Guia de arranque rapido
- Bitacora operativa y caja negra de diagnostico para fallos futuros

## Estado funcional actual

- Login de acceso en modo web.
- Creacion de facturas por lineas (concepto, cantidad, precio unitario, categoria).
- Generacion de Excel de factura.
- Impresion de ticket en flujo web (encolado backend + vista de impresion navegador).
- Edicion global de precios por categoria con confirmacion y logging.
- Registro mensual de ventas en SQLite (estado active/archived).
- Resumen mensual por categoria en backend.
- Cierre mensual con exportacion Excel y archivado de ventas activas.
- Confirmaciones de acciones sensibles (ticket, salida, cierre mensual).

## Estructura principal

- main.py: app de escritorio (Flet).
- web/app.py: backend web (FastAPI).
- web/templates/index.html: interfaz web.
- src/factura_model.py: modelos de factura y linea.
- src/factura_counter.py: contador correlativo de facturas.
- src/factura_writer.py: generacion de Excel de factura.
- src/printer.py: generacion de ticket ESC/POS.
- src/ventas_store.py: persistencia SQLite de ventas mensuales.
- src/monthly_closure.py: cierre mensual y exportacion de ganancias.
- src/settings.py: configuracion y logging centralizado.

## Requisitos

- Python 3.11+.
- uv para gestionar dependencias.

## Variables de entorno relevantes

### Emisor (ticket web)

- EMISOR_NIF (default: Y3806548Q)
- EMISOR_NOMBRE (default: Gisselle Marin Tabares)
- EMISOR_DIRECCION (default: Calle de Pablo Picasso 59)
- EMISOR_TELEFONO (default: 642 342 110)
- EMISOR_EMAIL (default: zoopicasso07@gmail.com)
- EMISOR_NEGOCIO (default: Zoo Picasso)

### Rutas y persistencia

- FACTURAS_DIR: carpeta de salida de facturas .xlsx.
- CONTADOR_PATH: ruta del JSON de contador de facturas.
- VENTAS_DB_PATH: ruta del SQLite de ventas mensuales.
- CIERRES_DIR: carpeta de salida de Excel de cierre mensual.

### Sesion web

- WEB_SESSION_SECRET
- WEB_SESSION_SAME_SITE
- WEB_SESSION_HTTPS_ONLY

## Ejecucion local

### Modo escritorio

uv sync
uv run main.py

### Modo web

uv sync
uv run uvicorn web.app:app --host 0.0.0.0 --port 8081 --reload

## Tests

./.venv/bin/python -m pytest tests/ -q

## Caja negra de operacion y diagnostico

Esta seccion debe leerse antes de tocar codigo en produccion.

### Flujo critico de facturacion web

1. Login valido.
2. POST /api/generar crea factura y Excel.
3. Si corresponde, se encola ticket para impresion.
4. Se registra venta mensual en background (no bloquea ticket ni respuesta).
5. UI refresca resumen mensual desde backend.

Puntos que NO deben romperse:

- /api/generar debe responder aunque falle el registro mensual.
- La impresion de ticket no debe depender de SQLite.
- La descarga de Excel debe seguir funcionando igual.

### Flujo critico de cierre mensual

1. Usuario confirma cierre en modal.
2. POST /api/ganancias/cierre-mes.
3. Se calcula resumen de ventas active del mes actual.
4. Se genera Excel de cierre.
5. Solo si el Excel se verifica, se archivan ventas active a archived.
6. UI vuelve a consultar resumen mensual; total deberia quedar en 0.

## Checklist rapido ante incidente

### Si falla generar factura

1. Revisar logs/app.log.
2. Probar /api/health.
3. Confirmar permisos de FACTURAS_DIR.
4. Confirmar estado de contador (CONTADOR_PATH).
5. Validar payload enviado desde UI (lineas, categoria, precios).

### Si falla impresion de ticket

1. Revisar logs de app para encolado de ticket.
2. Verificar endpoint /api/impresion/siguiente.
3. Confirmar que no se modifico src/printer.py.
4. Confirmar que el modal de ticket en frontend sigue operativo.

### Si falla resumen/cierre mensual

1. Revisar permisos de escritura en VENTAS_DB_PATH y CIERRES_DIR.
2. Confirmar existencia y accesibilidad de data/ventas.db.
3. Revisar logs de process_monthly_closure.
4. Validar que haya ventas active en el mes actual.
5. Verificar que el Excel de cierre fue generado y no esta vacio.

## Matriz de sintomas y causa probable

- La app web no arranca: ruta de SQLite inaccesible o error de inicializacion de DB.
- Genera factura pero no sube ganancias mensuales: fallo en tarea background de registro.
- Cierre mensual dice ok pero total no baja a cero: no se archivaron registros active.
- No se puede guardar precios por categoria: sesion no valida o error en data/precios_categorias.json.
- Ticket no sale pero factura si: problema de encolado/consumo, no de facturacion.

## Politica de rollback operativo

Ante fallo grave en produccion:

1. Volver al ultimo commit estable publicado.
2. Conservar backups de:
	- data/contador_facturas.json
	- data/precios_categorias.json
	- data/ventas.db
	- data/cierres/
3. Verificar /api/health, login, generar, descargar e impresion.
4. Rehabilitar cierre mensual solo tras smoke test.

## Cuaderno de bitacora (actualizar en cada incidente)

Plantilla sugerida:

- Fecha y hora:
- Entorno (local, VPS, branch, commit):
- Sintoma observado:
- Impacto (facturacion, ticket, cierre mensual, UI):
- Logs relevantes:
- Causa raiz:
- Accion correctiva aplicada:
- Validacion posterior:
- Tareas pendientes:

Registro inicial recomendado:

- 2026-04-22: Integracion de modulo mensual (SQLite + cierre mensual + Excel + resumen backend + modal de confirmacion). Validado con tests web en verde.

## Simulacro de deploy de infraestructura

DRY_RUN=1 bash deploy/install_vps.sh NO_DOMAIN /ruta/del/proyecto_padre

Notas:

- El script espera que exista generar_para_email dentro de la ruta padre indicada.
- En DRY_RUN=1 no se ejecutan sudo ni cambios en systemd/nginx.
