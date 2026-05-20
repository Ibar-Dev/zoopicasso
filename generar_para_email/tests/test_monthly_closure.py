"""
test_monthly_closure.py — Tests para src/monthly_closure.py
"""
import sys
from datetime import date
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import src.ventas_store as vs
import src.monthly_closure as mc
from src.factura_model import Factura, LineaFactura


@pytest.fixture(autouse=True)
def tmp_dbs(tmp_path, monkeypatch):
    monkeypatch.setattr(vs, "RUTA_DB_VENTAS", tmp_path / "test_ventas.db")
    monkeypatch.setattr(mc, "RUTA_CIERRES", tmp_path / "cierres")


def _factura_mes_actual(numero=1, importe=100.0, categoria="aves"):
    hoy = date.today()
    return Factura(
        numero=numero,
        fecha=hoy,
        cliente_nombre="Test",
        cliente_nif="X000",
        lineas=[LineaFactura("Servicio", 1, importe, categoria)],
    )


# ── sin ventas ──────────────────────────────────────────────────────────────────

class TestSinVentas:
    def test_devuelve_cero_ventas_y_excel_none(self):
        vs.inicializar_db_ventas()
        meta, archivo = mc.cerrar_mes("admin")
        assert meta["ok"] is True
        assert archivo is None
        assert meta["cantidad_ventas"] == 0

    def test_no_crea_archivo_excel(self, tmp_path):
        vs.inicializar_db_ventas()
        mc.cerrar_mes("admin")
        cierres_dir = tmp_path / "cierres"
        assert not cierres_dir.exists() or not any(cierres_dir.iterdir())


# ── con ventas ──────────────────────────────────────────────────────────────────

class TestConVentas:
    def test_genera_excel_y_devuelve_nombre(self, tmp_path):
        vs.registrar_ventas_factura(_factura_mes_actual(), "admin")
        meta, archivo = mc.cerrar_mes("admin")
        assert meta["ok"] is True
        assert archivo is not None
        assert archivo.exists()
        assert archivo.stat().st_size > 0

    def test_cantidad_ventas_correcta(self):
        hoy = date.today()
        f = Factura(
            numero=1,
            fecha=hoy,
            cliente_nombre="Test",
            cliente_nif="X000",
            lineas=[LineaFactura("A", 1, 50.0, "aves"), LineaFactura("B", 1, 30.0, "perros")],
        )
        vs.registrar_ventas_factura(f, "admin")
        meta, archivo = mc.cerrar_mes("admin")
        assert meta["cantidad_ventas"] == 2

    def test_total_correcto(self):
        vs.registrar_ventas_factura(_factura_mes_actual(importe=75.0), "admin")
        meta, archivo = mc.cerrar_mes("admin")
        assert meta["total"] == 75.0

    def test_ventas_quedan_archivadas_tras_cierre(self):
        vs.registrar_ventas_factura(_factura_mes_actual(), "admin")
        mc.cerrar_mes("admin")
        from datetime import datetime
        anio_mes = datetime.now().strftime("%Y-%m")
        assert vs.ventas_activas_detalle(anio_mes) == []

    def test_resumen_total_cero_tras_cierre(self):
        vs.registrar_ventas_factura(_factura_mes_actual(), "admin")
        mc.cerrar_mes("admin")
        from datetime import datetime
        anio_mes = datetime.now().strftime("%Y-%m")
        r = vs.resumen_ventas_activas(anio_mes)
        assert r["total"] == 0.0
        assert r["cantidad_ventas"] == 0


# ── Cierre diario ───────────────────────────────────────────────────────────────

class TestCierreDiario:
    def test_sin_ventas_devuelve_none(self):
        vs.inicializar_db_ventas()
        meta, archivo = mc.cerrar_dia("admin")
        assert meta["ok"] is True
        assert archivo is None
        assert meta["cantidad_ventas"] == 0

    def test_con_ventas_genera_excel(self):
        vs.registrar_ventas_factura(_factura_mes_actual(), "admin")
        meta, archivo = mc.cerrar_dia("admin")
        assert meta["ok"] is True
        assert archivo is not None and archivo.exists()
        assert archivo.stat().st_size > 0

    def test_total_correcto(self):
        vs.registrar_ventas_factura(_factura_mes_actual(importe=60.0), "admin")
        meta, _ = mc.cerrar_dia("admin")
        assert meta["total"] == 60.0

    def test_ventas_siguen_activas_tras_cierre_dia(self):
        vs.registrar_ventas_factura(_factura_mes_actual(), "admin")
        mc.cerrar_dia("admin")
        from datetime import datetime
        anio_mes = datetime.now().strftime("%Y-%m")
        assert vs.resumen_ventas_activas(anio_mes)["total"] == 100.0

    def test_cierre_dia_no_impide_cierre_mes(self):
        vs.registrar_ventas_factura(_factura_mes_actual(importe=50.0), "admin")
        mc.cerrar_dia("admin")
        meta, archivo = mc.cerrar_mes("admin")
        assert meta["ok"] is True
        assert meta["total"] == 50.0
        assert archivo is not None
