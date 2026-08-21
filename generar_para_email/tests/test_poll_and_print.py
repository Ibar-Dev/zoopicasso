import time

import pytest

import poll_and_print as poll_print


def test_iniciar_procesa_ticket_sin_crash(monkeypatch, tmp_path):
    agente = poll_print.AgenteImpresion("http://example.test", tmp_path)
    datos_ticket = {
        "hay_ticket": True,
        "ticket_b64": "Zm9v",
        "archivo_xlsx": "factura_2026_001.xlsx",
        "download_url": "http://example.test/api/descargar/factura_2026_001.xlsx",
    }
    llamados = []

    monkeypatch.setattr(agente, "verificar_conexion", lambda: True)
    monkeypatch.setattr(agente, "consultar_tickets", lambda: datos_ticket)

    def fake_procesar_ticket(datos):
        llamados.append(datos)
        raise KeyboardInterrupt

    monkeypatch.setattr(agente, "procesar_ticket", fake_procesar_ticket)
    monkeypatch.setattr(time, "sleep", lambda *_args, **_kwargs: (_ for _ in ()).throw(KeyboardInterrupt()))

    with pytest.raises(KeyboardInterrupt):
        agente.iniciar()

    assert llamados == [datos_ticket]
