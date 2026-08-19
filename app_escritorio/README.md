# Zoo Picasso — App de escritorio

Versión de escritorio unificada del sistema Zoo Picasso. Una sola ventana nativa con:

1. **Tickets (TPV)** — genera tickets, los imprime en la impresora térmica POS-80 (USB),
   los guarda en `../generar_para_email/data/tickets.xlsx` y registra cada línea en la base
   de ventas (`ventas.db`) con su categoría.
2. **Facturas** — genera facturas `.xlsx` (precios finales, IVA incluido), registra la venta
   en la base de datos con método de pago (efectivo / tarjeta / mixto) y cálculo de cambio,
   e imprime ticket térmico si se desea.
3. **Control de ventas** — resumen del día y del mes, historial filtrable por fechas,
   categoría y método de pago, y exportación a Excel (reporte mensual o historial filtrado).
4. **Envío de facturas por email** — tras generar una factura, se puede enviar el `.xlsx`
   al email del cliente mediante SMTP (Gmail recomendado). La configuración SMTP se hace
   en la pestaña **Configuración** y se guarda en `config/smtp_config.json`.

## Requisitos

- [uv](https://docs.astral.sh/uv/) (gestiona Python y dependencias)
- Impresora POS-80 por USB (en Windows requiere driver WinUSB con [Zadig](https://zadig.akeo.ie))

## Ejecución

```bash
cd app_escritorio
uv sync
uv run main.py
```

En Windows: doble clic en `IniciarApp.bat`.

## Configurar el envío de email

1. Abre la pestaña **Configuración**.
2. Rellena servidor SMTP, puerto, usuario y contraseña.
   - Gmail: servidor `smtp.gmail.com`, puerto `587`, TLS activado y una
     [App Password](https://support.google.com/accounts/answer/185833) (no la contraseña normal).
3. Pulsa **Guardar configuración** y luego **Enviar email de prueba**.
4. Al generar una factura con el email del cliente rellenado, pulsa **Enviar por email**.

## Datos que comparte con la app original

- Contadores de tickets y facturas (`data/contador.json`, `data/contador_facturas.json`)
- Excel de tickets (`data/tickets.xlsx`)
- Facturas generadas (`facturas/`)
- Base de ventas (`data/ventas.db`) — la misma que usa la versión web

## Estructura

```text
app_escritorio/
├── main.py                  # Entrada: ventana de escritorio con login y navegación
├── IniciarApp.bat           # Atajo Windows
├── pyproject.toml           # Dependencias
├── config/                  # smtp_config.json (no se sube al repo)
├── reportes/                # Excel generados por la pestana Ventas
├── escritorio/
│   ├── config_app.py        # Configuracion SMTP persistente
│   ├── email_envio.py       # Envio SMTP con adjunto .xlsx
│   ├── reportes.py          # Exportacion de reportes Excel
│   └── registro.py          # Registro de tickets en ventas.db
└── ui/
    ├── tickets_view.py      # Pestana Tickets
    ├── facturas_view.py     # Pestana Facturas
    ├── ventas_view.py       # Pestana Control de ventas
    └── email_view.py        # Pestana Configuracion (SMTP)
```

La app reutiliza los módulos de `../generar_para_email` (`src/*` y `tickets_src/*`)
añadiéndolos al `sys.path` desde `main.py`; no duplica la lógica de facturas/tickets.