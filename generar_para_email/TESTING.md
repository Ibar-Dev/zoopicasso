# Testing Documentation - Zoo Picasso Invoice Generator

## Overview

Comprehensive test suite for the invoice generation system with **91 tests** covering all modules.

### Test Statistics
- **Total Tests**: 91
- **Passing**: 91 ✅
- **Failing**: 0
- **Execution Time**: ~0.10-0.21 seconds
- **Code Coverage**: 90% overall

## Test Structure

### 1. Unit Tests (63 tests)

#### test_factura_model.py (15 tests)
Tests for the data model validation and calculations.

**TestLineaFactura (6 tests)**
- `test_crear_linea_valida`: Valid line item creation
- `test_calculo_total`: Total calculation (qty × price)
- `test_cantidad_cero_invalida`: Quantity must be > 0
- `test_cantidad_negativa_invalida`: Negative quantities rejected
- `test_precio_negativo_invalido`: Negative prices rejected
- `test_redondeo_total`: Rounding to 2 decimal places

**TestFactura (9 tests)**
- `test_crear_factura_valida`: Valid invoice creation
- `test_factura_sin_lineas_invalida`: Must have ≥1 line
- `test_cliente_opcional`: Client fields are optional
- `test_base_imponible`: Sum of line totals
- `test_cuota_iva`: 21% IVA calculation
- `test_total_con_iva`: Total with IVA included
- `test_numero_formateado`: Format: YYYY-NNN
- `test_fecha_formateada`: Format: DD/MM/YYYY
- `test_iva_porcentaje_constante`: IVA% is constant (21%)

#### test_factura_counter.py (10 tests)
Tests for invoice numbering and JSON persistence.

- `test_leer_contador_existente`: Read existing counter
- `test_escribir_contador`: Write counter value
- `test_contador_corrupto`: Detect corrupted JSON
- `test_crear_directorio_si_no_existe`: Directory creation
- `test_formato_contador_json`: Valid JSON structure
- `test_incremento_contador`: Counter increment logic
- `test_permisos_lectura_archivo`: Read permissions
- `test_permisos_escritura_archivo`: Write permissions
- `test_numeros_grandes`: Handle large counter values
- `test_contador_cero`: Support zero counter

#### test_factura_writer.py (15 tests)
Tests for Excel generation and file operations.

- `test_crear_nombre_archivo`: File naming validation
- `test_ruta_directorio_facturas`: Directory access
- `test_escritura_archivo_basico`: Basic file writing
- `test_validar_extension_xlsx`: .xlsx extension check
- `test_ruta_documentos_windows_basica`: Windows path construction
- `test_crear_directorio_copia`: Create backup directory
- `test_copiar_archivo_simple`: File copy operation
- `test_detectar_documentos_windows`: Detect Documents folder variants
- `test_manejo_error_permiso_denegado`: Permission denied handling
- `test_archivo_ya_existe`: Overwrite existing files
- `test_tamanio_archivo_generado`: File size validation
- `test_validar_ruta_absoluta`: Absolute path verification
- `test_crear_facturas_multiples`: Multiple file creation
- `test_limpiar_caracteres_invalidos_nombre`: Invalid character detection
- `test_timestamp_archivo`: File modification time

#### test_settings.py (23 tests)
Tests for configuration and logging setup.

**TestSettingsConfiguration (14 tests)**
- `test_cargar_env_file`: Load .env configuration
- `test_env_variable_log_level`: Extract LOG_LEVEL
- `test_env_variable_log_file`: Extract LOG_FILE
- `test_env_variable_facturas_dir`: Extract FACTURAS_DIR
- `test_ruta_absolutizar`: Convert to absolute paths
- `test_ruta_con_directorio`: Create directories
- `test_niveles_log_validos`: Valid logging levels
- `test_log_max_bytes_formato`: Max bytes format
- `test_log_backup_count`: Backup count validation
- `test_env_variable_tipos`: String type variables
- `test_parsear_log_max_bytes_int`: Parse integer values
- `test_env_comentario_ignorado`: Ignore comments
- `test_env_linea_vacia_ignorada`: Ignore empty lines
- `test_ruta_relativa_basada_proyecto`: Relative path resolution

**TestLoggingSetup (9 tests)**
- `test_crear_logger`: Logger creation
- `test_logger_nivel_default`: Default logging level
- `test_handler_consola`: Console handler setup
- `test_handler_archivo`: File handler setup
- `test_rotating_file_handler`: RotatingFileHandler with rotation
- `test_log_formatter`: Log message formatting
- `test_log_mensaje_simple`: Log message capture
- `test_log_diferentes_niveles`: Multi-level logging
- `test_log_con_excepciones`: Exception logging with traceback

### 2. Integration Tests (12 tests)

#### test_integration.py
End-to-end workflow tests combining multiple modules.

**TestIntegrationFlowCompleto**
- `test_crear_factura_valida_completa`: Full invoice with all fields
- `test_factura_calculo_correcto`: Calculation accuracy across layers
- `test_contador_incremento_secuencial`: Sequential numbering workflow
- `test_generar_nombre_factura_con_contador`: Counter-based naming
- `test_guardar_archivo_factura`: File saving workflow
- `test_copiar_factura_a_documentos`: Backup copying workflow
- `test_flujo_completo_sin_cliente`: Ticket mode (no client) flow
- `test_multiples_facturas_secuencia`: Multiple sequential invoices
- `test_validacion_lineas_minimas`: Minimum lines validation
- `test_validacion_cantidades_positivas`: Quantity constraints
- `test_formateo_numero_factura_consistente`: Invoice number formatting
- `test_formateo_fecha_consistente`: Date formatting

### 3. Real-Execution Tests (15 tests)

These tests execute real module logic with monkeypatching of filesystem-dependent paths.

#### test_factura_counter_real.py (5 tests)
- `test_inicializar_contador_crea_archivo`: Creates counter file and initializes with 0
- `test_leer_y_escribir_contador_real`: Reads and writes real JSON values
- `test_siguiente_numero_factura_incrementa`: Sequential increments via public API
- `test_leer_contador_corrupto_lanza_json_error`: Corrupted JSON handling
- `test_escribir_error_io_propagado`: I/O write error propagation

#### test_factura_writer_real.py (6 tests)
- `test_generar_factura_xlsx_crea_archivo`: Real XLSX generation
- `test_generar_factura_xlsx_contenido_basico`: Validates key workbook cells
- `test_copiar_en_documentos_windows_sin_rutas`: No-copy branch
- `test_copiar_en_documentos_windows_ok`: Copy success branch
- `test_rutas_documentos_windows_env_relativa`: Windows env path resolution
- `test_copia_windows_crea_fallback_documents`: Creates fallback Documents/Facturas when needed

#### test_settings_real.py (5 tests)
- `test_cargar_env_carga_variables`: Real .env parsing
- `test_ruta_desde_env_relativa`: Relative path resolution
- `test_ruta_desde_env_defecto`: Default path fallback
- `test_configurar_logging_crea_rotating_handler`: Real rotating handler setup
- `test_configurar_logging_valores_invalidos`: Invalid numeric fallback values

## Test Fixtures (conftest.py)

Reusable pytest fixtures for test isolation:

```python
@pytest.fixture
def temp_dir(tmp_path):
    """Temporary directory with auto-cleanup"""
    return tmp_path

@pytest.fixture
def temp_contador_file(temp_dir):
    """Mock JSON counter file: {"ultima_factura": 0}"""
    file = temp_dir / "contador.json"
    file.write_text(json.dumps({"ultima_factura": 0}), encoding="utf-8")
    return file

@pytest.fixture
def temp_env_file(temp_dir):
    """Mock .env configuration file"""
    file = temp_dir / ".env"
    content = """LOG_LEVEL=INFO
LOG_FILE=logs/app.log
LOG_MAX_BYTES=5242880
LOG_BACKUP_COUNT=5
FACTURAS_DIR=facturas
"""
    file.write_text(content, encoding="utf-8")
    return file

@pytest.fixture
def sample_linea_factura_data():
    """Sample invoice line item: Servicio A, 2 units × €50"""
    return {"concepto": "Servicio A", "cantidad": 2, "precio_unitario": 50.00}

@pytest.fixture
def sample_factura_data():
    """Sample complete invoice: 2 items, €200 base + €42 IVA = €242"""
    return {
        "numero": 1,
        "fecha": date.today(),
        "cliente_nombre": "Cliente Test",
        "cliente_nif": "12345678A",
        "lineas": [
            {"concepto": "Servicio A", "cantidad": 1, "precio_unitario": 100.00},
            {"concepto": "Servicio B", "cantidad": 2, "precio_unitario": 50.00},
        ],
    }
```

## Running Tests

### Run all tests
```bash
./.venv/bin/python -m pytest tests/ -v
```

### Run specific test file
```bash
./.venv/bin/python -m pytest tests/test_factura_model.py -v
```

### Validate counter path behavior
```bash
# Default behavior (uses data/contador_facturas.json)
PYTHONPATH=. uv run --active pytest tests/test_factura_counter_real.py::test_ruta_contador_por_defecto_apunta_a_data_del_proyecto -q

# Override with absolute path via CONTADOR_PATH
PYTHONPATH=. CONTADOR_PATH=/tmp/contador.json uv run --active pytest tests/test_factura_counter_real.py::test_ruta_contador_usa_contador_path_absoluto -q
```

### Run with coverage report
```bash
./.venv/bin/python -m pytest tests/ --cov=src --cov-report=html
```

### Run with detailed output
```bash
./.venv/bin/python -m pytest tests/ -vv --tb=long
```

## Code Coverage

**Overall**: 90% (337/374 statements)

**By Module**:
| Module | Coverage | Statements |
|--------|----------|------------|
| factura_model.py | 100% | 38/38 ✅ |
| __init__.py | 100% | 0/0 ✅ |
| factura_counter.py | 81% | 38/47 |
| factura_writer.py | 89% | 196/220 |
| settings.py | 94% | 65/69 |

**Note**: Remaining uncovered lines are mostly defensive/error branches that require deep fault injection.

## Testing Approach

### Isolation Testing
- Uses temporary directories (`tmp_path` fixture)
- Mocks file I/O operations
- Tests configuration parsing in isolation
- Validates error handling without side effects

### Fixture-Based Testing
- Reusable test data across test modules
- Auto-cleanup of temporary files
- Consistent sample data (2-item invoice = €242 total)

### Error Scenario Coverage
- JSON corruption detection
- Permission denied handling
- File overwrite scenarios
- Large number support
- Invalid input validation

## Continuous Testing

To run tests after code changes:

```bash
# Watch mode (requires pytest-watch)
ptw

# Quick smoke test
./.venv/bin/python -m pytest tests/test_factura_model.py -q

# Full suite with coverage
./.venv/bin/python -m pytest tests/ --cov=src --cov-report=term-missing
```

## Git Integration

Test suite tracked in commits:
- `e5afbdd`: Initial 63 unit and settings tests
- `d90d911`: 12 integration tests (75 total)
- `63da075`: Testing documentation baseline

Run tests before committing:
```bash
./.venv/bin/python -m pytest tests/ --tb=short
```

## Future Improvements

1. **UI Testing**: Add Flet component tests (if possible)
2. **Windows Testing**: Full openpyxl Excel validation
3. **Performance Tests**: Large invoice generation benchmarks
4. **Concurrency Tests**: Simultaneous counter increments
5. **Accessibility Tests**: Keyboard navigation in Flet UI
