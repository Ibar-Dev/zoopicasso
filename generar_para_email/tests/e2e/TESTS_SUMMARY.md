# Resumen de Tests E2E con Playwright

## 📋 Archivos Creados

### 1. **test_invoice_generation_flow.py** (Principal)
**Ubicación:** `generar_para_email/tests/e2e/test_invoice_generation_flow.py`

**Contenido:** Suite completa de tests del flujo de generación de facturas
- ✅ 12 tests en clase `TestInvoiceGenerationFlow`
- ✅ Login válido e inválido
- ✅ Agregar/eliminar líneas
- ✅ Rellenar datos del cliente
- ✅ Seleccionar categorías
- ✅ Cálculo de totales
- ✅ Generación de factura
- ✅ Validación de campos requeridos
- ✅ Validación de formato de precio
- ✅ Acumulación diaria

**Cobertura:** ~200 líneas de tests

---

### 2. **test_keyboard_shortcuts.py** (Tests de Atajos - NUEVO)
**Ubicación:** `generar_para_email/tests/e2e/test_keyboard_shortcuts.py`

**Contenido:** Tests específicos para atajos de teclado post-fix Windows 11
- ✅ 8 tests en clase `TestKeyboardShortcuts`
- ✅ Verificación Ctrl+Shift+A (agregar línea)
- ✅ Verificación Ctrl+Shift+D (eliminar línea)
- ✅ Verificación Ctrl+Shift+G (generar factura)
- ✅ Sin conflictos con navegador
- ✅ Sistema de ayuda muestra atajos correctos
- ✅ Secuencia de múltiples atajos
- ✅ Atajos funcionan con campos enfocados

**Propósito:** Garantizar que los atajos de teclado Windows-compatible funcionan correctamente

**Cobertura:** ~250 líneas de tests

---

### 3. **conftest_playwright.py** (Configuración)
**Ubicación:** `generar_para_email/tests/e2e/conftest_playwright.py`

**Contenido:** Configuración completa de fixtures y setup/teardown
- ✅ Lanzamiento automático de servidor FastAPI (puerto 8000)
- ✅ Espera a que servidor esté listo (max 60 segundos)
- ✅ Inicialización de BD
- ✅ Cleanup seguro del servidor
- ✅ Markers personalizados (@slow, @integration, @login, @invoice, @printer)
- ✅ Hooks para captura de screenshots en fallos
- ✅ Fixture `app_url` para todas las pruebas

**Características:**
- Manejo seguro de proceso con signal.SIGTERM/SIGKILL
- Logs detallados de startup/shutdown
- Setup automático de BD de ventas

**Código:** ~100 líneas

---

### 4. **README_PLAYWRIGHT.md** (Documentación Principal)
**Ubicación:** `generar_para_email/tests/e2e/README_PLAYWRIGHT.md`

**Contenido:** Guía completa para ejecutar tests
- ✅ Descripción de archivos de tests
- ✅ Requisitos e instalación
- ✅ 5 formas de ejecutar tests (todos, específico, con HTML report, headed, etc.)
- ✅ Tabla de cobertura de tests
- ✅ Estructura de fixtures
- ✅ Debugging y troubleshooting
- ✅ Ejemplos de ejecución
- ✅ Integración CI/CD
- ✅ Próximos pasos

**Lectura:** ~150 líneas

---

### 5. **SELECTORS_AND_BEST_PRACTICES.md** (Guía Técnica)
**Ubicación:** `generar_para_email/tests/e2e/SELECTORS_AND_BEST_PRACTICES.md`

**Contenido:** Referencia técnica para escribir tests
- ✅ Selectors disponibles (Login, Formulario, Totales, Diálogos)
- ✅ Patrones de buenas prácticas (8 patrones detallados)
- ✅ Esperas explícitas vs. implícitas
- ✅ Manejo de elementos dinámicos
- ✅ Validación de estados
- ✅ Debugging avanzado
- ✅ Ejemplos completos
- ✅ Tests parametrizados
- ✅ Troubleshooting común

**Lectura:** ~300 líneas

---

### 6. **run_e2e_tests.py** (Script Auxiliar)
**Ubicación:** `generar_para_email/tests/e2e/run_e2e_tests.py`

**Contenido:** Script Python para ejecutar tests fácilmente
```bash
python tests/e2e/run_e2e_tests.py all              # Todos
python tests/e2e/run_e2e_tests.py invoice         # Solo facturas
python tests/e2e/run_e2e_tests.py --headed        # Ver navegador
python tests/e2e/run_e2e_tests.py --html          # Con reporte HTML
```

**Características:**
- Interfaz simple y clara
- Opciones: filter, headed, html_report, verbose
- Salida con emojis y formato
- Exit codes correctos

**Código:** ~100 líneas

---

## 🎯 Cobertura de Tests

| Feature | Tests | Status |
|---------|-------|--------|
| Login | 2 (valid, invalid) | ✅ |
| Agregar líneas | 1 | ✅ |
| Eliminar líneas | 1 | ✅ |
| Datos de cliente | 1 | ✅ |
| Categorías | 1 | ✅ |
| Cálculo de totales | 1 | ✅ |
| Generación factura | 1 | ✅ |
| Cancelar generación | 1 | ✅ |
| Validación campos | 1 | ✅ |
| Validación precio | 1 | ✅ |
| Acumulado diario | 1 | ✅ |
| Archivo generado | 1 | ✅ |
| Atajos de teclado | 8 | ✅ |
| **TOTAL** | **≥ 20** | ✅ |

---

## 🚀 Inicio Rápido

### Instalación (Una sola vez)

```bash
cd generar_para_email

# Instalar dependencias (si no lo hizo)
uv sync

# Instalar browsers de Playwright
playwright install
```

### Ejecutar Tests

```bash
# Opción 1: Todos los tests
pytest tests/e2e/ -v

# Opción 2: Solo generación de facturas
pytest tests/e2e/test_invoice_generation_flow.py -v

# Opción 3: Solo atajos de teclado
pytest tests/e2e/test_keyboard_shortcuts.py -v

# Opción 4: Con script auxiliar
python tests/e2e/run_e2e_tests.py all

# Opción 5: Ver navegador en acción (cambiar headless=False en test)
pytest tests/e2e/ -v -s
```

---

## 📊 Estructura de Directorios

```
generar_para_email/
└── tests/
    └── e2e/
        ├── conftest.py                          # Config existente
        ├── conftest_playwright.py               # ✨ Nuevo - Config Playwright
        ├── test_invoice_generation_flow.py      # ✨ Nuevo - Tests principales
        ├── test_keyboard_shortcuts.py           # ✨ Nuevo - Tests de atajos
        ├── run_e2e_tests.py                     # ✨ Nuevo - Script auxiliar
        ├── README_PLAYWRIGHT.md                 # ✨ Nuevo - Guía principal
        ├── SELECTORS_AND_BEST_PRACTICES.md      # ✨ Nuevo - Referencia técnica
        ├── test_money_pipeline_basic.py         # Existente
        ├── test_cierres.py                      # Existente
        ├── test_edge_cases.py                   # Existente
        └── ...más tests
```

---

## 🔧 Configuración Automática

El servidor FastAPI se inicia automáticamente:
- **Puerto:** 8000
- **Host:** 127.0.0.1
- **Timeout:** 60 segundos máximo
- **Cleanup:** Automático al terminar tests

```python
# conftest_playwright.py maneja todo:
@pytest.fixture(scope="session", autouse=True)
def server_process():
    # Inicia servidor
    # Espera a que esté listo
    # Cleanup al terminar
```

---

## ✅ Validaciones Incluidas

### Tests de Generación de Facturas
- ✅ Página de login carga correctamente
- ✅ Login con credenciales válidas
- ✅ Login rechaza credenciales inválidas
- ✅ Agregar múltiples líneas
- ✅ Eliminar líneas (mínimo 1 required)
- ✅ Llenar datos del cliente (opcional)
- ✅ Seleccionar categoría
- ✅ Cálculo correcto de totales (cantidad × precio)
- ✅ Generar factura exitosamente
- ✅ Diálogo de impresión/cancelación
- ✅ Campos requeridos validados
- ✅ Formato de precio validado
- ✅ Acumulación diaria registrada

### Tests de Atajos de Teclado (NUEVO)
- ✅ Atajos mostrados correctamente en UI (Ctrl+Shift+, no Alt+)
- ✅ Ctrl+Shift+A: agrega línea
- ✅ Ctrl+Shift+D: elimina línea
- ✅ Ctrl+Shift+G: genera factura
- ✅ No interfieren con navegador
- ✅ Sistema de ayuda actualizado
- ✅ Funcionan en secuencia
- ✅ Funcionan con campos enfocados

---

## 📈 Características Avanzadas

### 1. Selectors Robustos
- Por ID (preferido)
- Por atributo label
- Por placeholder
- Por texto visible
- Combinaciones

### 2. Esperas Inteligentes
- Auto-waits implícitos
- `page.wait_for_selector()`
- `page.wait_for_function()`
- Timeouts configurables

### 3. Debugging
- Screenshots en fallos
- Logs del navegador
- Inspección de HTML
- Pausas en breakpoints

### 4. Reportes
- Output verbose
- Reporte HTML
- Timing de cada test
- Screenshots inclusos

---

## 🐛 Troubleshooting

### "Servidor no inicia"
```bash
# Verificar que el puerto 8000 está libre
lsof -i :8000

# O especificar puerto diferente en conftest_playwright.py
os.environ["PORT"] = "8001"
```

### "Elemento no encontrado"
```python
# Usar screenshot para debugging
page.screenshot(path="debug.png")

# Aumentar timeout
page.wait_for_selector("#elemento", timeout=10000)
```

### "Test timeout"
```bash
# Aumentar timeout global
pytest tests/e2e/ -v --timeout=30
```

---

## 📚 Referencias

- [Documentación README](README_PLAYWRIGHT.md)
- [Guía de Selectors](SELECTORS_AND_BEST_PRACTICES.md)
- [Playwright Docs](https://playwright.dev/python/)
- [pytest Docs](https://docs.pytest.org/)

---

## ✨ Próximos Pasos

- [ ] Tests de impresión de tickets (USB)
- [ ] Tests de flujo de pago (efectivo, tarjeta, mixto)
- [ ] Tests de cierre mensual
- [ ] Tests de cierre diario
- [ ] Tests de reportes
- [ ] Performance tests
- [ ] Tests de accesibilidad (a11y)
- [ ] Integración con CI/CD (GitHub Actions)

---

## 📝 Notas Importantes

1. **Credenciales de Test:** Usuario `Giselle`, Contraseña `123456`
2. **URL Default:** `http://localhost:8000`
3. **BD:** Se limpia antes/después de cada test (hoy)
4. **Browsers:** Chrome headless por defecto
5. **Atajos:** Ctrl+Shift+A/D/G (corregidos para Windows 11)

---

**Creado:** 2026-06-30  
**Versión:** 1.0  
**Estado:** ✅ Lista para usar
