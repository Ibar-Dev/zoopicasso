import json
from pathlib import Path

import pytest

from src import factura_counter


def test_inicializar_contador_crea_archivo(tmp_path, monkeypatch):
    ruta = tmp_path / "data" / "contador_facturas.json"
    monkeypatch.setattr(factura_counter, "RUTA_CONTADOR", ruta)

    factura_counter._inicializar_contador()

    assert ruta.exists()
    data = json.loads(ruta.read_text(encoding="utf-8"))
    assert data["ultima_factura"] == 0


def test_leer_y_escribir_contador_real(tmp_path, monkeypatch):
    ruta = tmp_path / "data" / "contador_facturas.json"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(factura_counter, "RUTA_CONTADOR", ruta)

    factura_counter._escribir(7)
    valor = factura_counter._leer()

    assert valor == 7


def test_siguiente_numero_factura_incrementa(tmp_path, monkeypatch):
    ruta = tmp_path / "data" / "contador_facturas.json"
    monkeypatch.setattr(factura_counter, "RUTA_CONTADOR", ruta)

    assert factura_counter.siguiente_numero_factura() == 1
    assert factura_counter.siguiente_numero_factura() == 2


def test_leer_contador_corrupto_lanza_json_error(tmp_path, monkeypatch):
    ruta = tmp_path / "data" / "contador_facturas.json"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("{json-roto", encoding="utf-8")
    monkeypatch.setattr(factura_counter, "RUTA_CONTADOR", ruta)

    with pytest.raises(json.JSONDecodeError):
        factura_counter._leer()


def test_escribir_error_io_propagado(monkeypatch):
    ruta = Path("/tmp/falso-contador.json")
    monkeypatch.setattr(factura_counter, "RUTA_CONTADOR", ruta)
    monkeypatch.setattr(type(ruta), "open", lambda *a, **k: (_ for _ in ()).throw(OSError("sin permisos")))

    with pytest.raises(OSError):
        factura_counter._escribir(1)
