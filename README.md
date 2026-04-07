# Zoo Picasso — Sistema de tickets

Aplicación web local para generar, guardar e imprimir tickets en Zoo Picasso. Interfaz Flet (navegador), persistencia en Excel e impresora térmica ESC/POS por USB.

## Requisitos

- [uv](https://docs.astral.sh/uv/) — gestiona Python y dependencias automáticamente

## Instalación

```bash
uv sync
```

## Ejecución

```bash
uv run main.py
```

Abre automáticamente el navegador en `http://localhost:8080`.

## Impresora

Modelo: **POS-80** conectada por USB (`VID 1FC9` / `PID 2016`, rollo 80mm, 48 caracteres de ancho).

**En Windows** es necesario instalar el driver WinUSB con [Zadig](https://zadig.akeo.ie):

1. Conectar la impresora por USB
2. Abrir Zadig → seleccionar el dispositivo POS-80
3. Instalar driver **WinUSB**

## Tests manuales

Sin impresora:

```bash
uv run test_manual.py
```

Con impresora conectada:

```bash
ZOO_PICASSO_TEST_PRINT=1 uv run test_manual.py
```

## Estructura del proyecto

```text
zoo_picasso/
├── main.py              # Interfaz gráfica (Flet)
├── test_manual.py       # Tests de integración manuales
├── src/
│   ├── ticket_model.py  # Modelo de datos (LineaTicket, Ticket)
│   ├── counter.py       # Numeración secuencial de tickets
│   ├── excel_writer.py  # Persistencia en .xlsx
│   └── printer.py       # Impresora térmica ESC/POS por USB
└── data/
    ├── contador.json    # Contador persistido
    └── tickets.xlsx     # Registro de tickets
```
