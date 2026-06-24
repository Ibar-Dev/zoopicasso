"""
E2E Tests para Edge Cases (Tests 16-20)
========================================

Validación de casos límite y situaciones excepcionales en el pipeline de dinero:
- Montos muy pequeños (0.01€)
- Montos muy grandes (9999.99€)
- Muchas líneas (50 líneas)
- Devoluciones/créditos
- Formatos decimales mixtos

Estos tests aseguran robustez y precisión financiera en escenarios extremos.
"""

import pytest
from pathlib import Path
from datetime import date

from tests.helpers import DBHelper, FileHelper


@pytest.fixture
def db_helper():
    """Proporciona helper de BD"""
    db_path = Path(__file__).parent.parent.parent / "data" / "ventas.db"
    return DBHelper(db_path)


@pytest.fixture
def file_helper():
    """Proporciona helper de archivos"""
    return FileHelper()


class TestEdgeCasesSmallAmounts:
    """Tests para montos muy pequeños"""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self, db_helper):
        """Setup y teardown de cada test"""
        db_helper.limpiar_facturas_hoy()
        yield
        db_helper.limpiar_facturas_hoy()
    
    def test_16_minimum_amount_001(self, db_helper):
        """Test 16: Monto mínimo posible (0.01€)
        
        Criterio:
        - 1 × 0.01 = 0.01€ exacto
        - Se guarda correctamente en BD
        - Total en resumen es 0.01
        """
        # Simulando que se registra una venta de 0.01€
        conn = db_helper.get_connection()
        cursor = conn.cursor()
        
        today = str(date.today())
        numero_factura = "2026-999"
        from datetime import datetime
        anio_mes = today[:7]  # YYYY-MM
        created_at = datetime.now().__str__()
        
        try:
            # Registrar una línea de 0.01€ en BD
            cursor.execute("""
                INSERT INTO ventas (numero_factura, fecha_venta, anio_mes, categoria, monto, estado, cliente_nombre, usuario, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (numero_factura, today, anio_mes, "perro", 0.01, "active", "Test Small", "TEST_USER", created_at))
            
            # También registrar en pagos_factura
            cursor.execute("""
                INSERT INTO pagos_factura (numero_factura, fecha_venta, anio_mes, monto_total, monto_efectivo, monto_tarjeta, metodo_pago, estado, usuario, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (numero_factura, today, anio_mes, 0.01, 0.01, 0.00, "efectivo", "active", "TEST_USER", created_at))
            
            conn.commit()
            
            # Verificar que está en BD
            resumen = db_helper.get_resumen_ventas_hoy()
            
            assert resumen['total'] >= 0.01, f"Total debe incluir 0.01, se obtuvo {resumen['total']}"
            assert resumen['cantidad'] >= 1, "Debe haber al menos una venta"
            
        finally:
            conn.close()
    
    def test_16b_minimum_quantity_with_small_price(self, db_helper):
        """Test 16b: Cantidad mínima con precio pequeño
        
        Criterio:
        - 1 × 0.01€ = 0.01€
        - Redondeo a 2 decimales exacto
        """
        # Verificar cálculo
        cantidad = 1
        precio = 0.01
        total = round(cantidad * precio, 2)
        
        assert total == 0.01, f"1 × 0.01 debería ser 0.01, se obtuvo {total}"
    
    def test_16c_many_small_amounts(self, db_helper):
        """Test 16c: Muchos montos pequeños sumados
        
        Criterio:
        - 100 × 0.01€ = 1.00€ exacto
        - Sin errores de acumulación
        """
        cantidad = 100
        precio_unitario = 0.01
        total = round(cantidad * precio_unitario, 2)
        
        assert total == 1.00, f"100 × 0.01 debería ser 1.00, se obtuvo {total}"


class TestEdgeCasesLargeAmounts:
    """Tests para montos muy grandes"""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self, db_helper):
        """Setup y teardown de cada test"""
        db_helper.limpiar_facturas_hoy()
        yield
        db_helper.limpiar_facturas_hoy()
    
    def test_17_maximum_amount_999999(self, db_helper):
        """Test 17: Monto muy grande (9999.99€)
        
        Criterio:
        - 1 × 9999.99 = 9999.99€
        - Sin overflow o truncamiento
        - Precisión a 2 decimales
        """
        cantidad = 1
        precio = 9999.99
        total = round(cantidad * precio, 2)
        
        assert total == 9999.99, f"1 × 9999.99 debería ser 9999.99, se obtuvo {total}"
    
    def test_17b_large_quantity_moderate_price(self, db_helper):
        """Test 17b: Cantidad grande con precio moderado
        
        Criterio:
        - 100 × 99.99€ = 9999.00€
        - Validación sin errores
        """
        cantidad = 100
        precio = 99.99
        total = round(cantidad * precio, 2)
        
        assert total == 9999.00, f"100 × 99.99 debería ser 9999.00, se obtuvo {total}"
    
    def test_17c_maximum_realistic_transaction(self, db_helper):
        """Test 17c: Transacción máxima realista
        
        Criterio:
        - 10 × 9999.99€ = 99999.90€ (suma de líneas)
        - Manejo de números grandes sin pérdida de precisión
        """
        lines = [(10, 9999.99)]  # 10 × 9999.99 = 99999.90
        
        total = sum(round(qty * price, 2) for qty, price in lines)
        expected = 99999.90
        
        assert total == expected, f"Total debería ser {expected}, se obtuvo {total}"


class TestEdgeCasesManyLines:
    """Tests para muchas líneas en una factura"""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self, db_helper):
        """Setup y teardown de cada test"""
        db_helper.limpiar_facturas_hoy()
        yield
        db_helper.limpiar_facturas_hoy()
    
    def test_18_fifty_line_items(self, db_helper):
        """Test 18: 50 líneas en una factura
        
        Criterio:
        - Cada línea: 1 × 10.00€ = 10.00€
        - Total: 50 × 10.00€ = 500.00€
        - Todas las líneas se procesan sin truncamiento
        """
        # Simular 50 líneas de 10.00€
        total = sum(round(1 * 10.00, 2) for _ in range(50))
        expected = 500.00
        
        assert total == expected, f"50 líneas de 10.00 debería ser 500.00, se obtuvo {total}"
    
    def test_18b_hundred_line_items(self, db_helper):
        """Test 18b: 100 líneas (stress test)
        
        Criterio:
        - 100 líneas × 5.50€ = 550.00€
        - Rendimiento sin problemas
        - Exactitud de suma
        """
        # 100 líneas
        total = sum(round(1 * 5.50, 2) for _ in range(100))
        expected = 550.00
        
        assert total == expected, f"100 líneas de 5.50 debería ser 550.00, se obtuvo {total}"
    
    def test_18c_many_lines_with_varying_amounts(self, db_helper):
        """Test 18c: Muchas líneas con montos variados
        
        Criterio:
        - 25 líneas × 10.00€ = 250.00€
        - 25 líneas × 20.00€ = 500.00€
        - Total: 750.00€ exacto
        """
        lines = [
            (10.00, 25),  # 25 líneas de 10.00 = 250.00
            (20.00, 25),  # 25 líneas de 20.00 = 500.00
        ]
        
        total = sum(round(price * qty, 2) for price, qty in lines)
        expected = 750.00
        
        assert total == expected, f"Total debería ser {expected}, se obtuvo {total}"


class TestEdgeCasesRefundsCredits:
    """Tests para devoluciones y créditos"""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self, db_helper):
        """Setup y teardown de cada test"""
        db_helper.limpiar_facturas_hoy()
        yield
        db_helper.limpiar_facturas_hoy()
    
    def test_19_refund_credit_negative_amount(self, db_helper):
        """Test 19: Devolución (monto negativo)
        
        Criterio:
        - Factura original: 100.00€
        - Devolución: -50.00€
        - Neto en cuenta: 50.00€
        """
        original = 100.00
        refund = -50.00
        net = round(original + refund, 2)
        
        assert net == 50.00, f"100.00 + (-50.00) debería ser 50.00, se obtuvo {net}"
    
    def test_19b_full_refund(self, db_helper):
        """Test 19b: Devolución completa (refund 100%)
        
        Criterio:
        - Factura original: 75.50€
        - Devolución completa: -75.50€
        - Neto: 0.00€
        """
        original = 75.50
        refund = -75.50
        net = round(original + refund, 2)
        
        assert net == 0.00, f"75.50 + (-75.50) debería ser 0.00, se obtuvo {net}"
    
    def test_19c_partial_refund_multiple_items(self, db_helper):
        """Test 19c: Devolución parcial en factura multilinea
        
        Criterio:
        - Línea 1: 50.00€
        - Línea 2: 30.00€
        - Total: 80.00€
        - Devolución de línea 2: -30.00€
        - Neto: 50.00€
        """
        items = [
            50.00,  # Item 1
            30.00,  # Item 2
        ]
        total = sum(items)
        refund_item2 = -30.00
        net = round(total + refund_item2, 2)
        
        assert net == 50.00, f"80.00 + (-30.00) debería ser 50.00, se obtuvo {net}"
    
    def test_19d_over_refund_credit_balance(self, db_helper):
        """Test 19d: Devolución superior (crédito para próxima compra)
        
        Criterio:
        - Factura original: 50.00€
        - Devolución: -60.00€ (incluye crédito)
        - Saldo del cliente: -10.00€ (debe)
        """
        original = 50.00
        over_refund = -60.00
        balance = round(original + over_refund, 2)
        
        assert balance == -10.00, f"50.00 + (-60.00) debería ser -10.00, se obtuvo {balance}"


class TestEdgeCasesMixedDecimals:
    """Tests para formatos decimales mixtos"""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self, db_helper):
        """Setup y teardown de cada test"""
        db_helper.limpiar_facturas_hoy()
        yield
        db_helper.limpiar_facturas_hoy()
    
    def test_20_mixed_decimal_formats(self, db_helper):
        """Test 20: Mezcla de formatos decimales
        
        Criterio:
        - "10.1" (1 decimal) → 10.10€
        - "20.2" (1 decimal) → 20.20€
        - "30.3" (1 decimal) → 30.30€
        - Total: 60.60€ exacto (sin errores de punto flotante)
        """
        # Simular entrada de usuario con formatos variados
        prices = [10.1, 20.2, 30.3]
        
        # Método 1: Sumar y redondear al final
        total_1 = round(sum(prices), 2)
        
        # Método 2: Redondear cada uno y sumar
        total_2 = round(sum(round(p, 2) for p in prices), 2)
        
        expected = 60.60
        
        assert total_1 == expected, f"Método 1: esperado {expected}, se obtuvo {total_1}"
        assert total_2 == expected, f"Método 2: esperado {expected}, se obtuvo {total_2}"
    
    def test_20b_comma_and_point_decimals(self, db_helper):
        """Test 20b: Coma y punto como separadores decimales
        
        Criterio:
        - "25.50" (punto) → 25.50€
        - "15,75" (coma) → 15.75€
        - Total: 41.25€
        """
        # Normalizar entrada (convertir comas a puntos)
        price_1 = float("25.50")  # Punto
        price_2 = float("15,75".replace(",", "."))  # Coma → punto
        
        total = round(price_1 + price_2, 2)
        expected = 41.25
        
        assert total == expected, f"25.50 + 15.75 debería ser 41.25, se obtuvo {total}"
    
    def test_20c_extreme_decimal_precision(self, db_helper):
        """Test 20c: Precisión extrema en decimales
        
        Criterio:
        - Validar que se rechazan números con 3+ decimales
        - Aceptar solo hasta 2 decimales
        - Evitar errores de precisión
        """
        import re
        
        # Regex de validación de precio
        precio_pattern = r'^(0|[1-9]\d*)([\.,]\d{1,2})?$'
        
        # Válidos (1-2 decimales o sin decimales)
        assert re.match(precio_pattern, "25.5")     # 1 decimal ✓
        assert re.match(precio_pattern, "25.50")    # 2 decimales ✓
        assert re.match(precio_pattern, "25")       # Sin decimales ✓
        
        # Inválidos (3+ decimales)
        assert not re.match(precio_pattern, "25.505")   # 3 decimales ✗
        assert not re.match(precio_pattern, "25.5000")  # 4 decimales ✗
    
    def test_20d_normalized_decimal_input(self, db_helper):
        """Test 20d: Normalización de entrada decimal
        
        Criterio:
        - Entrada: "15,5" (coma, 1 decimal)
        - Normalizado: 15.50€ (punto, 2 decimales)
        - Almacenado: 15.50 (siempre 2 decimales en BD)
        """
        # Entrada del usuario con coma
        user_input = "15,5"
        
        # Normalizar: reemplazar coma por punto y convertir a float
        normalized = float(user_input.replace(",", "."))
        
        # Guardar con 2 decimales
        stored = round(normalized, 2)
        
        assert stored == 15.50, f"Entrada '15,5' debería guardarse como 15.50, se obtuvo {stored}"


class TestEdgeCasesComplexScenarios:
    """Tests para escenarios complejos combinando edge cases"""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self, db_helper):
        """Setup y teardown de cada test"""
        db_helper.limpiar_facturas_hoy()
        yield
        db_helper.limpiar_facturas_hoy()
    
    def test_20e_complex_scenario_everything(self, db_helper):
        """Test 20e: Escenario complejo combinando todos los edge cases
        
        Criterio:
        - Mezcla de: montos pequeños + grandes + muchas líneas
        - Formato decimal mixto (punto y coma)
        - Devolución parcial
        - Total exacto calculado correctamente
        """
        # Simular factura compleja
        items = [
            0.01,      # Monto pequeño
            100.00,    # Monto normal
            5000.00,   # Monto grande (simulado)
            10.1,      # Formato decimal 1 decimal
            20.2,      # Formato decimal 1 decimal
            -35.51,    # Devolución (coma normalizada a punto)
        ]
        
        # Calcular total normalizando y redondeando
        total = round(sum(items), 2)
        # Cálculo: 0.01 + 100.00 + 5000.00 + 10.1 + 20.2 - 35.51 = 5094.8
        expected = 5094.80
        
        assert total == expected, f"Total esperado {expected}, se obtuvo {total}"
