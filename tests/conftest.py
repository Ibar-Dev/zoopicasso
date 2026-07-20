import pytest
from pathlib import Path
from datetime import date


@pytest.fixture
def temp_dir(tmp_path):
    """Directorio temporal para tests que requieren un path."""
    return tmp_path


@pytest.fixture
def temp_contador_file(tmp_path):
    """Archivo temporal que simula el contador de facturas."""
    f = tmp_path / "contador.json"
    f.write_text('{"ultima_factura": 0}', encoding="utf-8")
    return f


@pytest.fixture
def sample_factura_data():
    """Datos de muestra para crear facturas en tests de integración."""
    return {
        "numero": 1,
        "fecha": date.today(),
        "cliente_nombre": "Cliente Test",
        "cliente_nif": "12345678A",
        "lineas": [
            {"concepto": "Servicio A", "cantidad": 1, "precio_unitario": 100.0, "categoria": "perro"},
            {"concepto": "Servicio B", "cantidad": 2, "precio_unitario": 50.0, "categoria": "gato"},
        ],
    }


@pytest.fixture
def sample_linea_factura_data():
    """Datos de ejemplo para una línea de factura individual."""
    return {"concepto": "Servicio profesional", "cantidad": 2, "precio_unitario": 50.0, "categoria": "general"}


@pytest.fixture
def temp_env_file(tmp_path):
    """Crea un archivo .env temporal con variables mínimas para tests."""
    f = tmp_path / ".env"
    contenido = (
        "LOG_LEVEL=INFO\n"
        "LOG_FILE=logs/app.log\n"
        "FACTURAS_DIR=facturas\n"
    )
    f.write_text(contenido, encoding="utf-8")
    return f


@pytest.fixture
def caplog_handler(caplog):
    """Alias al fixture `caplog` con el nombre esperado por tests."""
    return caplog
