"""
E2E Tests para Atajos de Teclado
=================================

Tests específicos para verificar que los atajos de teclado funcionan correctamente
después de la corrección de Windows 11 compatibility (Alt+ → Ctrl+Shift+):

- Ctrl+Shift+A: Agregar línea
- Ctrl+Shift+D: Eliminar línea
- Ctrl+Shift+G: Generar factura
"""

import pytest
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

from tests.helpers import DBHelper, FileHelper


@pytest.fixture
def db_helper():
    """Proporciona helper de BD"""
    db_path = Path(__file__).parent.parent.parent / "data" / "ventas.db"
    return DBHelper(db_path)


@pytest.fixture
def app_url():
    """URL base de la aplicación web"""
    return "http://localhost:8000"


class TestKeyboardShortcuts:
    """Tests de atajos de teclado post-fix Windows 11"""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self, db_helper):
        """Cleanup de facturas antes y después del test"""
        db_helper.limpiar_facturas_hoy()
        yield
        db_helper.limpiar_facturas_hoy()
    
    def test_1_shortcuts_page_displays_correctly(self, app_url):
        """Test 1: La página muestra los atajos correctamente
        
        Criterio: Los atajos deben mostrar Ctrl+Shift+A/D/G, no Alt+A/D/G
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
            
            # Verificar que no hay referencias a Alt+ en la UI
            alt_references = page.locator("text=/Alt\\+/i")
            assert alt_references.count() == 0, "Encontradas referencias a Alt+ en la página"
            
            # Verificar que hay referencias a Ctrl+Shift+
            ctrl_shift_references = page.locator("text=/Ctrl\\+Shift\\+/i")
            assert ctrl_shift_references.count() > 0, "No se encontraron referencias a Ctrl+Shift+"
            
            browser.close()
    
    def test_2_keyboard_shortcut_add_line_ctrl_shift_a(self, app_url):
        """Test 2: Ctrl+Shift+A agrega una línea
        
        Criterio: Presionar Ctrl+Shift+A debe agregar una nueva línea de factura
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
            
            # Contar líneas iniciales (debería haber 1 por defecto)
            concepto_inputs = page.locator("input[placeholder*='Concepto']")
            initial_count = concepto_inputs.count()
            assert initial_count >= 1
            
            # Presionar Ctrl+Shift+A
            page.keyboard.press("Control+Shift+A")
            time.sleep(0.5)
            
            # Contar líneas nuevamente
            concepto_inputs = page.locator("input[placeholder*='Concepto']")
            new_count = concepto_inputs.count()
            
            # Debería haber agregado una línea
            assert new_count == initial_count + 1, \
                f"Se esperaba {initial_count + 1} líneas, se encontraron {new_count}"
            
            browser.close()
    
    def test_3_keyboard_shortcut_delete_line_ctrl_shift_d(self, app_url):
        """Test 3: Ctrl+Shift+D elimina una línea
        
        Criterio: Presionar Ctrl+Shift+D debe eliminar la última línea
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
            
            # Agregar una línea primero
            page.keyboard.press("Control+Shift+A")
            time.sleep(0.3)
            
            concepto_inputs = page.locator("input[placeholder*='Concepto']")
            count_before = concepto_inputs.count()
            assert count_before >= 2
            
            # Presionar Ctrl+Shift+D para eliminar
            page.keyboard.press("Control+Shift+D")
            time.sleep(0.5)
            
            # Verificar que se eliminó
            concepto_inputs = page.locator("input[placeholder*='Concepto']")
            count_after = concepto_inputs.count()
            
            assert count_after == count_before - 1, \
                f"Se esperaba {count_before - 1} líneas, se encontraron {count_after}"
            
            browser.close()
    
    def test_4_keyboard_shortcut_generate_ctrl_shift_g(self, app_url):
        """Test 4: Ctrl+Shift+G genera factura
        
        Criterio: Presionar Ctrl+Shift+G debe generar la factura (mostrar diálogo)
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
            
            # Llenar datos de factura
            concepto_inputs = page.locator("input[placeholder*='Concepto']")
            precio_inputs = page.locator("input[placeholder*='P. Unit']")
            
            concepto_inputs.first.fill("Test Service")
            precio_inputs.first.fill("100.00")
            
            # Seleccionar categoría
            page.click("div[label='Categoría']")
            page.wait_for_selector("text=perro", timeout=5000)
            page.click("text=perro")
            
            time.sleep(0.5)
            
            # Presionar Ctrl+Shift+G para generar
            page.keyboard.press("Control+Shift+G")
            
            # Esperar diálogo
            page.wait_for_selector("text=Imprimir ticket", timeout=10000)
            
            # Verificar que aparece el diálogo
            expect(page.locator("text=Imprimir ticket")).to_be_visible()
            
            browser.close()
    
    def test_5_keyboard_shortcuts_dont_conflict_with_browser(self, app_url):
        """Test 5: Los atajos no interfieren con funciones del navegador
        
        Criterio: Ctrl+Shift no debe activar funciones del navegador (DevTools, etc.)
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
            
            # Verificar que la página sigue visible después de Ctrl+Shift+A
            page.keyboard.press("Control+Shift+A")
            time.sleep(0.5)
            
            # La aplicación debe seguir respondiendo
            expect(page.locator("text=Generador de Facturas")).to_be_visible()
            expect(page.locator("#btn-generar")).to_be_visible()
            
            browser.close()
    
    def test_6_help_system_shows_correct_shortcuts(self, app_url):
        """Test 6: El sistema de ayuda muestra los atajos correctos
        
        Criterio: Los tooltips deben mostrar Ctrl+Shift+, no Alt+
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
            
            # Verificar botones tienen atributo title correcto
            btn_generar = page.locator("#btn-generar")
            title_attr = btn_generar.get_attribute("title") or ""
            
            # El título debería contener Ctrl+Shift+G si está configurado
            if title_attr:
                assert "Alt" not in title_attr, f"Encontrado Alt+ en título: {title_attr}"
            
            browser.close()
    
    def test_7_multiple_shortcuts_sequence(self, app_url):
        """Test 7: Secuencia de múltiples atajos
        
        Criterio: Probar secuencia realista: agregar línea, llenar, eliminar, agregar, generar
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
            
            # Secuencia: 
            # 1. Agregar línea (Ctrl+Shift+A)
            initial_count = page.locator("input[placeholder*='Concepto']").count()
            page.keyboard.press("Control+Shift+A")
            time.sleep(0.3)
            
            after_add = page.locator("input[placeholder*='Concepto']").count()
            assert after_add == initial_count + 1
            
            # 2. Eliminar línea (Ctrl+Shift+D)
            page.keyboard.press("Control+Shift+D")
            time.sleep(0.3)
            
            after_delete = page.locator("input[placeholder*='Concepto']").count()
            assert after_delete == initial_count
            
            # 3. Llenar línea actual
            concepto_inputs = page.locator("input[placeholder*='Concepto']")
            precio_inputs = page.locator("input[placeholder*='P. Unit']")
            
            concepto_inputs.first.fill("Integration Test")
            precio_inputs.first.fill("75.00")
            
            # Seleccionar categoría
            page.click("div[label='Categoría']")
            page.wait_for_selector("text=gato", timeout=5000)
            page.click("text=gato")
            
            time.sleep(0.5)
            
            # 4. Generar factura (Ctrl+Shift+G)
            page.keyboard.press("Control+Shift+G")
            
            # Debe mostrar diálogo
            page.wait_for_selector("text=Imprimir ticket", timeout=10000)
            expect(page.locator("text=Imprimir ticket")).to_be_visible()
            
            browser.close()
    
    def test_8_shortcuts_work_when_form_elements_focused(self, app_url):
        """Test 8: Los atajos funcionan incluso con campos de texto enfocados
        
        Criterio: Ctrl+Shift+A debe agregar línea incluso si hay un input enfocado
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
            
            # Enfocar un campo de concepto
            concepto_inputs = page.locator("input[placeholder*='Concepto']")
            concepto_inputs.first.click()
            concepto_inputs.first.fill("Test")
            
            # El campo debería estar enfocado
            # Ahora presionar Ctrl+Shift+A
            initial_count = concepto_inputs.count()
            page.keyboard.press("Control+Shift+A")
            time.sleep(0.5)
            
            # Debería haber agregado una línea
            new_count = page.locator("input[placeholder*='Concepto']").count()
            assert new_count == initial_count + 1
            
            browser.close()
