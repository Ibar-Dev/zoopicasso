"""
test_printer.py — Tests para src/printer.py

Valida el layout del ticket (preview_ticket) sin necesidad de impresora física.
"""
import re
from datetime import date

import pytest

from src.factura_model import EMAIL_EMISOR
from src.factura_model import Factura
from src.factura_model import LineaFactura
from src.factura_model import TELEFONO_EMISOR
from src.printer import preview_ticket

ANCHO = 42


@pytest.fixture
def factura_con_cliente():
    return Factura(
        numero=42,
        fecha=date(2026, 4, 13),
        cliente_nombre="Ana García López",
        cliente_nif="12345678Z",
        lineas=[
            LineaFactura(concepto="Entrada adulto", cantidad=2, precio_unitario=10.00),
            LineaFactura(concepto="Entrada niño", cantidad=1, precio_unitario=4.00),
        ],
    )


@pytest.fixture
def factura_sin_cliente():
    return Factura(
        numero=7,
        fecha=date(2026, 4, 14),
        cliente_nombre="",
        cliente_nif="",
        lineas=[
            LineaFactura(concepto="Servicio puntual", cantidad=1, precio_unitario=50.00),
        ],
    )


@pytest.fixture
def factura_concepto_largo():
    return Factura(
        numero=99,
        fecha=date(2026, 4, 14),
        cliente_nombre="",
        cliente_nif="",
        lineas=[
            LineaFactura(
                concepto="Clase de dibujo avanzada con materiales incluidos — sesión grupal",
                cantidad=1,
                precio_unitario=35.00,
            ),
        ],
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _lineas(ticket: str) -> list[str]:
    return ticket.split("\n")


def _ancho_maximo(ticket: str) -> int:
    return max(len(l) for l in _lineas(ticket))


# ── Tests de estructura ───────────────────────────────────────────────────────

class TestEstructuraTicket:

    def test_ninguna_linea_supera_el_ancho(self, factura_con_cliente):
        ticket = preview_ticket(factura_con_cliente, ancho=ANCHO)
        assert _ancho_maximo(ticket) <= ANCHO

    def test_contiene_nombre_negocio(self, factura_con_cliente):
        ticket = preview_ticket(factura_con_cliente, ancho=ANCHO)
        assert "ZOO PICASSO" in ticket

    def test_contiene_direccion(self, factura_con_cliente):
        ticket = preview_ticket(factura_con_cliente, ancho=ANCHO)
        assert "Pablo Picasso" in ticket

    def test_contiene_telefono(self, factura_con_cliente):
        ticket = preview_ticket(factura_con_cliente, ancho=ANCHO)
        assert TELEFONO_EMISOR in ticket

    def test_contiene_email(self, factura_con_cliente):
        ticket = preview_ticket(factura_con_cliente, ancho=ANCHO)
        assert EMAIL_EMISOR in ticket

    def test_contiene_numero_factura(self, factura_con_cliente):
        ticket = preview_ticket(factura_con_cliente, ancho=ANCHO)
        assert "2026-042" in ticket

    def test_contiene_total_correcto(self, factura_con_cliente):
        # 2*10 + 1*4 = 24.00
        ticket = preview_ticket(factura_con_cliente, ancho=ANCHO)
        assert "24.00 EUR" in ticket

    def test_contiene_iva_incluido(self, factura_con_cliente):
        ticket = preview_ticket(factura_con_cliente, ancho=ANCHO)
        assert "IVA incluido" in ticket

    def test_contiene_pie_gracias(self, factura_con_cliente):
        ticket = preview_ticket(factura_con_cliente, ancho=ANCHO)
        assert "Gracias por tu compra" in ticket

    def test_tiene_separadores(self, factura_con_cliente):
        ticket = preview_ticket(factura_con_cliente, ancho=ANCHO)
        assert "-" * ANCHO in ticket


# ── Tests de datos del cliente ────────────────────────────────────────────────

class TestDatosCliente:

    def test_con_cliente_muestra_nombre(self, factura_con_cliente):
        ticket = preview_ticket(factura_con_cliente, ancho=ANCHO)
        assert "Ana García López" in ticket

    def test_con_cliente_muestra_nif(self, factura_con_cliente):
        ticket = preview_ticket(factura_con_cliente, ancho=ANCHO)
        assert "12345678Z" in ticket

    def test_sin_cliente_no_muestra_etiqueta_cliente(self, factura_sin_cliente):
        ticket = preview_ticket(factura_sin_cliente, ancho=ANCHO)
        assert "Cliente:" not in ticket
        assert "NIF/CIF:" not in ticket


# ── Tests de líneas de conceptos ─────────────────────────────────────────────

class TestLineasConceptos:

    def test_muestra_todos_los_conceptos(self, factura_con_cliente):
        ticket = preview_ticket(factura_con_cliente, ancho=ANCHO)
        assert "Entrada adulto" in ticket
        assert "Entrada niño" in ticket

    def test_muestra_totales_por_linea(self, factura_con_cliente):
        ticket = preview_ticket(factura_con_cliente, ancho=ANCHO)
        assert "20.00 EUR" in ticket  # 2 * 10.00
        assert "4.00 EUR" in ticket   # 1 * 4.00

    def test_concepto_largo_se_trunca(self, factura_concepto_largo):
        ticket = preview_ticket(factura_concepto_largo, ancho=ANCHO)
        assert _ancho_maximo(ticket) <= ANCHO

    def test_cantidad_y_precio_unitario_presentes(self, factura_con_cliente):
        ticket = preview_ticket(factura_con_cliente, ancho=ANCHO)
        assert "2 x 10.00 EUR" in ticket
        assert "1 x 4.00 EUR" in ticket


# ── Tests de alineación ───────────────────────────────────────────────────────

class TestAlineacion:

    def test_encabezado_zoo_picasso_centrado(self, factura_con_cliente):
        ticket = preview_ticket(factura_con_cliente, ancho=ANCHO)
        linea_zoo = next(l for l in _lineas(ticket) if "ZOO PICASSO" in l)
        contenido = linea_zoo.strip()
        margen_izq = len(linea_zoo) - len(linea_zoo.lstrip())
        margen_der = len(linea_zoo) - len(linea_zoo.rstrip())
        assert abs(margen_izq - margen_der) <= 1, "ZOO PICASSO debe estar centrado"

    def test_total_final_alineado_derecha(self, factura_con_cliente):
        ticket = preview_ticket(factura_con_cliente, ancho=ANCHO)
        linea_total = next(l for l in _lineas(ticket) if l.startswith("TOTAL"))
        assert linea_total.endswith("24.00 EUR")

    def test_ancho_con_ancho_personalizado(self, factura_sin_cliente):
        ticket = preview_ticket(factura_sin_cliente, ancho=32)
        assert _ancho_maximo(ticket) <= 32
