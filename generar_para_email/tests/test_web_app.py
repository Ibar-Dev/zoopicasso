import sys
from pathlib import Path
from datetime import date

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from web.app import app
from src.factura_model import Factura, LineaFactura


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

    def _fake_numero() -> int:
        return 123

    def _fake_generar(_factura):
        ruta = tmp_path / "factura_2026_123.xlsx"
        ruta.write_bytes(b"xlsx")
        return ruta

    monkeypatch.setattr("web.app.siguiente_numero_factura", _fake_numero)
    monkeypatch.setattr("web.app.generar_factura_xlsx", _fake_generar)
    monkeypatch.setattr("web.app.RUTA_FACTURAS", tmp_path)

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
        },
    )

    assert generar.status_code == 200
    body = generar.json()
    assert body["numero"].endswith("-123")
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


def test_resumen_y_cierre_mensual_con_login(monkeypatch, tmp_path: Path):
    client = TestClient(app)

    login = client.post(
        "/api/login",
        json={
            "usuario": "Giselle",
            "password_hash": "2aa2d838b21d5fe3fe9819640d83e40aea9f899d93b25a0ef9858ba9f83effda",
        },
    )
    assert login.status_code == 200

    monkeypatch.setattr("web.app.RUTA_FACTURAS", tmp_path)
    monkeypatch.setattr("src.monthly_closure.RUTA_CIERRES", tmp_path / "cierres")

    def _fake_numero() -> int:
        return 321

    def _fake_generar(_factura):
        ruta = tmp_path / "factura_2026_321.xlsx"
        ruta.write_bytes(b"xlsx")
        return ruta

    monkeypatch.setattr("web.app.siguiente_numero_factura", _fake_numero)
    monkeypatch.setattr("web.app.generar_factura_xlsx", _fake_generar)

    generar = client.post(
        "/api/generar",
        json={
            "cliente_nombre": "Cliente mensual",
            "cliente_nif": "Y123",
            "lineas": [
                {
                    "concepto": "Servicio mensual",
                    "cantidad": 2,
                    "precio_unitario": 15.0,
                    "categoria": "perro",
                }
            ],
            "imprimir_ticket": False,
        },
    )
    assert generar.status_code == 200

    resumen = client.get("/api/ganancias/resumen")
    assert resumen.status_code == 200
    resumen_body = resumen.json()["resumen"]
    assert resumen_body["cantidad_ventas"] >= 1
    assert resumen_body["total"] >= 30.0

    cierre = client.post("/api/ganancias/cierre-mes", json={"confirmacion": True})
    assert cierre.status_code == 200
    cierre_body = cierre.json()
    assert cierre_body["ok"] is True
    assert "mensaje" in cierre_body
