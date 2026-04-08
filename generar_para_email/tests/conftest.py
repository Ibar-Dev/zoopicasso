"""
conftest.py — Configuración y fixtures compartidas para pytest

Proporciona fixtures reutilizables para todos los tests.
"""

import json
import logging
import shutil
import tempfile
from datetime import date
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Crea un directorio temporal para tests que necesitan archivos."""
    tmpdir = tempfile.mkdtemp()
    yield Path(tmpdir)
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def temp_contador_file(temp_dir):
    """Crea un archivo contador temporal para tests."""
    contador_file = temp_dir / "contador_facturas.json"
    contador_file.write_text(json.dumps({"ultima_factura": 0}), encoding="utf-8")
    return contador_file


@pytest.fixture
def temp_env_file(temp_dir):
    """Crea un archivo .env temporal para tests."""
    env_file = temp_dir / ".env"
    env_content = """
LOG_LEVEL=DEBUG
LOG_FILE=logs/test.log
LOG_MAX_BYTES=1048576
LOG_BACKUP_COUNT=3
FACTURAS_DIR=facturas
"""
    env_file.write_text(env_content, encoding="utf-8")
    return env_file


@pytest.fixture
def caplog_handler(caplog):
    """Retorna el handler de caplog configurado para tests de logging."""
    caplog.set_level(logging.DEBUG)
    return caplog


@pytest.fixture
def sample_linea_factura_data():
    """Datos de ejemplo para crear una línea de factura."""
    return {
        "concepto": "Servicio profesional",
        "cantidad": 2,
        "precio_unitario": 50.00,
    }


@pytest.fixture
def sample_factura_data():
    """Datos de ejemplo para crear una factura completa."""
    return {
        "numero": 1,
        "fecha": date.today(),
        "cliente_nombre": "Cliente Test",
        "cliente_nif": "12345678A",
        "lineas": [
            {
                "concepto": "Servicio A",
                "cantidad": 1,
                "precio_unitario": 100.00,
            },
            {
                "concepto": "Servicio B",
                "cantidad": 2,
                "precio_unitario": 50.00,
            },
        ],
    }
