#!/usr/bin/env python3
"""
run_e2e_tests.py - Script para ejecutar tests E2E de Playwright
================================================================

Proporciona una forma fácil de ejecutar diferentes suites de tests:
- Todos los tests
- Solo tests de generación de facturas
- Tests específicos
- Con reportes HTML

Uso:
    python tests/e2e/run_e2e_tests.py all              # Todos los tests
    python tests/e2e/run_e2e_tests.py invoice          # Solo facturas
    python tests/e2e/run_e2e_tests.py login            # Solo login
    python tests/e2e/run_e2e_tests.py --headed         # Ver navegador
    python tests/e2e/run_e2e_tests.py --html           # Con reporte HTML
"""

import sys
import subprocess
from pathlib import Path
from typing import List


def run_tests(
    test_filter: str = "all",
    headed: bool = False,
    html_report: bool = False,
    verbose: bool = True,
) -> int:
    """
    Ejecuta los tests E2E con la configuración especificada.
    
    Args:
        test_filter: Tipo de tests a ejecutar (all, invoice, login, etc.)
        headed: Si True, mostrar navegador (headless=False)
        html_report: Si True, generar reporte HTML
        verbose: Si True, output detallado
    
    Returns:
        Exit code de pytest
    """
    
    # Cambiar a directorio del proyecto
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    # Construir comando pytest
    cmd: List[str] = ["pytest", "tests/e2e/"]
    
    # Filtrar tests
    if test_filter == "invoice":
        cmd.append("test_invoice_generation_flow.py")
    elif test_filter == "money":
        cmd.append("test_money_pipeline_basic.py")
    elif test_filter == "cierres":
        cmd.append("test_cierres.py")
    elif test_filter == "excel":
        cmd.append("test_excel_verification.py")
    elif test_filter == "edge":
        cmd.append("test_edge_cases.py")
    # Para "all", no agregar filtro
    
    # Opciones de output
    if verbose:
        cmd.append("-v")
    
    # Reporte HTML
    if html_report:
        cmd.extend(["--html=tests/e2e/report.html", "--self-contained-html"])
    
    # Mostrar print statements
    cmd.append("-s")
    
    # Información de setup/teardown
    cmd.append("-ra")
    
    print("🧪 Ejecutando tests E2E")
    print("=" * 70)
    print(f"Directorio: {project_root}")
    print(f"Comando: {' '.join(cmd)}")
    print("=" * 70 + "\n")
    
    # Ejecutar pytest
    try:
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=False,
        )
        return result.returncode
    except KeyboardInterrupt:
        print("\n\n❌ Tests interrumpidos por el usuario")
        return 1
    except Exception as e:
        print(f"\n❌ Error al ejecutar tests: {e}")
        return 1


def main():
    """Punto de entrada del script"""
    
    # Parser simple de argumentos
    test_filter = "all"
    headed = False
    html_report = False
    verbose = True
    
    for arg in sys.argv[1:]:
        if arg in ("all", "invoice", "money", "cierres", "excel", "edge"):
            test_filter = arg
        elif arg == "--headed":
            headed = True
            print("⚠️  Modo headed: El navegador será visible")
        elif arg == "--html":
            html_report = True
            print("📊 Se generará reporte HTML")
        elif arg == "-q":
            verbose = False
        elif arg in ("-h", "--help"):
            print(__doc__)
            return 0
    
    # Ejecutar tests
    exit_code = run_tests(
        test_filter=test_filter,
        headed=headed,
        html_report=html_report,
        verbose=verbose,
    )
    
    # Mostrar resultado
    print("\n" + "=" * 70)
    if exit_code == 0:
        print("✅ Tests completados exitosamente")
    else:
        print(f"❌ Tests fallaron (exit code: {exit_code})")
    print("=" * 70 + "\n")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
