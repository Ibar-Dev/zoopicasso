# Guía de Selectors y Mejores Prácticas para Tests Playwright

## Selectors Disponibles

### Login

```python
# Campos de entrada
usuario_field = page.locator("#usuario")
password_field = page.locator("#password")

# Botón
login_btn = page.locator("button:has-text('Entrar')")
```

### Formulario de Factura

```python
# Cliente
page.locator("#cliente_nombre")     # Nombre del cliente
page.locator("#cliente_nif")        # NIF del cliente

# Líneas de factura (dinámicas)
concepto_inputs = page.locator("input[placeholder*='Concepto']")
precio_inputs = page.locator("input[placeholder*='P. Unit']")
cantidad_inputs = page.locator("input[placeholder*='Cant']")
total_fields = page.locator("input[label='Total']")

# Categoría (dropdown)
categoria_dropdown = page.locator("div[label='Categoría']")

# Botones
btn_add_line = page.locator("button:has-text('+ Añadir línea')")
btn_remove_line = page.locator("button:has-text('- Quitar línea')")
btn_generate = page.locator("#btn-generar")
btn_open_folder = page.locator("button:has-text('ABRIR CARPETA DE FACTURAS')")
```

### Totales y Acumulados

```python
# Labels de totales (solo lectura)
lbl_number = page.locator("text=/Factura.*\\d{4}-\\d{3}/")
lbl_iva = page.locator("text=/IVA:.*Incluido/")
lbl_total = page.locator("text=/TOTAL:.*€/")
lbl_invoices_day = page.locator("text=/FACTURAS DEL DÍA:.*\\d+/")
lbl_accumulated = page.locator("text=/ACUMULADO DEL DÍA:.*€/")
```

### Diálogos

```python
# Diálogo de impresión
dialog_print = page.locator("text=Imprimir ticket")
btn_no_print = page.locator("button:has-text('No')")
btn_yes_print = page.locator("button:has-text('Sí, imprimir')")

# Mensajes de error
error_msg = page.locator("text=/error|Error/i")
success_msg = page.locator("text=/✓|Success|guardada/i")
```

---

## Patrones y Mejores Prácticas

### 1. Usar Locators, no Selectors CSS Manuales

✅ **BIEN:**
```python
usuario = page.locator("#usuario")
usuario.fill("Giselle")
```

❌ **MALO:**
```python
# Evitar acceso directo al DOM
usuario = page.query_selector("#usuario")
```

### 2. Esperar Explícitamente

✅ **BIEN:**
```python
page.wait_for_selector("#btn-generar", timeout=5000)
page.locator("button:has-text('Entrar')").click()
page.wait_for_selector("text=Imprimir ticket", timeout=10000)
```

❌ **MALO:**
```python
time.sleep(2)  # Evitar sleeps fijos
page.click("button")
```

### 3. Usar Expect para Aserciones

✅ **BIEN:**
```python
from playwright.sync_api import expect

expect(page.locator("#usuario")).to_be_visible()
expect(page.locator("#usuario")).to_be_enabled()
expect(page.locator("text=Error")).not_to_be_visible()
```

❌ **MALO:**
```python
assert page.locator("#usuario").is_visible()
```

### 4. Manejo de Elementos Dinámicos

Para campos que se agregan/remueven dinámicamente:

```python
# Esperar a que esté presente
page.wait_for_selector("input[placeholder*='Concepto']")

# Obtener todos los elementos
concepto_inputs = page.locator("input[placeholder*='Concepto']")
count = concepto_inputs.count()

# Acceder al primero/último
first_input = concepto_inputs.first
last_input = concepto_inputs.last

# O por índice
segundo_input = concepto_inputs.nth(1)

# Iterar
for i in range(concepto_inputs.count()):
    input_field = concepto_inputs.nth(i)
    input_field.fill(f"Item {i+1}")
```

### 5. Llenar Campos de Forma Robusta

```python
# Para text inputs
input_field = page.locator("#cliente_nombre")
input_field.fill("")  # Limpiar primero
input_field.fill("Nueva Clínica Veterinaria")

# Para dropdowns
page.click("div[label='Categoría']")
page.wait_for_selector("text=perro")
page.click("text=perro")

# Para campos de precio (manejar comas y puntos)
price_input = page.locator("input[placeholder*='P. Unit']")
price_input.fill("25.50")  # O "25,50"
```

### 6. Validar Estados

```python
# Verificar que el valor se guardó
assert page.locator("#usuario").input_value() == "Giselle"

# Verificar que está deshabilitado
expect(page.locator("#btn-generar")).to_be_disabled()

# Verificar visibilidad
expect(page.locator("text=Imprimir ticket")).to_be_visible()
```

### 7. Debugging

```python
# Capturar screenshot
page.screenshot(path=f"debug_{test_name}.png")

# Inspeccionar HTML
html = page.content()
print(html)

# Ver logs del navegador
page.on("console", lambda msg: print(f"LOG: {msg.text}"))

# Pausar en un punto
page.pause()  # Requiere --debug

# Información del elemento
locator = page.locator("#usuario")
print(locator.get_attribute("placeholder"))
print(locator.inner_text())
print(locator.input_value())
```

### 8. Manejo de Errores

```python
try:
    page.locator("element_que_no_existe").click(timeout=1000)
except Exception as e:
    print(f"Element no encontrado: {e}")
    page.screenshot(path="error.png")

# O usar esperas con timeout
try:
    page.wait_for_selector("#elemento", timeout=2000)
except TimeoutError:
    print("Elemento no apareció dentro del timeout")
```

---

## Selectors Robustos (Por Orden de Preferencia)

### 1. Por atributo ID (Más Robusto)

```python
page.locator("#cliente_nombre")
page.locator("#btn-generar")
```

### 2. Por atributo label

```python
page.locator("input[label='Total']")
page.locator("div[label='Categoría']")
```

### 3. Por placeholder

```python
page.locator("input[placeholder*='Concepto']")  # Contiene
page.locator("input[placeholder^='P. Unit']")   # Empieza con
```

### 4. Por texto visible (Menos Robusto)

```python
page.locator("button:has-text('Entrar')")
page.locator("text=Usuario o contraseña incorrectos")
```

### 5. Por combinación de atributos

```python
page.locator("input[type='text'][placeholder*='cliente']")
```

---

## Timing y Sincronización

### Auto-waits de Playwright (Automático)

```python
# Playwright espera automáticamente:
# 1. Que el elemento sea visible
# 2. Que esté habilitado
# 3. Que pueda recibir clicks

page.click("button")  # Espera automáticamente
page.fill("input", "valor")  # Espera automáticamente
```

### Esperas Explícitas

```python
# Esperar a elemento
page.wait_for_selector("#elemento", timeout=5000)

# Esperar a función
page.wait_for_function(
    "() => document.querySelectorAll('input').length > 3",
    timeout=5000
)

# Esperar a evento de navegación
with page.expect_navigation():
    page.click("a[href='/new-page']")
```

---

## Ejemplos Completos

### Test Básico con Todas las Prácticas

```python
def test_complete_invoice_generation_example(app_url):
    """Test completo que demuestra buenas prácticas"""
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # 1. Navegar
            page.goto(app_url, wait_until="networkidle")
            
            # 2. Esperar elementos
            page.wait_for_selector("#usuario", timeout=5000)
            
            # 3. Llenar y validar
            usuario = page.locator("#usuario")
            usuario.fill("Giselle")
            assert usuario.input_value() == "Giselle"
            
            # 4. Interactuar con elementos dinámicos
            page.locator("button:has-text('Entrar')").click()
            page.wait_for_selector("#btn-generar", timeout=5000)
            
            # 5. Usar expect para aserciones
            expect(page.locator("text=Generador de Facturas")).to_be_visible()
            
            # 6. Llenar múltiples campos
            concepto_inputs = page.locator("input[placeholder*='Concepto']")
            expect(concepto_inputs.first).to_be_visible()
            concepto_inputs.first.fill("Servicio veterinario")
            
            # 7. Capturar en caso de error
            assert page.locator("#btn-generar").is_enabled()
            
        except Exception as e:
            page.screenshot(path=f"error_{int(time.time())}.png")
            raise
        
        finally:
            browser.close()
```

### Test con Datos Parametrizados

```python
@pytest.mark.parametrize("precio,cantidad,esperado", [
    ("25.50", "1", "25.50"),
    ("25,50", "1", "25.50"),
    ("100", "2", "200.00"),
    ("10.99", "3", "32.97"),
])
def test_price_calculations(app_url, precio, cantidad, esperado):
    """Test de cálculos con diferentes formatos"""
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Setup
        page.goto(app_url)
        # ... login ...
        
        # Llenar con parámetros
        page.locator("input[placeholder*='P. Unit']").first.fill(precio)
        page.locator("input[placeholder*='Cant']").first.fill(cantidad)
        
        # Validar resultado
        total = page.locator("input[label='Total']").first.input_value()
        assert total == esperado
        
        browser.close()
```

---

## Troubleshooting Común

### "Timeout waiting for selector"

```python
# Aumentar timeout
page.wait_for_selector("#element", timeout=10000)

# O usar try-except
try:
    page.wait_for_selector("#element", timeout=3000)
except TimeoutError:
    page.screenshot(path="timeout.png")
    # Inspeccionar qué hay en la página
    print(page.content()[:1000])
```

### "Element not interactable"

```python
# Scroll al elemento
page.locator("#element").scroll_into_view_if_needed()

# O usar keyboard
page.keyboard.press("Tab")
page.keyboard.press("Enter")
```

### "Input field not clearing"

```python
# Usar triple click + delete
input_field = page.locator("#input")
input_field.triple_click()
input_field.press("Delete")
input_field.fill("new_value")

# O usar Ctrl+A + Delete
input_field.press("Control+A")
input_field.press("Delete")
input_field.fill("new_value")
```

---

## Recursos

- [Playwright Documentation](https://playwright.dev/python/)
- [Playwright Locators API](https://playwright.dev/python/docs/api/class-locator)
- [Best Practices](https://playwright.dev/python/docs/best-practices)
