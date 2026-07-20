import sys
from pathlib import Path
from datetime import date

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from web.app import app
from src.factura_model import Factura, LineaFactura
import src.ventas_store as _vs


def test_index_ok():
    client = TestClient(app)
    res = client.get("/")

    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]


def test_health_ok():
    client = TestClient(app)
    res = client.get("/api/health")

    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_login_fallido():
    client = TestClient(app)
    res = client.post(
        "/api/login",
        json={"usuario": "otro", "password_hash": "x" * 64},
    )

    assert res.status_code == 401


def test_generar_y_descargar_con_login(monkeypatch, tmp_path: Path):
    client = TestClient(app)

    # Login válido
    login = client.post(
        "/api/login",
        json={
            "usuario": "Giselle",
            "password_hash": "2aa2d838b21d5fe3fe9819640d83e40aea9f899d93b25a0ef9858ba9f83effda",
        },
    )
    assert login.status_code == 200

    def _fake_registrar(_t, _u):
        return "2026-123"

    def _fake_generar(_transaccion):
        ruta = tmp_path / "factura_2026_123.xlsx"
        ruta.write_bytes(b"xlsx")
        return ruta

    monkeypatch.setattr("web.app.registrar_transaccion", _fake_registrar)
    monkeypatch.setattr("web.app.generar_xlsx", _fake_generar)
    monkeypatch.setattr("web.app.anexar_a_excel", lambda _t: None)
    monkeypatch.setattr("web.app.factura_writer.RUTA_FACTURAS", tmp_path)

    generar = client.post(
        "/api/generar",
        json={
            "cliente_nombre": "Cliente 1",
            "cliente_nif": "X123",
            "lineas": [
                {
                    "concepto": "Servicio",
                    "cantidad": 2,
                    "precio_unitario": 10.5,
                }
            ],
            "metodo_pago": "tarjeta",
            "monto_tarjeta": 21.0,
        },
    )

    assert generar.status_code == 200
    body = generar.json()
    assert "123" in body["numero"]
    assert body["archivo"] == "factura_2026_123.xlsx"

    descarga = client.get(body["download_url"])
    assert descarga.status_code == 200
    assert (
        descarga.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def test_resumen_ganancias_requiere_login():
    client = TestClient(app)
    res = client.get("/api/ganancias/resumen")
    assert res.status_code == 401


def _cliente_logueado(monkeypatch, tmp_path):
    """Helper: devuelve un TestClient ya autenticado con monkeypatches de generación."""
    client = TestClient(app)
    login = client.post(
        "/api/login",
        json={
            "usuario": "Giselle",
            "password_hash": "2aa2d838b21d5fe3fe9819640d83e40aea9f899d93b25a0ef9858ba9f83effda",
        },
    )
    assert login.status_code == 200

    monkeypatch.setattr(_vs, "RUTA_DB_VENTAS", tmp_path / "test_ventas.db")

    def _fake_generar(_transaccion):
        ruta = tmp_path / "factura_2026_999.xlsx"
        ruta.write_bytes(b"xlsx")
        return ruta

    monkeypatch.setattr("web.app.generar_xlsx", _fake_generar)
    monkeypatch.setattr("web.app.anexar_a_excel", lambda _t: None)
    monkeypatch.setattr("web.app.factura_writer.RUTA_FACTURAS", tmp_path)
    return client


def test_config_reporta_ruta_facturas_efectiva(monkeypatch, tmp_path):
    client = TestClient(app)
    login = client.post(
        "/api/login",
        json={
            "usuario": "Giselle",
            "password_hash": "2aa2d838b21d5fe3fe9819640d83e40aea9f899d93b25a0ef9858ba9f83effda",
        },
    )
    assert login.status_code == 200

    monkeypatch.setattr("web.app.factura_writer.RUTA_FACTURAS", tmp_path)

    res = client.get("/api/config")
    assert res.status_code == 200

    body = res.json()
    assert body["rutas"]["facturas_principal"] == str(tmp_path.resolve())
    assert "facturas_settings" in body["rutas"]


def test_generar_sin_ticket_siempre_genera_excel(monkeypatch, tmp_path):
    client = _cliente_logueado(monkeypatch, tmp_path)
    generado = {"count": 0}
    encolado = {"count": 0}

    def _fake_generar(_transaccion):
        generado["count"] += 1
        ruta = tmp_path / "factura_2026_321.xlsx"
        ruta.write_bytes(b"xlsx")
        return ruta

    def _fake_encolar(_transaccion, _cola):
        encolado["count"] += 1

    monkeypatch.setattr("web.app.generar_xlsx", _fake_generar)
    monkeypatch.setattr("web.app.encolar_impresion", _fake_encolar)

    res = client.post(
        "/api/generar",
        json={
            "lineas": [{"concepto": "Test", "cantidad": 1, "precio_unitario": 10.0}],
            "metodo_pago": "tarjeta",
            "monto_tarjeta": 10.0,
            "imprimir_ticket": False,
        },
    )

    assert res.status_code == 200
    body = res.json()
    assert body["ticket_impreso"] is False
    assert generado["count"] == 1
    assert encolado["count"] == 0

    descarga = client.get(body["download_url"])
    assert descarga.status_code == 200


def test_generar_con_ticket_tambien_genera_excel(monkeypatch, tmp_path):
    client = _cliente_logueado(monkeypatch, tmp_path)
    generado = {"count": 0}
    encolado = {"count": 0}

    def _fake_generar(_transaccion):
        generado["count"] += 1
        ruta = tmp_path / "factura_2026_654.xlsx"
        ruta.write_bytes(b"xlsx")
        return ruta

    def _fake_encolar(_transaccion, _cola):
        encolado["count"] += 1

    monkeypatch.setattr("web.app.generar_xlsx", _fake_generar)
    monkeypatch.setattr("web.app.encolar_impresion", _fake_encolar)

    res = client.post(
        "/api/generar",
        json={
            "lineas": [{"concepto": "Test", "cantidad": 1, "precio_unitario": 10.0}],
            "metodo_pago": "tarjeta",
            "monto_tarjeta": 10.0,
            "imprimir_ticket": True,
        },
    )

    assert res.status_code == 200
    body = res.json()
    assert body["ticket_impreso"] is True
    assert generado["count"] == 1
    assert encolado["count"] == 1

    descarga = client.get(body["download_url"])
    assert descarga.status_code == 200


def test_generar_si_falla_excel_retorna_500(monkeypatch, tmp_path):
    client = _cliente_logueado(monkeypatch, tmp_path)

    def _fake_generar(_transaccion):
        raise OSError("disk full")

    monkeypatch.setattr("web.app.generar_xlsx", _fake_generar)

    res = client.post(
        "/api/generar",
        json={
            "lineas": [{"concepto": "Test", "cantidad": 1, "precio_unitario": 10.0}],
            "metodo_pago": "tarjeta",
            "monto_tarjeta": 10.0,
        },
    )

    assert res.status_code == 500
    assert res.json()["detail"] == "No se pudo generar la factura"


def test_generar_sin_metodo_pago_retorna_400(monkeypatch, tmp_path):
    client = _cliente_logueado(monkeypatch, tmp_path)
    res = client.post(
        "/api/generar",
        json={
            "lineas": [{"concepto": "Test", "cantidad": 1, "precio_unitario": 10.0}],
        },
    )
    assert res.status_code == 400
    assert "pago" in res.json()["detail"].lower() or "método" in res.json()["detail"].lower()


def test_generar_efectivo_ok(monkeypatch, tmp_path):
    client = _cliente_logueado(monkeypatch, tmp_path)
    res = client.post(
        "/api/generar",
        json={
            "lineas": [{"concepto": "Test", "cantidad": 1, "precio_unitario": 10.0}],
            "metodo_pago": "efectivo",
            "monto_efectivo": 10.0,
            "efectivo_entregado": 20.0,
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["cambio"] == 10.0


def test_generar_efectivo_entregado_insuficiente_retorna_400(monkeypatch, tmp_path):
    client = _cliente_logueado(monkeypatch, tmp_path)
    res = client.post(
        "/api/generar",
        json={
            "lineas": [{"concepto": "Test", "cantidad": 1, "precio_unitario": 10.0}],
            "metodo_pago": "efectivo",
            "monto_efectivo": 10.0,
            "efectivo_entregado": 5.0,
        },
    )
    assert res.status_code == 400


def test_generar_tarjeta_ok(monkeypatch, tmp_path):
    client = _cliente_logueado(monkeypatch, tmp_path)
    res = client.post(
        "/api/generar",
        json={
            "lineas": [{"concepto": "Test", "cantidad": 2, "precio_unitario": 15.0}],
            "metodo_pago": "tarjeta",
            "monto_tarjeta": 30.0,
        },
    )
    assert res.status_code == 200
    assert res.json()["cambio"] == 0.0


def test_generar_mixto_ok(monkeypatch, tmp_path):
    client = _cliente_logueado(monkeypatch, tmp_path)
    res = client.post(
        "/api/generar",
        json={
            "lineas": [{"concepto": "Test", "cantidad": 1, "precio_unitario": 50.0}],
            "metodo_pago": "mixto",
            "monto_efectivo": 20.0,
            "monto_tarjeta": 30.0,
            "efectivo_entregado": 25.0,
        },
    )
    assert res.status_code == 200
    assert res.json()["cambio"] == 5.0


def test_generar_mixto_suma_incorrecta_retorna_400(monkeypatch, tmp_path):
    client = _cliente_logueado(monkeypatch, tmp_path)
    res = client.post(
        "/api/generar",
        json={
            "lineas": [{"concepto": "Test", "cantidad": 1, "precio_unitario": 50.0}],
            "metodo_pago": "mixto",
            "monto_efectivo": 10.0,
            "monto_tarjeta": 10.0,
            "efectivo_entregado": 10.0,
        },
    )
    assert res.status_code == 400


@pytest.mark.parametrize("concepto", ["Alimentación", "Snack", "Accesorios", "Higiene", "Salud", "Servicio de peluquería"])
def test_generar_concepto_valido(concepto, monkeypatch, tmp_path):
    client = _cliente_logueado(monkeypatch, tmp_path)
    res = client.post(
        "/api/generar",
        json={
            "lineas": [{"concepto": concepto, "cantidad": 1, "precio_unitario": 10.0}],
            "metodo_pago": "tarjeta",
            "monto_tarjeta": 10.0,
        },
    )
    assert res.status_code == 200


# ── /api/session ──────────────────────────────────────────────────────────────

def test_session_sin_login():
    client = TestClient(app)
    res = client.get("/api/session")
    assert res.status_code == 200
    assert res.json() == {"logged_in": False}


def test_session_con_login():
    client = TestClient(app)
    client.post(
        "/api/login",
        json={
            "usuario": "Giselle",
            "password_hash": "2aa2d838b21d5fe3fe9819640d83e40aea9f899d93b25a0ef9858ba9f83effda",
        },
    )
    res = client.get("/api/session")
    assert res.status_code == 200


# ── /api/logout ───────────────────────────────────────────────────────────────

def test_logout():
    client = TestClient(app)
    client.post(
        "/api/login",
        json={
            "usuario": "Giselle",
            "password_hash": "2aa2d838b21d5fe3fe9819640d83e40aea9f899d93b25a0ef9858ba9f83effda",
        },
    )
    res = client.post("/api/logout")
    assert res.status_code == 200
    assert res.json()["ok"] is True
    session = client.get("/api/session")
    assert session.json() == {"logged_in": False}


# ── /api/ganancias/ajuste ─────────────────────────────────────────────────────

def test_ajuste_ok(monkeypatch, tmp_path):
    client = _cliente_logueado(monkeypatch, tmp_path)
    client.post(
        "/api/generar",
        json={
            "lineas": [{"concepto": "Test ajuste", "cantidad": 1, "precio_unitario": 50.0}],
            "metodo_pago": "tarjeta",
            "monto_tarjeta": 50.0,
        },
    )
    res = client.post("/api/ganancias/ajuste", json={"monto": 10.0})
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["resumen"]["ajuste_total"] == 10.0


def test_ajuste_supera_total_retorna_400(monkeypatch, tmp_path):
    client = _cliente_logueado(monkeypatch, tmp_path)
    client.post(
        "/api/generar",
        json={
            "lineas": [{"concepto": "Test", "cantidad": 1, "precio_unitario": 20.0}],
            "metodo_pago": "tarjeta",
            "monto_tarjeta": 20.0,
        },
    )
    res = client.post("/api/ganancias/ajuste", json={"monto": 999.0})
    assert res.status_code == 400


# ── /api/ganancias/historial ──────────────────────────────────────────────────

def test_historial_ok(monkeypatch, tmp_path):
    client = _cliente_logueado(monkeypatch, tmp_path)
    client.post(
        "/api/generar",
        json={
            "lineas": [{"concepto": "Historial test", "cantidad": 1, "precio_unitario": 15.0}],
            "metodo_pago": "tarjeta",
            "monto_tarjeta": 15.0,
        },
    )
    hoy = date.today().isoformat()
    res = client.get(f"/api/ganancias/historial?fecha_desde={hoy}&fecha_hasta={hoy}")
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert len(body["filas"]) >= 1


# ── /api/precios_categorias (DEPRECADO) ──────────────────────────────────────
# La gestión de precios por categoría ha sido removida de la UI.
# Este test se mantiene para asegurar compatibilidad con backups y código heredado.

def test_precios_categorias_post(monkeypatch, tmp_path):
    """La gestión de precios por categoría solo expone POST (endpoint deprecado).
    El GET fue eliminado cuando se removió la UI; solo se mantiene POST para
    compatibilidad con código heredado."""
    precios_path = tmp_path / "precios_categorias.json"
    monkeypatch.setattr("web.app.PRECIOS_CATEGORIAS_PATH", precios_path)

    client = TestClient(app)
    client.post(
        "/api/login",
        json={
            "usuario": "Giselle",
            "password_hash": "2aa2d838b21d5fe3fe9819640d83e40aea9f899d93b25a0ef9858ba9f83effda",
        },
    )
    post_res = client.post("/api/precios_categorias", json={"precios": {"aves": 25.50, "perros": 30.0}})
    assert post_res.status_code == 200
    assert post_res.json()["ok"] is True
    assert post_res.json()["precios"]["aves"] == 25.50


# ── /api/backup/manual ────────────────────────────────────────────────────────

def test_backup_manual_devuelve_zip(monkeypatch, tmp_path):
    import zipfile as zf
    client = TestClient(app)
    client.post(
        "/api/login",
        json={
            "usuario": "Giselle",
            "password_hash": "2aa2d838b21d5fe3fe9819640d83e40aea9f899d93b25a0ef9858ba9f83effda",
        },
    )

    def _fake_backup(backup_dir, retener):
        archivo = backup_dir / "backup_test.zip"
        with zf.ZipFile(archivo, "w") as z:
            z.writestr("test.txt", "ok")
        return archivo

    monkeypatch.setattr("web.app.hacer_backup", _fake_backup)
    monkeypatch.setattr("web.app.DATA_DIR", tmp_path)
    res = client.post("/api/backup/manual")
    assert res.status_code == 200
    assert "zip" in res.headers["content-type"]
    assert len(res.content) > 0


def test_backup_manual_sin_login_retorna_401():
    client = TestClient(app)
    res = client.post("/api/backup/manual")
    assert res.status_code == 401


# ── /api/backup/estado ────────────────────────────────────────────────────────

def test_backup_estado_ok(monkeypatch, tmp_path):
    client = TestClient(app)
    client.post(
        "/api/login",
        json={
            "usuario": "Giselle",
            "password_hash": "2aa2d838b21d5fe3fe9819640d83e40aea9f899d93b25a0ef9858ba9f83effda",
        },
    )
    monkeypatch.setattr("web.app.DATA_DIR", tmp_path)
    res = client.get("/api/backup/estado")
    assert res.status_code == 200
    assert res.json()["ok"] is True


# ── /api/ganancias/ajustes ────────────────────────────────────────────────────

def test_ajustes_lista_ok(monkeypatch, tmp_path):
    client = _cliente_logueado(monkeypatch, tmp_path)
    res = client.get("/api/ganancias/ajustes")
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert isinstance(body["ajustes"], list)


# ── /api/descargar/<archivo> ──────────────────────────────────────────────────

def test_descargar_factura_no_encontrada(monkeypatch, tmp_path):
    client = TestClient(app)
    client.post(
        "/api/login",
        json={
            "usuario": "Giselle",
            "password_hash": "2aa2d838b21d5fe3fe9819640d83e40aea9f899d93b25a0ef9858ba9f83effda",
        },
    )
    monkeypatch.setattr("web.app.factura_writer.RUTA_FACTURAS", tmp_path)
    res = client.get("/api/descargar/no_existe.xlsx")
    assert res.status_code == 404


def test_descargar_factura_usa_ruta_efectiva(monkeypatch, tmp_path):
    client = TestClient(app)
    client.post(
        "/api/login",
        json={
            "usuario": "Giselle",
            "password_hash": "2aa2d838b21d5fe3fe9819640d83e40aea9f899d93b25a0ef9858ba9f83effda",
        },
    )

    monkeypatch.setattr("web.app.factura_writer.RUTA_FACTURAS", tmp_path)
    archivo = tmp_path / "factura_efectiva.xlsx"
    archivo.write_bytes(b"xlsx")

    res = client.get(f"/api/descargar/{archivo.name}")
    assert res.status_code == 200


# ── /api/impresion/siguiente ──────────────────────────────────────────────────

def test_siguiente_ticket_vacio():
    import web.app as webapp
    webapp.cola_impresion.clear()
    client = TestClient(app)
    
    # Login requerido para acceder al endpoint
    login_res = client.post(
        "/api/login",
        json={
            "usuario": "Giselle",
            "password_hash": "2aa2d838b21d5fe3fe9819640d83e40aea9f899d93b25a0ef9858ba9f83effda",
        },
    )
    assert login_res.status_code == 200
    
    res = client.get("/api/impresion/siguiente")
    assert res.status_code == 204


def test_siguiente_ticket_con_datos():
    import web.app as webapp
    webapp.cola_impresion.clear()
    webapp.cola_impresion.append(b"\x1b\x40Hello\n")
    client = TestClient(app)
    
    # Login requerido para acceder al endpoint
    login_res = client.post(
        "/api/login",
        json={
            "usuario": "Giselle",
            "password_hash": "2aa2d838b21d5fe3fe9819640d83e40aea9f899d93b25a0ef9858ba9f83effda",
        },
    )
    assert login_res.status_code == 200
    
    res = client.get("/api/impresion/siguiente")
    assert res.status_code == 200
    body = res.json()
    assert body["hay_ticket"] is True
    assert "ticket_b64" in body
    webapp.cola_impresion.clear()
