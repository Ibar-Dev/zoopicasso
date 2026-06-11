"""
Tests end-to-end con Playwright para el sistema de cierres.

Verifica:
- Botones de cierre visibles
- Modales se abren
- Respuestas del API
"""

import pytest
import httpx


def test_ui_page_loads(base_url, page):
    """Verifica que la página principal carga correctamente."""
    page.goto(f"{base_url}/")
    page.wait_for_load_state("networkidle")
    
    # Verificar que la página tiene contenido
    title = page.title()
    assert title, "La página debe tener un título"
    
    # Verificar que hay un body
    content = page.locator("body").inner_text()
    assert len(content) > 0, "La página debe tener contenido"


def test_botones_cierre_visibles(base_url, page):
    """Verifica que los botones de cierre están visibles en la UI."""
    page.goto(f"{base_url}/")
    page.wait_for_load_state("networkidle")
    
    # Verificar que los botones existen
    btn_cierre_dia = page.locator("#btn-cierre-dia")
    btn_cierre_mes = page.locator("#btn-cierre-mes")
    
    assert btn_cierre_dia.count() > 0, "Botón 'Cierre del Día' debe existir"
    assert btn_cierre_mes.count() > 0, "Botón 'Cierre del Mes' debe existir"
    
    # Verificar que son visibles
    assert btn_cierre_dia.is_visible(), "Botón 'Cierre del Día' debe ser visible"
    assert btn_cierre_mes.is_visible(), "Botón 'Cierre del Mes' debe ser visible"


def test_modal_cierre_dia_se_abre(base_url, page):
    """Verifica que el modal para cierre de día se abre al hacer click."""
    page.goto(f"{base_url}/")
    page.wait_for_load_state("networkidle")
    
    # Click en botón "Cierre del Día"
    btn_cierre_dia = page.locator("#btn-cierre-dia")
    btn_cierre_dia.click()
    
    # Esperar a que el modal sea visible
    modal = page.locator(".modal")
    page.wait_for_timeout(500)
    
    # Verificar que el modal existe
    assert modal.count() > 0, "Modal debe aparecer después de click"


def test_modal_cierre_mes_se_abre(base_url, page):
    """Verifica que el modal para cierre de mes se abre al hacer click."""
    page.goto(f"{base_url}/")
    page.wait_for_load_state("networkidle")
    
    # Click en botón "Cierre del Mes"
    btn_cierre_mes = page.locator("#btn-cierre-mes")
    btn_cierre_mes.click()
    
    # Esperar a que el modal sea visible
    modal = page.locator(".modal")
    page.wait_for_timeout(500)
    
    # Verificar que el modal existe
    assert modal.count() > 0, "Modal debe aparecer después de click"


def test_api_health_check(base_url):
    """Verifica que el servidor está funcionando."""
    response = httpx.get(f"{base_url}/api/health")
    assert response.status_code == 200, "Health check debe retornar 200"
    data = response.json()
    assert "status" in data or "ok" in data, "Health check debe retornar datos"


def test_api_endpoint_cierre_dia_existe(base_url):
    """Verifica que el endpoint POST /api/ganancias/cierre-dia existe y responde."""
    response = httpx.post(
        f"{base_url}/api/ganancias/cierre-dia",
        json={"confirmacion": False},  # Sin confirmación
    )
    
    # Debe retornar un status (no error de conexión)
    assert response.status_code in [302, 400, 401, 403], \
        f"Endpoint debe responder (recibido: {response.status_code})"


def test_api_endpoint_cierre_mes_existe(base_url):
    """Verifica que el endpoint POST /api/ganancias/cierre-mes existe y responde."""
    response = httpx.post(
        f"{base_url}/api/ganancias/cierre-mes",
        json={"confirmacion": False},  # Sin confirmación
    )
    
    # Debe retornar un status (no error de conexión)
    assert response.status_code in [302, 400, 401, 403], \
        f"Endpoint debe responder (recibido: {response.status_code})"

