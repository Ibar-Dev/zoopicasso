# Guía de Tests E2E con Playwright

## Descripción

Este directorio contiene tests end-to-end (E2E) para la aplicación web de facturas, utilizando **Playwright**.

### Archivos de Tests

- **test_invoice_generation_flow.py** - Tests del flujo completo de generación de facturas
  - Login
  - Completar datos de cliente
  - Agregar líneas de factura
  - Seleccionar categorías
  - Cálculo de totales
  - Generación de factura

- **test_money_pipeline_basic.py** - Tests del pipeline de dinero

- **test_cierres.py** - Tests de cierre mensual

- **test_edge_cases.py** - Tests de casos límite

- **test_excel_verification.py** - Verificación de archivos Excel generados

---

## Requisitos

```bash
# Instalar Playwright (ya está en pyproject.toml)
uv sync

# Instalar browsers de Playwright
playwright install
```

---

## Ejecutar los Tests

### Opción 1: Ejecutar todos los tests E2E

```bash
cd generar_para_email
pytest tests/e2e/ -v
```

### Opción 2: Ejecutar solo tests de generación de facturas

```bash
pytest tests/e2e/test_invoice_generation_flow.py -v
```

### Opción 3: Ejecutar un test específico

```bash
pytest tests/e2e/test_invoice_generation_flow.py::TestInvoiceGenerationFlow::test_1_login_page_loads -v
```

### Opción 4: Ejecutar con reporte en HTML

```bash
pytest tests/e2e/ -v --html=report.html --self-contained-html
```

### Opción 5: Ejecutar en modo "headed" (ver navegador)

```bash
pytest tests/e2e/test_invoice_generation_flow.py -v -s
# Luego modificar en el test:
# browser = p.chromium.launch(headless=False)  # Ver el navegador
```

---

## Estructura de los Tests

### TestInvoiceGenerationFlow

12 tests que cubren el flujo completo:

| Test | Descripción |
|------|-------------|
| test_1_login_page_loads | Página de login carga correctamente |
| test_2_login_with_valid_credentials | Login con Giselle/123456 funciona |
| test_3_login_with_invalid_credentials | Credenciales inválidas muestran error |
| test_4_add_invoice_lines | Agregar múltiples líneas de factura |
| test_5_fill_client_info | Rellenar datos del cliente |
| test_6_category_selection | Seleccionar categoría del dropdown |
| test_7_total_calculation | Cálculo correcto de totales (cantidad × precio) |
| test_8_generate_invoice_success | Generar factura y mostrar confirmación |
| test_9_cancel_invoice_generation | Cancelar sin imprimir |
| test_10_validate_required_fields | Validar campos obligatorios |
| test_11_price_format_validation | Validar formato de precio (25.50, 25,50, 100) |
| test_12_daily_accumulation | Acumulación diaria de ventas |

### TestInvoiceFileGeneration

Tests de generación de archivos:

| Test | Descripción |
|------|-------------|
| test_invoice_file_created | Verificar que se crea archivo .xlsx |

---

## Configuración de Tests

### Fixtures

- **app_url**: URL base de la aplicación (http://localhost:8000)
- **db_helper**: Helper para acceso a base de datos
- **file_helper**: Helper para verificación de archivos

### Setup/Teardown

Cada test limpia la BD antes y después de ejecutarse:

```python
@pytest.fixture(autouse=True)
def setup_teardown(self, db_helper):
    db_helper.limpiar_facturas_hoy()  # Cleanup inicial
    yield
    db_helper.limpiar_facturas_hoy()  # Cleanup final
```

---

## Requisitos para Ejecutar

### 1. Servidor FastAPI debe estar corriendo

**Opción A**: Modo automático (el conftest.py lo inicia)

```bash
# El server se lanza automáticamente
pytest tests/e2e/ -v
```

**Opción B**: Manual (si prefieres controlarlo)

```bash
# Terminal 1: Arrancar el server
cd generar_para_email
uv run uvicorn web.app:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2: Ejecutar tests
pytest tests/e2e/ -v
```

### 2. Base de datos inicializada

Los fixtures automáticamente limpian las facturas del día, pero la BD debe existir:

```bash
cd generar_para_email
uv run python -c "from src.ventas_store import inicializar_db_ventas; inicializar_db_ventas()"
```

---

## Debugging y Troubleshooting

### Ver el navegador en acción

Cambiar en el test:

```python
browser = p.chromium.launch(headless=True)  # FALSE para ver el navegador
```

### Aumentar timeouts

```python
page.wait_for_selector("#btn-generar", timeout=10000)  # 10 segundos
```

### Guardar screenshot si algo falla

```python
page.screenshot(path="debug_screenshot.png")
```

### Ver logs del navegador

```python
page = browser.new_page()
page.on("console", lambda msg: print(msg.text))
```

---

## Ejemplos Útiles

### Ejecutar solo tests que no requieren impresora

```bash
pytest tests/e2e/ -v -k "not printer"
```

### Ejecutar tests en paralelo (máximo 4 workers)

```bash
pytest tests/e2e/ -v -n 4
```

### Ejecutar con salida detallada

```bash
pytest tests/e2e/ -vv -s
```

---

## Notas Importantes

1. **Credenciales de test**: Usuario: `Giselle`, Contraseña: `123456`
2. **URL**: Los tests asumen que la app corre en `http://localhost:8000`
3. **Cleanup**: Cada test limpia las facturas del día para evitar interferencias
4. **Headless**: Por defecto los browsers corren en headless (sin interfaz gráfica) para rapidez
5. **Screenshots**: Los tests pueden guardar screenshots para debugging

---

## Integración Continua (CI)

Para ejecutar en CI/CD (GitHub Actions, GitLab CI, etc.):

```yaml
- name: Install Playwright browsers
  run: playwright install

- name: Run E2E tests
  run: pytest tests/e2e/ -v --html=report.html
```

---

## Próximos Pasos

- [ ] Agregar tests para impresión de tickets
- [ ] Tests para flujo de pago (efectivo, tarjeta, mixto)
- [ ] Tests para cierre mensual
- [ ] Mejorar selectors para mejor estabilidad
- [ ] Agregar capturas de pantalla en reportes
