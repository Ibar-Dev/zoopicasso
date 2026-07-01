#!/usr/bin/env python3
"""
test_printer_agent.py - Test y verificación del Agente de Impresión
====================================================================

Script para verificar que:
  1. Python está correctamente configurado
  2. Dependencias están instaladas
  3. Servidor está accesible
  4. Cola de impresión funciona
  5. Impresora USB está disponible
  6. Carpeta de tickets es escribible

Uso:
  python test_printer_agent.py
"""

import sys
import os
from pathlib import Path

# Estilos de output
class Style:
    """ANSI color codes para terminal"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_test(name: str, passed: bool, message: str = ""):
    """Imprime resultado de test"""
    status = f"{Style.GREEN}✓ PASS{Style.RESET}" if passed else f"{Style.RED}✗ FAIL{Style.RESET}"
    print(f"  {status}  {name}")
    if message:
        print(f"         {message}")


def print_section(title: str):
    """Imprime encabezado de sección"""
    print(f"\n{Style.BLUE}{Style.BOLD}═══ {title} ═══{Style.RESET}")


def test_imports():
    """Test 1: Verificar que pueden importarse las dependencias"""
    print_section("Test 1: Importar Dependencias")
    
    # Test: requests
    try:
        import requests
        print_test("requests", True)
    except ImportError as e:
        print_test("requests", False, f"pip install requests")
        return False
    
    # Test: src.printer (local)
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from src.printer import imprimir_ticket_usb_windows
        print_test("src.printer", True)
    except ImportError as e:
        print_test("src.printer", False, str(e))
        return False
    
    return True


def test_server_connection(url: str):
    """Test 2: Verificar conexión con servidor"""
    print_section("Test 2: Conexión con Servidor")
    
    import requests
    
    try:
        resp = requests.get(f"{url}/api/health", timeout=5)
        if resp.status_code == 200:
            print_test("Servidor accesible", True, f"GET {url}/api/health → 200 OK")
            return True
        else:
            print_test("Servidor accesible", False, f"Status: {resp.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_test("Servidor accesible", False, f"No hay conexión con {url}")
        return False
    except requests.exceptions.Timeout:
        print_test("Servidor accesible", False, "Timeout (servidor muy lento)")
        return False
    except Exception as e:
        print_test("Servidor accesible", False, str(e))
        return False


def test_printing_queue(url: str):
    """Test 3: Verificar cola de impresión"""
    print_section("Test 3: Cola de Impresión")
    
    import requests
    
    try:
        resp = requests.get(f"{url}/api/impresion/siguiente", timeout=5)
        
        if resp.status_code == 204:
            print_test("Cola de impresión", True, "Cola vacía (204 No Content)")
            return True
        elif resp.status_code == 200:
            datos = resp.json()
            hay_ticket = datos.get("hay_ticket", False)
            archivo = datos.get("archivo_xlsx", "N/A")
            print_test("Cola de impresión", True, 
                      f"Hay {1 if hay_ticket else 0} ticket(s), Excel: {archivo}")
            return True
        elif resp.status_code == 401:
            print_test("Cola de impresión", False, "No autenticado (401)")
            return False
        else:
            print_test("Cola de impresión", False, f"Status: {resp.status_code}")
            return False
    except Exception as e:
        print_test("Cola de impresión", False, str(e))
        return False


def test_printer_availability():
    """Test 4: Verificar disponibilidad de impresora USB"""
    print_section("Test 4: Impresora USB")
    
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from src.printer import listar_impresoras_usb
        
        impresoras = listar_impresoras_usb()
        if impresoras:
            for imp in impresoras:
                print_test(f"Impresora encontrada", True, imp)
            return True
        else:
            print_test("Impresora encontrada", False, 
                      "No hay impresoras USB conectadas.\n"
                      "         Conecta una impresora ESC/POS USB")
            return False
    except Exception as e:
        print_test("Impresora encontrada", False, f"Error: {e}")
        return False


def test_tickets_folder(folder_path: str):
    """Test 5: Verificar carpeta de tickets"""
    print_section("Test 5: Carpeta de Tickets")
    
    folder = Path(folder_path)
    
    # Test: existe
    if folder.exists():
        print_test("Carpeta existe", True, str(folder))
    else:
        # Intentar crear
        try:
            folder.mkdir(parents=True, exist_ok=True)
            print_test("Carpeta existe", True, f"Creada: {folder}")
        except Exception as e:
            print_test("Carpeta existe", False, f"No se pudo crear: {e}")
            return False
    
    # Test: escribible
    try:
        test_file = folder / ".test_write"
        test_file.write_text("test")
        test_file.unlink()
        print_test("Carpeta escribible", True)
        return True
    except Exception as e:
        print_test("Carpeta escribible", False, f"Error: {e}")
        return False


def test_config():
    """Test 6: Verificar configuración de variables de entorno"""
    print_section("Test 6: Configuración")
    
    url = os.getenv("PRINTER_SERVER_URL", "http://localhost:8000")
    folder = os.getenv("TICKETS_FOLDER", "C:/Facturas_Tickets/")
    poll_interval = os.getenv("POLL_INTERVAL", "3")
    reconnect_delay = os.getenv("RECONNECT_DELAY", "5")
    
    print(f"  {Style.YELLOW}ℹ{Style.RESET}  PRINTER_SERVER_URL = {url}")
    print(f"  {Style.YELLOW}ℹ{Style.RESET}  TICKETS_FOLDER = {folder}")
    print(f"  {Style.YELLOW}ℹ{Style.RESET}  POLL_INTERVAL = {poll_interval}s")
    print(f"  {Style.YELLOW}ℹ{Style.RESET}  RECONNECT_DELAY = {reconnect_delay}s")
    
    return True


def main():
    """Ejecuta todos los tests"""
    
    print(f"\n{Style.BOLD}{Style.BLUE}")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║  TEST Y VERIFICACIÓN: Agente de Impresión Local                   ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print(f"{Style.RESET}\n")
    
    # Obtener configuración
    url = os.getenv("PRINTER_SERVER_URL", "http://localhost:8000")
    folder = os.getenv("TICKETS_FOLDER", "C:/Facturas_Tickets/")
    
    results = []
    
    # Ejecutar tests
    results.append(("Importar dependencias", test_imports()))
    results.append(("Conexión con servidor", test_server_connection(url)))
    results.append(("Cola de impresión", test_printing_queue(url)))
    results.append(("Impresora USB", test_printer_availability()))
    results.append(("Carpeta de tickets", test_tickets_folder(folder)))
    
    test_config()
    
    # Resumen
    print_section("RESUMEN")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = f"{Style.GREEN}✓{Style.RESET}" if result else f"{Style.RED}✗{Style.RESET}"
        print(f"  {status}  {test_name}")
    
    print()
    if passed == total:
        print(f"{Style.GREEN}{Style.BOLD}✓ TODOS LOS TESTS PASARON{Style.RESET}")
        print(f"\nPuedes iniciar el agente:")
        print(f"  python poll_and_print.py")
        return 0
    else:
        print(f"{Style.YELLOW}{Style.BOLD}⚠ ALGUNOS TESTS FALLARON ({passed}/{total}){Style.RESET}")
        print(f"\nRevisa los errores arriba y ejecuta de nuevo.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
