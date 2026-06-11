"""
Configuración para tests end-to-end con Playwright.
Lanza servidor FastAPI en puerto 8001 para tests.
"""

import os
import sys
import time
import pytest
import subprocess
import requests
from pathlib import Path
from datetime import datetime

# Agregar src al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.ventas_store import (
    inicializar_db_ventas,
    registrar_ventas_factura,
    resumen_ventas_activas,
)
from src.factura_model import Factura, LineaFactura, PagoInfo


@pytest.fixture(scope="session", autouse=True)
def server_process():
    """Lanza servidor FastAPI para tests."""
    # Configurar puerto para tests
    os.environ["PORT"] = "8001"
    
    # Lanzar servidor FastAPI
    process = subprocess.Popen(
        ["uvicorn", "web.app:app", "--host", "127.0.0.1", "--port", "8001"],
        cwd=Path(__file__).parent.parent.parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    # Esperar a que el servidor esté listo
    max_retries = 30
    for i in range(max_retries):
        try:
            response = requests.get("http://127.0.0.1:8001/api/health", timeout=1)
            if response.status_code == 200:
                print(f"✅ Servidor FastAPI listo en puerto 8001 (intento {i+1})")
                break
        except requests.exceptions.RequestException:
            if i < max_retries - 1:
                time.sleep(1)
            else:
                raise RuntimeError(
                    "No se pudo conectar al servidor FastAPI después de 30 segundos"
                )
    
    yield process
    
    # Terminar servidor después de tests
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


@pytest.fixture(scope="session")
def base_url():
    """URL base para tests."""
    return "http://127.0.0.1:8001"


@pytest.fixture(scope="function")
def test_db():
    """Inicializar BD para tests y agregar datos de prueba."""
    # Inicializar BD
    inicializar_db_ventas()
    
    # Crear factura de prueba con ventas activas
    factura = Factura(
        numero=999,
        fecha=datetime.now().date(),
        cliente="Cliente Test",
        items=[
            LineaFactura(
                descripcion="Producto Test",
                cantidad=2.0,
                categoria="general",
                precio_unitario=100.0,
            )
        ],
        observaciones="Factura de prueba para tests",
        pago_info=PagoInfo(metodo="efectivo", monto_pago=200.0),
    )
    
    # Registrar ventas de la factura
    registrar_ventas_factura(
        factura_numero=999,
        usuario="Giselle",
        total=200.0,
        pago_metodo="efectivo",
        items=factura.items,
    )
    
    # Verificar que las ventas se registraron
    resumen = resumen_ventas_activas(datetime.now().strftime("%Y-%m"))
    print(f"✅ BD inicializada con {resumen['cantidad']} venta(s) activa(s)")
    
    yield
    
    # Limpiar después de test (opcional - dejar datos para debugging)
    # cleanup_test_db()

