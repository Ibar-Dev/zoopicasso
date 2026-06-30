"""
E2E Tests para Flujo de Generación de Facturas
===============================================

Tests E2E que verifican el flujo completo de generación de facturas usando Playwright:
- Login
- Completar datos de cliente (opcional)
- Agregar líneas de factura
- Validar totales
- Generar factura
- Verificar archivo guardado
"""

import pytest
from pathlib import Path
from datetime import date
import time
import json

# Importar Playwright
from playwright.sync_api import sync_playwright, expect

# Importar helpers
from tests.helpers import DBHelper, FileHelper
from tests.fixtures.test_data import TEST_DATA_VALIDATIONS


@pytest.fixture
def db_helper():
    """Proporciona helper de BD"""
    db_path = Path(__file__).parent.parent.parent / "data" / "ventas.db"
    return DBHelper(db_path)


@pytest.fixture
def file_helper():
    """Proporciona helper de archivos"""
    return FileHelper()


@pytest.fixture
def app_url():
    """URL base de la aplicación web"""
    return "http://localhost:8000"


class TestInvoiceGenerationFlow:
    """Tests del flujo completo de generación de facturas"""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self, db_helper):
        """Setup y teardown de cada test"""
        db_helper.limpiar_facturas_hoy()
        yield
        db_helper.limpiar_facturas_hoy()
    
    def test_1_login_page_loads(self, app_url):
        """Test 1: Página de login carga correctamente
        
        Criterio: La página de login debe estar disponible y contener campos de usuario/password
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            page.goto(app_url, wait_until="networkidle")
            
            # Verificar que hay campos de login
            usuario_field = page.locator("#usuario")
            password_field = page.locator("#password")
            login_btn = page.locator("button:has-text('Entrar')")
            
            expect(usuario_field).to_be_visible()
            expect(password_field).to_be_visible()
            expect(login_btn).to_be_visible()
            
            browser.close()
    
    def test_2_login_with_valid_credentials(self, app_url):
        """Test 2: Login con credenciales válidas
        
        Criterio: Usuario Giselle con contraseña correcta debe acceder a la app
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            page.goto(app_url, wait_until="networkidle")
            
            # Rellenar credenciales
            page.fill("#usuario", "Giselle")
            page.fill("#password", "123456")
            
            # Click en botón Entrar
            page.click("button:has-text('Entrar')")
            
            # Esperar a que cargue la app principal
            page.wait_for_selector("#btn-generar", timeout=5000)
            
            # Verificar que estamos en la app
            assert page.locator("text=Generador de Facturas").is_visible()
            assert page.locator("#btn-generar").is_visible()
            
            browser.close()
    
    def test_3_login_with_invalid_credentials(self, app_url):
        """Test 3: Login con credenciales inválidas
        
        Criterio: Credenciales incorrectas deben mostrar error
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            page.goto(app_url, wait_until="networkidle")
            
            # Rellenar credenciales incorrectas
            page.fill("#usuario", "usuario_incorrecto")
            page.fill("#password", "password_incorrecta")
            
            # Click en botón Entrar
            page.click("button:has-text('Entrar')")
            
            # Esperar a mensaje de error
            time.sleep(1)
            
            # Verificar mensaje de error
            error_msg = page.locator("text=Usuario o contraseña incorrectos")
            assert error_msg.is_visible()
            
            browser.close()
    
    def test_4_add_invoice_lines(self, app_url):
        """Test 4: Agregar líneas de factura
        
        Criterio: Debe permitir agregar múltiples líneas con concepto, precio, cantidad, categoría
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Login
            page.goto(app_url, wait_until="networkidle")
            page.fill("#usuario", "Giselle")
            page.fill("#password", "123456")
            page.click("button:has-text('Entrar')")
            page.wait_for_selector("#btn-generar", timeout=5000)
            
            # Rellenar primera línea (debería haber una por defecto)
            concepto_inputs = page.locator("input[placeholder*='Concepto']")
            precio_inputs = page.locator("input[placeholder*='P. Unit']")
            cantidad_inputs = page.locator("input[placeholder*='Cant']")
            
            # Seleccionar el primer concepto y rellenar
            concepto_inputs.first.fill("Atención veterinaria - Perro")
            precio_inputs.first.fill("50.00")
            cantidad_inputs.first.fill("1")
            
            # Esperar a que se actualice el total
            time.sleep(0.5)
            
            # Verificar que se calcló el total correctamente
            total_fields = page.locator("input[label='Total']")
            assert total_fields.first.input_value() == "50.00"
            
            # Agregar segunda línea
            page.click("button:has-text('+ Añadir línea')")
            time.sleep(0.5)
            
            # Verificar que ahora hay 2 líneas
            concepto_inputs = page.locator("input[placeholder*='Concepto']")
            assert concepto_inputs.count() >= 2
            
            browser.close()
    
    def test_5_fill_client_info(self, app_url):
        """Test 5: Rellenar datos del cliente (opcional)
        
        Criterio: Debe permitir ingresar nombre y NIF del cliente
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Login
            page.goto(app_url, wait_until="networkidle")
            page.fill("#usuario", "Giselle")
            page.fill("#password", "123456")
            page.click("button:has-text('Entrar')")
            page.wait_for_selector("#btn-generar", timeout=5000)
            
            # Rellenar datos del cliente
            page.fill("#cliente_nombre", "Veterinaria San Carlos")
            page.fill("#cliente_nif", "B12345678")
            
            # Verificar que los datos se guardaron
            assert page.locator("#cliente_nombre").input_value() == "Veterinaria San Carlos"
            assert page.locator("#cliente_nif").input_value() == "B12345678"
            
            browser.close()
    
    def test_6_category_selection(self, app_url):
        """Test 6: Seleccionar categoría para cada línea
        
        Criterio: Debe permitir seleccionar categoría de la lista desplegable
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Login
            page.goto(app_url, wait_until="networkidle")
            page.fill("#usuario", "Giselle")
            page.fill("#password", "123456")
            page.click("button:has-text('Entrar')")
            page.wait_for_selector("#btn-generar", timeout=5000)
            
            # Llenar línea de factura
            concepto_inputs = page.locator("input[placeholder*='Concepto']")
            precio_inputs = page.locator("input[placeholder*='P. Unit']")
            
            concepto_inputs.first.fill("Servicio veterinario")
            precio_inputs.first.fill("75.50")
            
            # Seleccionar categoría (dropdown)
            page.click("div[label='Categoría']")
            page.wait_for_selector("text=perro")
            page.click("text=perro")
            
            # Verificar que se seleccionó
            time.sleep(0.5)
            
            browser.close()
    
    def test_7_total_calculation(self, app_url):
        """Test 7: Cálculo correcto de totales
        
        Criterio: El total debe calcularse como cantidad * precio
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Login
            page.goto(app_url, wait_until="networkidle")
            page.fill("#usuario", "Giselle")
            page.fill("#password", "123456")
            page.click("button:has-text('Entrar')")
            page.wait_for_selector("#btn-generar", timeout=5000)
            
            # Rellenar con cantidad > 1
            concepto_inputs = page.locator("input[placeholder*='Concepto']")
            precio_inputs = page.locator("input[placeholder*='P. Unit']")
            cantidad_inputs = page.locator("input[placeholder*='Cant']")
            
            concepto_inputs.first.fill("Alimento premium")
            precio_inputs.first.fill("25.00")
            cantidad_inputs.first.fill("3")
            
            time.sleep(0.5)
            
            # Verificar total = 25 * 3 = 75
            total_fields = page.locator("input[label='Total']")
            assert total_fields.first.input_value() == "75.00"
            
            # Verificar total general en la UI
            grand_total = page.locator("text=/TOTAL:.*75\.00/")
            assert grand_total.count() > 0
            
            browser.close()
    
    def test_8_generate_invoice_success(self, app_url):
        """Test 8: Generar factura exitosamente
        
        Criterio: Click en botón "Generar Factura" debe crear la factura y mostrar confirmación
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Login
            page.goto(app_url, wait_until="networkidle")
            page.fill("#usuario", "Giselle")
            page.fill("#password", "123456")
            page.click("button:has-text('Entrar')")
            page.wait_for_selector("#btn-generar", timeout=5000)
            
            # Rellenar datos de la factura
            concepto_inputs = page.locator("input[placeholder*='Concepto']")
            precio_inputs = page.locator("input[placeholder*='P. Unit']")
            
            concepto_inputs.first.fill("Consulta veterinaria")
            precio_inputs.first.fill("100.00")
            
            # Seleccionar categoría
            page.click("div[label='Categoría']")
            page.wait_for_selector("text=perro", timeout=5000)
            page.click("text=perro")
            
            time.sleep(0.5)
            
            # Click en Generar Factura
            page.click("#btn-generar")
            
            # Esperar a que aparezca el diálogo de impresión o confirmación
            page.wait_for_selector("text=Imprimir ticket", timeout=10000)
            
            # Verificar que el diálogo está visible
            assert page.locator("text=Imprimir ticket").is_visible()
            
            browser.close()
    
    def test_9_cancel_invoice_generation(self, app_url):
        """Test 9: Cancelar generación sin imprimir
        
        Criterio: Click en "No" debe cerrar diálogo y resetear el formulario
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Login
            page.goto(app_url, wait_until="networkidle")
            page.fill("#usuario", "Giselle")
            page.fill("#password", "123456")
            page.click("button:has-text('Entrar')")
            page.wait_for_selector("#btn-generar", timeout=5000)
            
            # Rellenar y generar factura
            concepto_inputs = page.locator("input[placeholder*='Concepto']")
            precio_inputs = page.locator("input[placeholder*='P. Unit']")
            
            concepto_inputs.first.fill("Servicio")
            precio_inputs.first.fill("50.00")
            
            # Seleccionar categoría
            page.click("div[label='Categoría']")
            page.wait_for_selector("text=gato", timeout=5000)
            page.click("text=gato")
            
            time.sleep(0.5)
            page.click("#btn-generar")
            
            # Esperar diálogo
            page.wait_for_selector("text=Imprimir ticket", timeout=10000)
            
            # Click en No
            page.click("button:has-text('No')")
            
            time.sleep(0.5)
            
            # Verificar que el formulario fue reseteado
            concepto_inputs = page.locator("input[placeholder*='Concepto']")
            assert concepto_inputs.first.input_value() == ""
            
            browser.close()
    
    def test_10_validate_required_fields(self, app_url):
        """Test 10: Validar campos obligatorios
        
        Criterio: No debe permitir generar factura sin concepto o categoría
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Login
            page.goto(app_url, wait_until="networkidle")
            page.fill("#usuario", "Giselle")
            page.fill("#password", "123456")
            page.click("button:has-text('Entrar')")
            page.wait_for_selector("#btn-generar", timeout=5000)
            
            # Intentar generar sin llenar nada
            page.click("#btn-generar")
            
            time.sleep(1)
            
            # Verificar que aparece error
            error_msg = page.locator("text=Selecciona una categoría")
            assert error_msg.is_visible()
            
            browser.close()
    
    def test_11_price_format_validation(self, app_url):
        """Test 11: Validar formato de precio
        
        Criterio: Solo aceptar formato EUR válido (25.50, 25,50, 100, 0.99)
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Login
            page.goto(app_url, wait_until="networkidle")
            page.fill("#usuario", "Giselle")
            page.fill("#password", "123456")
            page.click("button:has-text('Entrar')")
            page.wait_for_selector("#btn-generar", timeout=5000)
            
            # Probar varios formatos de precio
            precio_inputs = page.locator("input[placeholder*='P. Unit']")
            
            # Formato válido con punto
            precio_inputs.first.fill("25.50")
            time.sleep(0.3)
            concepto_inputs = page.locator("input[placeholder*='Concepto']")
            concepto_inputs.first.fill("Test")
            time.sleep(0.3)
            total_fields = page.locator("input[label='Total']")
            assert total_fields.first.input_value() == "25.50"
            
            # Formato válido con coma
            precio_inputs.first.fill("25,50")
            time.sleep(0.3)
            assert total_fields.first.input_value() == "25.50"
            
            browser.close()
    
    def test_12_daily_accumulation(self, app_url):
        """Test 12: Acumulación diaria de ventas
        
        Criterio: Las ventas deben acumularse en el contador diario
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Login
            page.goto(app_url, wait_until="networkidle")
            page.fill("#usuario", "Giselle")
            page.fill("#password", "123456")
            page.click("button:has-text('Entrar')")
            page.wait_for_selector("#btn-generar", timeout=5000)
            
            # Verificar totales iniciales en cero
            acumulado_label = page.locator("text=ACUMULADO DEL DÍA:")
            total_label = page.locator("text=0.00 €")
            
            assert total_label.count() > 0
            
            # TODO: Agregar lógica para generar factura y verificar acumulado
            
            browser.close()


class TestInvoiceFileGeneration:
    """Tests de generación de archivos de factura"""
    
    def test_invoice_file_created(self, app_url, file_helper):
        """Test: Verificar que el archivo de factura se crea correctamente
        
        Criterio: Debe crearse archivo .xlsx con el nombre correcto
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Login y generar factura
            page.goto(app_url, wait_until="networkidle")
            page.fill("#usuario", "Giselle")
            page.fill("#password", "123456")
            page.click("button:has-text('Entrar')")
            page.wait_for_selector("#btn-generar", timeout=5000)
            
            # Rellenar factura
            concepto_inputs = page.locator("input[placeholder*='Concepto']")
            precio_inputs = page.locator("input[placeholder*='P. Unit']")
            
            concepto_inputs.first.fill("Test Invoice")
            precio_inputs.first.fill("99.99")
            
            # Seleccionar categoría
            page.click("div[label='Categoría']")
            page.wait_for_selector("text=perro", timeout=5000)
            page.click("text=perro")
            
            time.sleep(0.5)
            
            # Generar
            page.click("#btn-generar")
            page.wait_for_selector("text=Imprimir ticket", timeout=10000)
            
            # Cerrar diálogo sin imprimir
            page.click("button:has-text('No')")
            
            time.sleep(1)
            
            # TODO: Verificar que el archivo existe
            
            browser.close()
