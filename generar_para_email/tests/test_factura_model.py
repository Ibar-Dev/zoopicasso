"""
test_factura_model.py — Tests para los modelos de datos (LineaFactura, Factura)
"""

import pytest
from datetime import date

from src.factura_model import LineaFactura, Factura, IVA_PCT


class TestLineaFactura:
    """Tests para la clase LineaFactura."""

    def test_crear_linea_valida(self, sample_linea_factura_data):
        """Crear una línea de factura válida."""
        linea = LineaFactura(**sample_linea_factura_data)
        assert linea.concepto == "Servicio profesional"
        assert linea.cantidad == 2
        assert linea.precio_unitario == 50.00
        assert linea.total == 100.00

    def test_calculo_total(self):
        """Verificar que el total se calcula correctamente."""
        linea = LineaFactura("Servicios", 3, 25.50)
        assert linea.total == 76.50  # 3 * 25.50

    def test_cantidad_cero_invalida(self):
        """Cantidad cero debe lanzar ValueError."""
        with pytest.raises(ValueError, match="cantidad debe ser mayor que 0"):
            LineaFactura("Servicio", 0, 100.00)

    def test_cantidad_negativa_invalida(self):
        """Cantidad negativa debe lanzar ValueError."""
        with pytest.raises(ValueError, match="cantidad debe ser mayor que 0"):
            LineaFactura("Servicio", -1, 100.00)

    def test_precio_negativo_invalido(self):
        """Precio negativo debe lanzar ValueError."""
        with pytest.raises(ValueError, match="precio unitario no puede ser negativo"):
            LineaFactura("Servicio", 1, -100.00)

    def test_redondeo_total(self):
        """Verificar que el total se redondea correctamente a 2 decimales."""
        linea = LineaFactura("Servicio", 3, 10.01)
        assert linea.total == 30.03
        assert isinstance(linea.total, float)


class TestFactura:
    """Tests para la clase Factura."""

    def test_crear_factura_valida(self, sample_factura_data):
        """Crear una factura válida con datos correctos."""
        lineas = [
            LineaFactura(d["concepto"], d["cantidad"], d["precio_unitario"])
            for d in sample_factura_data["lineas"]
        ]
        factura = Factura(
            numero=sample_factura_data["numero"],
            fecha=sample_factura_data["fecha"],
            cliente_nombre=sample_factura_data["cliente_nombre"],
            cliente_nif=sample_factura_data["cliente_nif"],
            lineas=lineas,
        )
        assert factura.numero == 1
        assert factura.cliente_nombre == "Cliente Test"
        assert factura.cliente_nif == "12345678A"
        assert len(factura.lineas) == 2

    def test_factura_sin_lineas_invalida(self):
        """Factura sin líneas debe ser inválida."""
        with pytest.raises(ValueError, match="debe tener al menos una línea"):
            Factura(
                numero=1,
                fecha=date.today(),
                cliente_nombre="Cliente",
                cliente_nif="12345678A",
                lineas=[],
            )

    def test_cliente_opcional(self):
        """Cliente y NIF pueden ser vacíos (strings vacíos)."""
        linea = LineaFactura("Servicio", 1, 100.00)
        factura = Factura(
            numero=1,
            fecha=date.today(),
            cliente_nombre="",
            cliente_nif="",
            lineas=[linea],
        )
        assert factura.cliente_nombre == ""
        assert factura.cliente_nif == ""

    def test_base_imponible(self, sample_factura_data):
        """Calcular base imponible (suma de totales)."""
        lineas = [
            LineaFactura(d["concepto"], d["cantidad"], d["precio_unitario"])
            for d in sample_factura_data["lineas"]
        ]
        factura = Factura(
            numero=1,
            fecha=date.today(),
            cliente_nombre="Cliente",
            cliente_nif="12345678A",
            lineas=lineas,
        )
        # 100 + 100 = 200
        assert factura.base_imponible == 200.00

    def test_cuota_iva(self, sample_factura_data):
        """Calcular cuota de IVA correctamente."""
        lineas = [
            LineaFactura(d["concepto"], d["cantidad"], d["precio_unitario"])
            for d in sample_factura_data["lineas"]
        ]
        factura = Factura(
            numero=1,
            fecha=date.today(),
            cliente_nombre="Cliente",
            cliente_nif="12345678A",
            lineas=lineas,
        )
        # 200 * 21% = 42
        assert factura.cuota_iva == 0.00

    def test_total_con_iva(self, sample_factura_data):
        """Calcular total con IVA correctamente."""
        lineas = [
            LineaFactura(d["concepto"], d["cantidad"], d["precio_unitario"])
            for d in sample_factura_data["lineas"]
        ]
        factura = Factura(
            numero=1,
            fecha=date.today(),
            cliente_nombre="Cliente",
            cliente_nif="12345678A",
            lineas=lineas,
        )
        # 200 + 42 = 242
        assert factura.total_con_iva == 200.00

    def test_numero_formateado(self):
        """Formato de número de factura YYYY-NNN."""
        linea = LineaFactura("Servicio", 1, 100.00)
        factura = Factura(
            numero=5,
            fecha=date(2026, 4, 8),
            cliente_nombre="Cliente",
            cliente_nif="12345678A",
            lineas=[linea],
        )
        assert factura.numero_formateado == "2026-005"

    def test_fecha_formateada(self):
        """Formato de fecha DD/MM/YYYY."""
        linea = LineaFactura("Servicio", 1, 100.00)
        factura = Factura(
            numero=1,
            fecha=date(2026, 4, 8),
            cliente_nombre="Cliente",
            cliente_nif="12345678A",
            lineas=[linea],
        )
        assert factura.fecha_formateada == "08/04/2026"

    def test_iva_porcentaje_constante(self):
        """Verificar que IVA_PCT tiene valor correcto."""
        assert IVA_PCT == 21
