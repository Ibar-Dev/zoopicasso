import hashlib
import importlib
import os
import sys
from datetime import date
from pathlib import Path


def _reset_project_paths():
    root = Path(__file__).resolve().parents[1]
    sys.path[:] = [p for p in sys.path if p not in {str(root), str(root / 'app_escritorio'), str(root / 'generar_para_email')}]
    sys.path.insert(0, str(root))
    return root


def test_app_escritorio_bootstrap_adds_project_paths():
    root = _reset_project_paths()

    module = importlib.import_module('app_escritorio.bootstrap')
    module.ensure_project_paths()

    assert str(root) in sys.path
    assert str(root / 'app_escritorio') in sys.path
    assert str(root / 'generar_para_email') in sys.path


def test_app_escritorio_main_imports_and_exposes_main_entrypoint():
    _reset_project_paths()

    module = importlib.import_module('app_escritorio.main')

    assert hasattr(module, 'main')
    assert callable(module.main)
    assert module._USUARIO_VALIDO == 'Giselle'


def test_app_escritorio_package_imports_ui_modules():
    _reset_project_paths()

    for name in [
        'app_escritorio.main',
        'app_escritorio.ui.email_view',
        'app_escritorio.ui.facturas_view',
        'app_escritorio.ui.tickets_view',
        'app_escritorio.ui.ventas_view',
    ]:
        module = importlib.import_module(name)
        assert module is not None


def test_login_credentials_are_valid():
    password = 'Gisellepicasso'
    expected_hash = '2aa2d838b21d5fe3fe9819640d83e40aea9f899d93b25a0ef9858ba9f83effda'
    assert hashlib.sha256(password.encode()).hexdigest() == expected_hash


def test_generating_invoice_excel_creates_file(tmp_path, monkeypatch):
    facturas_dir = tmp_path / 'facturas'
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'generar_para_email'))

    import src.factura_writer as factura_writer
    from src.factura_model import Factura, LineaFactura

    monkeypatch.setattr(factura_writer, 'RUTA_FACTURAS', facturas_dir)

    factura = Factura(
        numero=999,
        fecha=date.today(),
        cliente_nombre='Cliente prueba',
        cliente_nif='00000000T',
        lineas=[LineaFactura(concepto='Prueba', cantidad=1, precio_unitario=10.0, categoria='General')],
    )

    ruta = factura_writer.generar_factura_xlsx(factura)

    assert ruta.exists()
    assert ruta.suffix == '.xlsx'
    assert ruta.parent == facturas_dir
