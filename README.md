# Zoo Picasso — Sistema de tickets y facturas

Dos aplicaciones independientes para Zoo Picasso:

- **Tickets** — Genera, guarda e imprime tickets en TPV (interfaz web, impresora térmica ESC/POS por USB)
- **Facturas** — Genera facturas en `.xlsx` para LibreOffice Calc (interfaz escritorio, sin impresora)

## Requisitos

- [uv](https://docs.astral.sh/uv/) — gestiona Python y dependencias automáticamente

---

## App de Tickets

### Instalación

```bash
uv sync
```

### Ejecución

```bash
uv run main.py
```

Abre automáticamente el navegador en `http://localhost:8080`.

### Impresora

Modelo: **POS-80** conectada por USB (`VID 1FC9` / `PID 2016`, rollo 80mm, 48 caracteres de ancho).

**En Windows** es necesario instalar el driver WinUSB con [Zadig](https://zadig.akeo.ie):

1. Conectar la impresora por USB
2. Abrir Zadig → seleccionar el dispositivo POS-80
3. Instalar driver **WinUSB**

### Tests manuales

```bash
uv run test_manual.py                          # Sin impresora
ZOO_PICASSO_TEST_PRINT=1 uv run test_manual.py # Con impresora
```

---

## App de Facturas (Gisselle Marin Tabares)

Genera facturas con IVA desglosado (21%) en formato `.xlsx` para enviar por email.
Funciona como app de escritorio independiente, sin necesidad de navegador.

### Ejecutar facturas

```bash
uv run generar_para_email/main.py
```

Las facturas se guardan en `generar_para_email/facturas/factura_YYYY_NNN.xlsx`.

### Instalación en Windows (ordenador de Gisselle)

1. Instalar uv: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
2. Copiar la carpeta `generar_para_email/` al PC de destino
3. Doble clic en `generar_para_email/Facturas.bat`

---

## Estructura del proyecto

```text
zoo_picasso/
├── main.py                       # Tickets — Interfaz Flet (navegador, puerto 8080)
├── test_manual.py                # Tests de integración manuales
├── Facturas.bat                  # Atajo Windows para lanzar la app de facturas
├── src/
│   ├── ticket_model.py           # Modelo de datos (LineaTicket, Ticket)
│   ├── counter.py                # Numeración secuencial de tickets
│   ├── excel_writer.py           # Persistencia en .xlsx
│   └── printer.py                # Impresora térmica ESC/POS por USB
├── data/
│   ├── contador.json             # Contador de tickets persistido
│   └── tickets.xlsx              # Registro de todos los tickets
└── generar_para_email/           # App de facturas (independiente)
    ├── main.py                   # Interfaz Flet (escritorio)
    ├── pyproject.toml            # Dependencias propias (flet + openpyxl)
    ├── Facturas.bat              # Lanzador Windows
    ├── src/
    │   ├── factura_model.py      # Modelo de datos (LineaFactura, Factura)
    │   ├── factura_counter.py    # Numeración secuencial de facturas
    │   └── factura_writer.py     # Genera .xlsx con formato de factura
    ├── data/
    │   └── contador_facturas.json  # Contador de facturas persistido
    └── facturas/                 # Facturas generadas (se crea automáticamente)
        └── factura_YYYY_NNN.xlsx
```
