"""
test_ventas_store.py — Tests unitarios para src/ventas_store.py
"""
import sqlite3
import sys
from datetime import date
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import src.ventas_store as vs
from src.factura_model import Factura, LineaFactura, PagoInfo


@pytest.fixture(autouse=True)
def db_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(vs, "RUTA_DB_VENTAS", tmp_path / "test_ventas.db")


def _factura(numero=1, anio=2026, mes=5, lineas=None):
    if lineas is None:
        lineas = [LineaFactura("Consulta", 1, 30.0, "aves")]
    return Factura(
        numero=numero,
        fecha=date(anio, mes, 10),
        cliente_nombre="Test Cliente",
        cliente_nif="X123",
        lineas=lineas,
    )


def _pago(
    total=30.0,
    efectivo=30.0,
    tarjeta=0.0,
    metodo="efectivo",
    entregado=50.0,
    cambio=20.0,
):
    return PagoInfo(
        monto_total=total,
        monto_efectivo=efectivo,
        monto_tarjeta=tarjeta,
        metodo_pago=metodo,
        efectivo_entregado=entregado,
        cambio=cambio,
    )


# ── inicializar_db_ventas ──────────────────────────────────────────────────────

class TestInicializarDb:
    def test_crea_tablas(self):
        vs.inicializar_db_ventas()
        conn = sqlite3.connect(vs.RUTA_DB_VENTAS)
        tablas = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        conn.close()
        assert {"ventas", "pagos_factura", "ajustes_manuales", "transacciones", "contadores"}.issubset(tablas)

    def test_idempotente(self):
        vs.inicializar_db_ventas()
        vs.inicializar_db_ventas()  # debe ejecutarse sin error ni duplicados


# ── registrar_ventas_factura ───────────────────────────────────────────────────

class TestRegistrarVentasFactura:
    def test_registra_lineas(self):
        f = _factura()
        vs.registrar_ventas_factura(f, "admin")
        rows = vs.ventas_activas_detalle("2026-05")
        assert len(rows) == 1
        assert rows[0]["monto"] == 30.0
        assert rows[0]["categoria"] == "aves"

    def test_registra_multiples_lineas(self):
        f = _factura(
            lineas=[
                LineaFactura("Consulta", 1, 20.0, "perros"),
                LineaFactura("Vacuna", 2, 15.0, "gatos"),
            ]
        )
        vs.registrar_ventas_factura(f, "admin")
        rows = vs.ventas_activas_detalle("2026-05")
        assert len(rows) == 2

    def test_registra_pago_info(self):
        f = _factura()
        vs.registrar_ventas_factura(f, "admin", pago=_pago())
        conn = sqlite3.connect(vs.RUTA_DB_VENTAS)
        row = conn.execute("SELECT * FROM pagos_factura").fetchone()
        conn.close()
        assert row is not None
        assert row[4] == 30.0   # monto_total

    def test_sin_pago_no_inserta_pagos_factura(self):
        f = _factura()
        vs.registrar_ventas_factura(f, "admin")
        conn = sqlite3.connect(vs.RUTA_DB_VENTAS)
        count = conn.execute("SELECT COUNT(*) FROM pagos_factura").fetchone()[0]
        conn.close()
        assert count == 0

    def test_categoria_vacia_se_normaliza(self):
        f = _factura(lineas=[LineaFactura("Algo", 1, 10.0, "")])
        vs.registrar_ventas_factura(f, "admin")
        rows = vs.ventas_activas_detalle("2026-05")
        assert rows[0]["categoria"] == "sin_categoria"


# ── resumen_ventas_activas ─────────────────────────────────────────────────────

class TestResumenVentasActivas:
    def test_sin_ventas_devuelve_ceros(self):
        vs.inicializar_db_ventas()
        r = vs.resumen_ventas_activas("2026-05")
        assert r["total"] == 0.0
        assert r["cantidad_ventas"] == 0
        assert r["por_categoria"] == {}

    def test_con_ventas_calcula_total(self):
        vs.registrar_ventas_factura(_factura(), "admin")
        r = vs.resumen_ventas_activas("2026-05")
        assert r["total"] == 30.0
        assert r["cantidad_ventas"] == 1

    def test_con_ajuste_descuenta_del_total(self):
        vs.registrar_ventas_factura(_factura(), "admin")
        vs.registrar_ajuste("2026-05", "admin", 10.0)
        r = vs.resumen_ventas_activas("2026-05")
        assert r["total"] == 20.0
        assert r["total_bruto"] == 30.0
        assert r["ajuste_total"] == 10.0

    def test_pago_efectivo_y_tarjeta(self):
        f = _factura(lineas=[LineaFactura("X", 1, 100.0, "aves")])
        pago = _pago(total=100.0, efectivo=60.0, tarjeta=40.0, metodo="mixto")
        vs.registrar_ventas_factura(f, "admin", pago=pago)
        r = vs.resumen_ventas_activas("2026-05")
        assert r["total_efectivo"] == 60.0
        assert r["total_tarjeta"] == 40.0

    def test_no_mezcla_meses(self):
        vs.registrar_ventas_factura(_factura(anio=2026, mes=4), "admin")
        r = vs.resumen_ventas_activas("2026-05")
        assert r["total"] == 0.0


# ── resumen_ventas_dia ─────────────────────────────────────────────────────────

class TestResumenVentasDia:
    def test_sin_ventas_devuelve_ceros(self):
        vs.inicializar_db_ventas()
        r = vs.resumen_ventas_dia("2026-05-10")
        assert r["total"] == 0.0
        assert r["cantidad_ventas"] == 0

    def test_con_ventas_del_dia(self):
        vs.registrar_ventas_factura(_factura(), "admin")
        r = vs.resumen_ventas_dia("2026-05-10")
        assert r["total"] == 30.0
        assert r["cantidad_ventas"] == 1

    def test_no_mezcla_dias(self):
        vs.registrar_ventas_factura(_factura(), "admin")
        r = vs.resumen_ventas_dia("2026-05-11")
        assert r["total"] == 0.0


# ── registrar_ajuste / listar_ajustes_activos ──────────────────────────────────

class TestAjustes:
    def test_registra_ajuste_positivo(self):
        vs.registrar_ajuste("2026-05", "admin", 15.0)
        ajustes = vs.listar_ajustes_activos("2026-05")
        assert len(ajustes) == 1
        assert ajustes[0]["monto"] == 15.0

    def test_registra_ajuste_negativo(self):
        vs.registrar_ajuste("2026-05", "admin", -5.0)
        ajustes = vs.listar_ajustes_activos("2026-05")
        assert ajustes[0]["monto"] == -5.0

    def test_lista_vacia_sin_ajustes(self):
        vs.inicializar_db_ventas()
        assert vs.listar_ajustes_activos("2026-05") == []

    def test_no_mezcla_meses(self):
        vs.registrar_ajuste("2026-04", "admin", 10.0)
        assert vs.listar_ajustes_activos("2026-05") == []


# ── archivar_ajustes_activos ───────────────────────────────────────────────────

class TestArchivarAjustes:
    def test_archiva_ajustes_del_mes(self):
        vs.registrar_ajuste("2026-05", "admin", 10.0)
        vs.archivar_ajustes_activos("2026-05", "cierre-001", "2026-05-31T00:00:00+00:00")
        assert vs.listar_ajustes_activos("2026-05") == []

    def test_no_afecta_otros_meses(self):
        vs.registrar_ajuste("2026-04", "admin", 5.0)
        vs.archivar_ajustes_activos("2026-05", "cierre-001", "2026-05-31T00:00:00+00:00")
        assert len(vs.listar_ajustes_activos("2026-04")) == 1


# ── ventas_activas_detalle ─────────────────────────────────────────────────────

class TestVentasActivasDetalle:
    def test_devuelve_campos_correctos(self):
        vs.registrar_ventas_factura(_factura(), "admin")
        rows = vs.ventas_activas_detalle("2026-05")
        assert len(rows) == 1
        row = rows[0]
        assert "numero_factura" in row
        assert "categoria" in row
        assert "monto" in row
        assert row["usuario"] == "admin"

    def test_vacio_sin_ventas(self):
        vs.inicializar_db_ventas()
        assert vs.ventas_activas_detalle("2026-05") == []


# ── archivar_ventas_activas ────────────────────────────────────────────────────

class TestArchivarVentas:
    def test_devuelve_rowcount(self):
        vs.registrar_ventas_factura(
            _factura(lineas=[LineaFactura("A", 1, 10.0, "aves"), LineaFactura("B", 1, 20.0, "perros")]),
            "admin",
        )
        count = vs.archivar_ventas_activas("2026-05", "cierre-001", "2026-05-31T00:00:00+00:00")
        assert count == 2

    def test_ventas_quedan_archivadas(self):
        vs.registrar_ventas_factura(_factura(), "admin")
        vs.archivar_ventas_activas("2026-05", "cierre-001", "2026-05-31T00:00:00+00:00")
        assert vs.ventas_activas_detalle("2026-05") == []

    def test_no_toca_otros_meses(self):
        vs.registrar_ventas_factura(_factura(anio=2026, mes=4), "admin")
        vs.archivar_ventas_activas("2026-05", "cierre-001", "2026-05-31T00:00:00+00:00")
        assert len(vs.ventas_activas_detalle("2026-04")) == 1

    def test_devuelve_cero_si_no_hay_ventas(self):
        vs.inicializar_db_ventas()
        count = vs.archivar_ventas_activas("2026-05", "cierre-001", "2026-05-31T00:00:00+00:00")
        assert count == 0


# ── historial_ventas ───────────────────────────────────────────────────────────

class TestHistorialVentas:
    def _setup_dos_facturas(self):
        f1 = _factura(numero=1, lineas=[LineaFactura("A", 1, 50.0, "aves")])
        f2 = _factura(numero=2, lineas=[LineaFactura("B", 1, 80.0, "perros")])
        vs.registrar_ventas_factura(f1, "admin", pago=_pago(total=50.0, efectivo=50.0, tarjeta=0.0))
        vs.registrar_ventas_factura(f2, "admin", pago=_pago(total=80.0, efectivo=0.0, tarjeta=80.0, metodo="tarjeta"))

    def test_devuelve_todas_las_facturas(self):
        self._setup_dos_facturas()
        rows = vs.historial_ventas("2026-05-01", "2026-05-31")
        assert len(rows) == 2

    def test_filtra_por_categoria(self):
        self._setup_dos_facturas()
        rows = vs.historial_ventas("2026-05-01", "2026-05-31", categoria="aves")
        assert len(rows) == 1
        assert "aves" in rows[0]["categorias"]

    def test_filtra_por_metodo_pago(self):
        self._setup_dos_facturas()
        rows = vs.historial_ventas("2026-05-01", "2026-05-31", metodo_pago="tarjeta")
        assert len(rows) == 1

    def test_rango_sin_resultados(self):
        self._setup_dos_facturas()
        rows = vs.historial_ventas("2024-01-01", "2024-01-31")
        assert rows == []

    def test_incluye_ventas_archivadas(self):
        self._setup_dos_facturas()
        vs.archivar_ventas_activas("2026-05", "cierre-001", "2026-05-31T00:00:00+00:00")
        rows = vs.historial_ventas("2026-05-01", "2026-05-31")
        assert len(rows) == 2
