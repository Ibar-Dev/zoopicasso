#!/usr/bin/env python3
"""
conftest.py - Configuración de Playwright E2E Tests
====================================================

Configura:
- Lanzamiento del servidor FastAPI para tests
- Inicialización de fixtures de Playwright
- Setup/Teardown de base de datos
"""

import os
import sys
import time
import pytest
import subprocess
import requests
import signal
from pathlib import Path
from datetime import datetime
from typing import Generator

# Agregar src al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.ventas_store import inicializar_db_ventas


@pytest.fixture(scope="session")
def server_process() -> Generator:
    """
    Lanza servidor FastAPI en puerto 8000 para tests E2E.
    
    Espera a que el servidor esté listo antes de ejecutar los tests.
    """
    print("\n" + "="*70)
    print("🚀 Iniciando servidor FastAPI para tests E2E...")
    print("="*70)
    
    # Configurar puerto para tests
    os.environ["PORT"] = "8000"
    
    # Lanzar servidor FastAPI
    process = subprocess.Popen(
        [
            "python", "-m", "uvicorn",
            "web.app:app",
            "--host", "127.0.0.1",
            "--port", "8000",
            "--log-level", "info"
        ],
        cwd=Path(__file__).parent.parent.parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid,  # Crear nuevo session group en Linux
    )
    
    # Esperar a que el servidor esté listo
    max_retries = 60  # 60 segundos máximo
    retry_count = 0
    
    print("⏳ Esperando a que el servidor esté listo...")
    
    while retry_count < max_retries:
        try:
            response = requests.get(
                "http://127.0.0.1:8000/",
                timeout=2
            )
            if response.status_code == 200:
                print(f"✅ Servidor FastAPI listo en http://127.0.0.1:8000")
                print("="*70 + "\n")
                break
        except requests.exceptions.RequestException:
            retry_count += 1
            if retry_count % 10 == 0:
                print(f"   ⏳ Intento {retry_count}/{max_retries}...")
            time.sleep(1)
    
    if retry_count >= max_retries:
        print("❌ El servidor FastAPI no se inició correctamente")
        process.terminate()
        raise RuntimeError(
            "No se pudo conectar al servidor FastAPI en puerto 8000 después de 60 segundos"
        )
    
    yield process
    
    # Cleanup: Terminar el servidor
    print("\n" + "="*70)
    print("🛑 Deteniendo servidor FastAPI...")
    print("="*70)
    
    try:
        # Enviar SIGTERM al grupo de procesos
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        process.wait(timeout=5)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        # Si no terminó, forzar kill
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
    
    print("✅ Servidor FastAPI detenido\n")


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment(server_process):
    """
    Setup del entorno de pruebas.
    
    - Inicializar base de datos
    - Validar conexión al servidor
    """
    print("\n" + "="*70)
    print("📊 Configurando entorno de pruebas...")
    print("="*70)
    
    # Inicializar base de datos
    try:
        print("  📦 Inicializando base de datos de ventas...")
        inicializar_db_ventas()
        print("  ✅ Base de datos lista")
    except Exception as e:
        print(f"  ⚠️  Error al inicializar BD: {e}")
    
    # Validar que el servidor está respondiendo
    try:
        response = requests.get("http://127.0.0.1:8000/", timeout=5)
        assert response.status_code == 200
        print("  ✅ Servidor accesible")
    except Exception as e:
        raise RuntimeError(f"No se puede conectar al servidor: {e}")
    
    print("="*70 + "\n")
    
    yield


@pytest.fixture
def app_url() -> str:
    """URL base de la aplicación web para tests"""
    return "http://localhost:8000"


# Markers personalizados para pytest
def pytest_configure(config):
    """Registrar markers personalizados"""
    config.addinivalue_line(
        "markers", "slow: marca tests que son lentos"
    )
    config.addinivalue_line(
        "markers", "integration: marca tests de integración"
    )
    config.addinivalue_line(
        "markers", "login: marca tests que requieren login"
    )
    config.addinivalue_line(
        "markers", "invoice: marca tests de generación de facturas"
    )
    config.addinivalue_line(
        "markers", "printer: marca tests que usan impresora"
    )


# Hook para capturar errores y mostrar screenshots
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Genera reporte de test y captura información de fallos
    """
    outcome = yield
    
    if outcome.excinfo is not None:
        print(f"\n❌ Test fallido: {item.name}")
        if hasattr(item, '_playwright_page'):
            try:
                screenshot_path = f"screenshot_{item.name}_{int(time.time())}.png"
                item._playwright_page.screenshot(path=screenshot_path)
                print(f"📷 Screenshot guardado: {screenshot_path}")
            except Exception:
                pass
