# E2E Tests para Money Pipeline - Zoo Picasso

## Descripción General

Suite completa de tests E2E con Playwright para verificar la integridad del pipeline de dinero (entrada → validación → cálculos → BD → Excel).

## Estructura

```
tests/
├── conftest.py                          # Fixtures compartidas
├── pytest.ini                           # Configuración de pytest
├── helpers/
│   ├── __init__.py
│   ├── db_helper.py                    # Helper para consultas BD
│   └── file_helper.py                  # Helper para lectura de Excel
├── fixtures/
│   ├── __init__.py
│   └── test_data.py                    # Datos de prueba
└── e2e/
    ├── __init__.py
    └── money_pipeline_spec.py          # 15 tests críticos
```

## Requisitos

```bash
# Asegurar que estamos en el venv
source .venv/bin/activate

# Instalar dependencias (si no están ya)
pip install playwright pytest pytest-asyncio openpyxl
```

## Tests Implementados (15)

### BLOQUE 1: Validaciones (Tests 1-5)

| Test | Descripción | Criterio |
|------|-------------|----------|
| Test 1 | Formatos de precio válidos | Acepta "25.50", "25,50", "100", "0.99" |
| Test 2 | Formatos de precio inválidos | Rechaza "-25.50", "25.999", "abc" |
| Test 3 | Cantidades válidas | Acepta 1, 10, 100 |
| Test 4 | Cantidades inválidas | Rechaza 0, -1 |
| Test 5 | Campos requeridos | Cliente y categoría son obligatorios |

### BLOQUE 2: Cálculos (Tests 6-10)

| Test | Descripción | Criterio |
|------|-------------|----------|
| Test 6 | Multiplicación simple | 2 × 10.00 = 20.00 |
| Test 7 | Redondeo de decimales | 3 × 10.01 = 30.03 (exacto) |
| Test 8 | Suma multilinea | (2×15.50) + (1×10.75) + (3×5.25) = 57.50 |
| Test 9 | Pago exacto | Total 45.50, pago 45.50 = vuelto 0.00 |
| Test 10 | Precisión alta | 3 × 33.33 = 99.99 (exacto) |

### BLOQUE 3: Verificación en BD (Tests 11-15)

| Test | Descripción | Criterio |
|------|-------------|----------|
| Test 11 | Una línea se guarda | BD contiene: categoria='perro', cantidad=1, monto=25.00 |
| Test 12 | Números de factura incrementan | Cada nueva factura tiene número secuencial (YYYY-NNN) |
| Test 13 | Múltiples líneas correctas | 2 líneas: (2×20.00) + (1×15.00) = 55.00 |
| Test 14 | Resumen por categoría | por_categoria['perro']=10.00, por_categoria['gato']=20.00 |
| Test 15 | Aislamiento de facturas | 2 facturas (15.00, 20.00) se guardan sin interferencia |

## Ejecutar Tests

### Todos los tests
```bash
source .venv/bin/activate
pytest tests/e2e/money_pipeline_spec.py -v
```

### Un test específico
```bash
# Test 6 (multiplicación simple)
pytest tests/e2e/money_pipeline_spec.py::TestCalculos::test_6_simple_multiplication -v

# Tests del bloque de validaciones
pytest tests/e2e/money_pipeline_spec.py::TestValidaciones -v
```

### Con salida detallada
```bash
pytest tests/e2e/money_pipeline_spec.py -v --tb=short
```

### Modo headless/visible (cambiar en conftest.py)
```bash
# Headless (por defecto, no muestra navegador)
pytest tests/e2e/money_pipeline_spec.py -v

# Visible (muestra navegador)
# Editar en conftest.py: headless=False en async_playwright()
```

## Pre-requisitos para Ejecución

1. **Aplicación FastAPI ejecutándose**: `http://localhost:8000`
   ```bash
   # En otra terminal
   python main.py
   ```

2. **BD SQLite accesible**: `data/ventas.db` debe existir

3. **Directorio de facturas**: `facturas/` debe existir

## Interpretación de Resultados

### Test Exitoso ✅
```
tests/e2e/money_pipeline_spec.py::TestValidaciones::test_1_valid_price_formats PASSED
```

### Test Fallido ❌
```
tests/e2e/money_pipeline_spec.py::TestCalculos::test_6_simple_multiplication FAILED
AssertionError: assert 20.01 == 20.00
```

**Acciones correctivas:**
1. Verificar cálculos en app.js (puede haber problema de punto flotante)
2. Verificar almacenamiento en BD (puede haber redondeo incorrecto)
3. Ejecutar test individual con `-s` para ver logs: `pytest ... -s`

## Helpers Disponibles

### DBHelper
```python
from tests.helpers import DBHelper

db = DBHelper(Path("data/ventas.db"))
db.get_last_factura_numero()           # Último número de factura
db.get_venta_by_factura("2024-001")    # Líneas de factura
db.get_pago_by_factura("2024-001")     # Datos de pago
db.get_resumen_ventas_hoy()            # Resumen del día
db.get_total_ventas("2024-001")        # Total de factura
db.limpiar_facturas_hoy()              # Limpiar datos de hoy
db.limpiar_factura("2024-001")         # Limpiar factura específica
```

### FileHelper
```python
from tests.helpers import FileHelper

FileHelper.get_last_factura_file(Path("facturas/"))      # Último Excel generado
FileHelper.read_excel_total(Path("facturas/...xlsx"))    # Total del Excel
FileHelper.read_excel_lineas(Path("facturas/...xlsx"))   # Líneas del Excel
FileHelper.read_excel_cliente(Path("facturas/...xlsx"))  # Datos de cliente
FileHelper.verify_factura_file_exists(Path("facturas/"), "2024-001")
```

## Debugging

### Ver eventos del navegador
```python
# En conftest.py, descomentar:
page.on("console", lambda msg: print(f"[Console] {msg.text}"))
page.on("request", lambda req: print(f"[Request] {req.url}"))
```

### Pausar test para inspeccionar
```python
await page.pause()  # Pausa en Playwright Inspector
```

### Screenshot en caso de fallo
```python
await page.screenshot(path="screenshot-test-failed.png")
```

## Extensión Futura

### Próximos Bloques (Tests 16-30)

- **Tests 16-20**: Edge cases (montos pequeños, grandes, refunds)
- **Tests 21-24**: Verificación de Excel generado
- **Tests 25-28**: Generación de tickets (ESC/POS)
- **Tests 29-30**: Recuperación de borradores

## Troubleshooting

| Problema | Solución |
|----------|----------|
| "timeout waiting for selector" | Aplicación no está en http://localhost:8000 |
| "database is locked" | Detener otras conexiones a BD o usar transacciones |
| "No such table: ventas" | BD no existe o está corrupta, restore desde backup |
| "Página no carga" | Verificar que FastAPI está ejecutándose sin errores |

## Contribuciones

Cuando agregues nuevos tests:
1. Documentar en este README
2. Usar fixtures de db_helper y file_helper
3. Limpiar datos con `cleanup_test_data()` o `db_helper.limpiar_facturas_hoy()`
4. Agregar al menos un assert por test
5. Incluir docstring con criterio de éxito
