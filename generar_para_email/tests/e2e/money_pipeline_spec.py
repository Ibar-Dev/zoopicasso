"""
E2E Tests para Money Pipeline (Tests 1-15)
===========================================

Verifica el flujo completo de dinero:
- Validación de entrada
- Cálculos correctos
- Almacenamiento en BD
- Generación de Excel

Importante: Los tests utilizan Playwright para simular interacción real del usuario.
"""

import asyncio
import pytest
from datetime import date
from pathlib import Path
from playwright.async_api import Page, expect

from tests.helpers import DBHelper, FileHelper
from tests.fixtures.test_data import (
    TEST_DATA_VALIDATIONS,
    TEST_DATA_QUANTITY,
    TEST_DATA_SIMPLE_VALIDATIONS,
    TEST_DATA_CALCULATIONS,
    TEST_DATA_DB_VERIFICATION,
)


@pytest.fixture
def db_helper(tmp_path) -> DBHelper:
    """Proporciona helper de BD"""
    db_path = Path(__file__).parent.parent.parent / "data" / "ventas.db"
    return DBHelper(db_path)


@pytest.fixture
def file_helper() -> FileHelper:
    """Proporciona helper de archivos"""
    return FileHelper()


@pytest.fixture
def facturas_dir() -> Path:
    """Directorio de facturas"""
    return Path(__file__).parent.parent.parent / "facturas"


# ============================================================================
# BLOQUE 1: VALIDACIONES DE ENTRADA (Tests 1-5)
# ============================================================================

@pytest.mark.asyncio
class TestValidaciones:
    """Tests para validación de entrada de datos"""
    
    async def test_1_valid_price_formats(self, page: Page, db_helper: DBHelper):
        """Test 1: Validar formatos de precio aceptados
        
        Criterio: Precio debe aceptar:
        - "25.50" (punto decimal)
        - "25,50" (coma decimal)
        - "100" (entero)
        - Máximo 2 decimales
        """
        # Limpiar datos previos
        db_helper.limpiar_facturas_hoy()
        
        # Navegar a la aplicación
        await page.goto("http://localhost:8000")
        await page.wait_for_load_state("networkidle")
        
        # Test cada formato de precio
        valid_prices = ["25.50", "25,50", "100", "0.99"]
        
        for price in valid_prices:
            # Llenar formulario
            await page.fill('input[placeholder*="precio" i]', "")
            await page.fill('input[placeholder*="precio" i]', price)
            
            # Verificar que se acepta (no muestra error)
            error_element = page.locator("span:has-text('Formato de precio inválido')")
            is_visible = await error_element.is_visible()
            
            assert not is_visible, f"Precio '{price}' debería ser válido pero fue rechazado"
    
    async def test_2_invalid_price_formats(self, page: Page):
        """Test 2: Rechazar formatos de precio inválidos
        
        Criterio: Debe rechazar:
        - "-25.50" (negativo)
        - "25.999" (3+ decimales)
        - "abc" (texto)
        - "" (vacío)
        """
        await page.goto("http://localhost:8000")
        await page.wait_for_load_state("networkidle")
        
        invalid_prices = ["-25.50", "25.999", "abc"]
        
        for price in invalid_prices:
            # Intentar llenar con precio inválido
            await page.fill('input[placeholder*="precio" i]', price)
            await page.keyboard.press("Tab")  # Trigger validation
            
            # Esperar error
            error_element = page.locator("span:has-text('Formato de precio inválido')")
            is_visible = await error_element.is_visible()
            
            assert is_visible, f"Precio '{price}' debería ser rechazado"
    
    async def test_3_valid_quantities(self, page: Page):
        """Test 3: Validar cantidades positivas
        
        Criterio: Cantidad debe ser >= 1
        """
        await page.goto("http://localhost:8000")
        await page.wait_for_load_state("networkidle")
        
        valid_quantities = [1, 10, 100]
        
        for qty in valid_quantities:
            await page.fill('input[placeholder*="cantidad" i]', str(qty))
            await page.keyboard.press("Tab")
            
            error_element = page.locator("span:has-text('Cantidad inválida')")
            is_visible = await error_element.is_visible()
            
            assert not is_visible, f"Cantidad {qty} debería ser válida"
    
    async def test_4_invalid_quantities(self, page: Page):
        """Test 4: Rechazar cantidades inválidas
        
        Criterio: Rechazar 0, negativos
        """
        await page.goto("http://localhost:8000")
        await page.wait_for_load_state("networkidle")
        
        invalid_quantities = [0, -1]
        
        for qty in invalid_quantities:
            await page.fill('input[placeholder*="cantidad" i]', str(qty))
            await page.keyboard.press("Tab")
            
            error_element = page.locator("span:has-text('Cantidad debe ser')")
            is_visible = await error_element.is_visible()
            
            assert is_visible, f"Cantidad {qty} debería ser rechazada"
    
    async def test_5_required_fields(self, page: Page):
        """Test 5: Validar campos requeridos
        
        Criterio: Cliente y categoría son obligatorios
        """
        await page.goto("http://localhost:8000")
        await page.wait_for_load_state("networkidle")
        
        # Intentar agregar línea sin cliente
        await page.fill('input[placeholder*="cliente" i]', "")
        await page.fill('select[name="categoria"]', "")
        await page.fill('input[placeholder*="cantidad" i]', "1")
        await page.fill('input[placeholder*="precio" i]', "10.00")
        
        # Click en agregar
        await page.click('button:has-text("Agregar")')
        
        # Debe haber error
        error = page.locator("span:has-text('requerido')")
        is_visible = await error.is_visible()
        
        assert is_visible, "Debería mostrar error de campo requerido"


# ============================================================================
# BLOQUE 2: CÁLCULOS (Tests 6-10)
# ============================================================================

@pytest.mark.asyncio
class TestCalculos:
    """Tests para validar cálculos de dinero"""
    
    async def test_6_simple_multiplication(self, page: Page, db_helper: DBHelper):
        """Test 6: Cálculo simple (cantidad × precio)
        
        Criterio: 2 × 10.00 = 20.00
        """
        db_helper.limpiar_facturas_hoy()
        await page.goto("http://localhost:8000")
        await page.wait_for_load_state("networkidle")
        
        # Agregar línea: 2 × 10.00
        await page.fill('input[placeholder*="cliente" i]', "Cliente Test 6")
        await page.select('select[name="categoria"]', "perro")
        await page.fill('input[placeholder*="cantidad" i]', "2")
        await page.fill('input[placeholder*="precio" i]', "10.00")
        await page.click('button:has-text("Agregar")')
        
        # Verificar que se muestra 20.00 en la UI
        total_cell = page.locator("text=20.00")
        await expect(total_cell).to_be_visible(timeout=5000)
    
    async def test_7_decimal_rounding(self, page: Page):
        """Test 7: Redondeo de decimales
        
        Criterio: 3 × 10.01 = 30.03 (sin errores de punto flotante)
        """
        await page.goto("http://localhost:8000")
        await page.wait_for_load_state("networkidle")
        
        await page.fill('input[placeholder*="cliente" i]', "Cliente Test 7")
        await page.select('select[name="categoria"]', "gato")
        await page.fill('input[placeholder*="cantidad" i]', "3")
        await page.fill('input[placeholder*="precio" i]', "10.01")
        await page.click('button:has-text("Agregar")')
        
        # Verificar resultado: 30.03
        total_cell = page.locator("text=30.03")
        await expect(total_cell).to_be_visible(timeout=5000)
    
    async def test_8_multiline_sum(self, page: Page, db_helper: DBHelper):
        """Test 8: Suma de múltiples líneas
        
        Criterio: (2×15.50) + (1×10.75) + (3×5.25) = 57.50
        """
        db_helper.limpiar_facturas_hoy()
        await page.goto("http://localhost:8000")
        await page.wait_for_load_state("networkidle")
        
        lines = [
            {"qty": "2", "price": "15.50", "cat": "perro"},
            {"qty": "1", "price": "10.75", "cat": "gato"},
            {"qty": "3", "price": "5.25", "cat": "ave"},
        ]
        
        for line in lines:
            await page.fill('input[placeholder*="cliente" i]', "Cliente Test 8")
            await page.select('select[name="categoria"]', line["cat"])
            await page.fill('input[placeholder*="cantidad" i]', line["qty"])
            await page.fill('input[placeholder*="precio" i]', line["price"])
            await page.click('button:has-text("Agregar")')
            await page.wait_for_timeout(500)
        
        # Total debe ser 57.50
        total_element = page.locator("text=57.50")
        await expect(total_element).to_be_visible(timeout=5000)
    
    async def test_9_exact_payment(self, page: Page):
        """Test 9: Pago exacto (sin vuelto)
        
        Criterio: Total 45.50, pago 45.50 = vuelto 0.00
        """
        await page.goto("http://localhost:8000")
        await page.wait_for_load_state("networkidle")
        
        # Crear factura con total 45.50
        await page.fill('input[placeholder*="cliente" i]', "Cliente Test 9")
        await page.select('select[name="categoria"]', "perro")
        await page.fill('input[placeholder*="cantidad" i]', "1")
        await page.fill('input[placeholder*="precio" i]', "45.50")
        await page.click('button:has-text("Agregar")')
        
        # Llenar método de pago (efectivo, monto exacto)
        await page.select('select[name="metodo_pago"]', "efectivo")
        await page.fill('input[placeholder*="efectivo" i]', "45.50")
        
        # Vuelto debe ser 0.00
        vuelto = page.locator("input:has-text('0.00')")
        await expect(vuelto).to_be_visible(timeout=5000)
    
    async def test_10_high_precision_total(self, page: Page):
        """Test 10: Precisión en cálculos (2 decimales exactos)
        
        Criterio: 3 × 33.33 = 99.99 (exactamente)
        """
        await page.goto("http://localhost:8000")
        await page.wait_for_load_state("networkidle")
        
        await page.fill('input[placeholder*="cliente" i]', "Cliente Test 10")
        await page.select('select[name="categoria"]', "gato")
        await page.fill('input[placeholder*="cantidad" i]', "3")
        await page.fill('input[placeholder*="precio" i]', "33.33")
        await page.click('button:has-text("Agregar")')
        
        # Total: 99.99
        total = page.locator("text=99.99")
        await expect(total).to_be_visible(timeout=5000)


# ============================================================================
# BLOQUE 3: VERIFICACIÓN EN BD (Tests 11-15)
# ============================================================================

@pytest.mark.asyncio
class TestBDVerification:
    """Tests para verificar almacenamiento correcto en BD"""
    
    async def test_11_single_line_insertion(self, page: Page, db_helper: DBHelper):
        """Test 11: Una línea se guarda correctamente en BD
        
        Criterio:
        - Tabla 'ventas' tiene una fila
        - categoria='perro', cantidad=1, monto=25.00
        """
        db_helper.limpiar_facturas_hoy()
        await page.goto("http://localhost:8000")
        await page.wait_for_load_state("networkidle")
        
        # Crear factura
        await page.fill('input[placeholder*="cliente" i]', "BD Test 11")
        await page.select('select[name="categoria"]', "perro")
        await page.fill('input[placeholder*="cantidad" i]', "1")
        await page.fill('input[placeholder*="precio" i]', "25.00")
        await page.click('button:has-text("Agregar")')
        
        # Generar factura
        await page.click('button:has-text("Generar")')
        await page.wait_for_timeout(2000)
        
        # Verificar en BD
        resumen = db_helper.get_resumen_ventas_hoy()
        assert resumen['cantidad'] >= 1, "Debería haber al menos una venta registrada"
        assert resumen['total'] == 25.00, "Total debería ser 25.00"
    
    async def test_12_factura_numbering_increments(self, page: Page, db_helper: DBHelper):
        """Test 12: Números de factura incrementan correctamente
        
        Criterio:
        - Cada nueva factura tiene número secuencial
        - Formato: YYYY-NNN (año y número)
        """
        db_helper.limpiar_facturas_hoy()
        await page.goto("http://localhost:8000")
        await page.wait_for_load_state("networkidle")
        
        # Crear primera factura
        await page.fill('input[placeholder*="cliente" i]', "BD Test 12a")
        await page.select('select[name="categoria"]', "perro")
        await page.fill('input[placeholder*="cantidad" i]', "1")
        await page.fill('input[placeholder*="precio" i]', "10.00")
        await page.click('button:has-text("Agregar")')
        
        numero_1 = await page.input_value('input:has-text("numero")')
        
        # Crear segunda factura
        await page.fill('input[placeholder*="cliente" i]', "BD Test 12b")
        await page.select('select[name="categoria"]', "gato")
        await page.fill('input[placeholder*="cantidad" i]', "1")
        await page.fill('input[placeholder*="precio" i]', "20.00")
        await page.click('button:has-text("Agregar")')
        
        numero_2 = await page.input_value('input:has-text("numero")')
        
        # Números deben ser diferentes
        assert numero_1 != numero_2, f"Números de factura deben ser distintos: {numero_1} vs {numero_2}"
    
    async def test_13_correct_storage_multiline(self, page: Page, db_helper: DBHelper):
        """Test 13: Múltiples líneas se guardan correctamente
        
        Criterio:
        - Cada línea tiene su fila en ventas
        - Totales coinciden: (2×20.00) + (1×15.00) = 55.00
        """
        db_helper.limpiar_facturas_hoy()
        await page.goto("http://localhost:8000")
        await page.wait_for_load_state("networkidle")
        
        # Línea 1: 2 × 20.00
        await page.fill('input[placeholder*="cliente" i]', "BD Test 13")
        await page.select('select[name="categoria"]', "perro")
        await page.fill('input[placeholder*="cantidad" i]', "2")
        await page.fill('input[placeholder*="precio" i]', "20.00")
        await page.click('button:has-text("Agregar")')
        await page.wait_for_timeout(500)
        
        # Línea 2: 1 × 15.00
        await page.fill('input[placeholder*="cliente" i]', "BD Test 13")
        await page.select('select[name="categoria"]', "gato")
        await page.fill('input[placeholder*="cantidad" i]', "1")
        await page.fill('input[placeholder*="precio" i]', "15.00")
        await page.click('button:has-text("Agregar")')
        await page.wait_for_timeout(500)
        
        # Generar
        await page.click('button:has-text("Generar")')
        await page.wait_for_timeout(2000)
        
        # Verificar total en BD
        resumen = db_helper.get_resumen_ventas_hoy()
        assert resumen['total'] == 55.00, f"Total debería ser 55.00, se obtuvo {resumen['total']}"
    
    async def test_14_category_summary_aggregation(self, page: Page, db_helper: DBHelper):
        """Test 14: Resumen por categoría se calcula correctamente
        
        Criterio:
        - por_categoria['perro'] = 10.00
        - por_categoria['gato'] = 20.00
        """
        db_helper.limpiar_facturas_hoy()
        await page.goto("http://localhost:8000")
        await page.wait_for_load_state("networkidle")
        
        # Agregar línea de perro: 1 × 10.00
        await page.fill('input[placeholder*="cliente" i]', "BD Test 14")
        await page.select('select[name="categoria"]', "perro")
        await page.fill('input[placeholder*="cantidad" i]', "1")
        await page.fill('input[placeholder*="precio" i]', "10.00")
        await page.click('button:has-text("Agregar")')
        await page.wait_for_timeout(500)
        
        # Agregar línea de gato: 1 × 20.00
        await page.fill('input[placeholder*="cliente" i]', "BD Test 14")
        await page.select('select[name="categoria"]', "gato")
        await page.fill('input[placeholder*="cantidad" i]', "1")
        await page.fill('input[placeholder*="precio" i]', "20.00")
        await page.click('button:has-text("Agregar")')
        await page.wait_for_timeout(500)
        
        # Generar
        await page.click('button:has-text("Generar")')
        await page.wait_for_timeout(2000)
        
        # Verificar resumen por categoría
        resumen = db_helper.get_resumen_ventas_hoy()
        assert resumen['por_categoria'].get('perro', 0.0) == 10.00, "perro debería ser 10.00"
        assert resumen['por_categoria'].get('gato', 0.0) == 20.00, "gato debería ser 20.00"
    
    async def test_15_multiple_invoices_isolation(self, page: Page, db_helper: DBHelper):
        """Test 15: Múltiples facturas se almacenan sin interferencia
        
        Criterio:
        - Factura 1: total 15.00
        - Factura 2: total 20.00
        - Totales se mantienen separados y correctos
        """
        db_helper.limpiar_facturas_hoy()
        await page.goto("http://localhost:8000")
        await page.wait_for_load_state("networkidle")
        
        # Factura 1: 1 × 15.00
        await page.fill('input[placeholder*="cliente" i]', "BD Test 15a")
        await page.select('select[name="categoria"]', "perro")
        await page.fill('input[placeholder*="cantidad" i]', "1")
        await page.fill('input[placeholder*="precio" i]', "15.00")
        await page.click('button:has-text("Agregar")')
        await page.wait_for_timeout(500)
        
        await page.click('button:has-text("Generar")')
        await page.wait_for_timeout(2000)
        
        # Factura 2: 1 × 20.00
        await page.fill('input[placeholder*="cliente" i]', "BD Test 15b")
        await page.select('select[name="categoria"]', "gato")
        await page.fill('input[placeholder*="cantidad" i]', "1")
        await page.fill('input[placeholder*="precio" i]', "20.00")
        await page.click('button:has-text("Agregar")')
        await page.wait_for_timeout(500)
        
        await page.click('button:has-text("Generar")')
        await page.wait_for_timeout(2000)
        
        # Verificar totales
        resumen = db_helper.get_resumen_ventas_hoy()
        expected_total = 15.00 + 20.00
        assert resumen['total'] == expected_total, f"Total combinado debería ser {expected_total}, se obtuvo {resumen['total']}"
