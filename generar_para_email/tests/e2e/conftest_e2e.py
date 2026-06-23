"""
conftest.py específico para tests E2E con Playwright
"""
import pytest
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser


# Fixture para el navegador
@pytest.fixture(scope="session")
def browser_instance():
    """Crea una instancia de navegador para todos los tests"""
    # Usar un approach sincrono para evitar issues de event loop
    import subprocess
    import sys
    
    # Ejecutar en proceso separado si es necesario
    return None


@pytest.fixture
async def page(request):
    """Proporciona una página nueva para cada test"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        yield page
        
        await context.close()
        await browser.close()


@pytest.fixture
def base_url() -> str:
    """URL base de la aplicación"""
    return "http://localhost:8000"


@pytest.fixture
def db_path() -> Path:
    """Ruta de la BD SQLite"""
    return Path(__file__).parent.parent.parent / "data" / "ventas.db"


@pytest.fixture
def facturas_dir() -> Path:
    """Directorio de facturas"""
    return Path(__file__).parent.parent.parent / "facturas"
