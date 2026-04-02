# Zoo Picasso — Sistema de tickets

Aplicación de escritorio para generar, guardar e imprimir tickets de compra en Zoo Picasso. Interfaz Tkinter, persistencia en Excel y soporte para impresora térmica ESC/POS por red.

## Requisitos

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) para gestión de dependencias

## Instalación

```bash
uv sync
```

## Configuración

Las siguientes variables de entorno deben definirse antes de ejecutar en producción:

| Variable | Descripción | Ejemplo |
| --- | --- | --- |
| `ZOO_PICASSO_NIF` | NIF del negocio para el ticket | `B12345678` |
| `ZOO_PICASSO_PRINTER_IP` | IP de la impresora térmica en la red local | `192.168.1.100` |
| `ZOO_PICASSO_PRINTER_PORT` | Puerto de la impresora (por defecto: `9100`) | `9100` |

Si `ZOO_PICASSO_NIF` o `ZOO_PICASSO_PRINTER_IP` no están configuradas, la aplicación arrancará con una advertencia en el log.

## Ejecución

```bash
uv run main.py
```

## Tests manuales

Sin impresora:

```bash
uv run test_manual.py
```

Con impresora (requiere `ZOO_PICASSO_PRINTER_IP` configurada):

```bash
ZOO_PICASSO_TEST_PRINT=1 uv run test_manual.py
```

## Estructura del proyecto

```text
zoo_picasso/
├── main.py              # Interfaz gráfica (Tkinter)
├── test_manual.py       # Tests de integración manuales
├── src/
│   ├── ticket_model.py  # Modelo de datos (LineaTicket, Ticket)
│   ├── counter.py       # Numeración secuencial de tickets
│   ├── excel_writer.py  # Persistencia en .xlsx
│   └── printer.py       # Impresora térmica ESC/POS
└── data/
    ├── contador.json    # Contador persistido
    └── tickets.xlsx     # Registro de tickets
```

## Impresora

Probado con **pcCom Essential** (rollo 58mm, 32 caracteres de ancho) via LAN en el puerto TCP 9100.
Para rollo de 80mm, cambiar `ANCHO_TICKET = 48` en [src/printer.py](src/printer.py).
