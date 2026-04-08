import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from web.app import app


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
