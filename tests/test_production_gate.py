import hashlib
import importlib
import importlib.util
import sys
from datetime import date
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _add_project_paths() -> None:
    root = _project_root()
    for path in (root, root / 'app_escritorio', root / 'generar_para_email'):
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)


def _load_module_from_path(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_add_project_paths()


def test_entrypoints_import_for_production_gate():
    root = _project_root()

    modules = [
        importlib.import_module('app_escritorio.main'),
        _load_module_from_path('zoo_picasso_facturas_main', root / 'generar_para_email' / 'main.py'),
        _load_module_from_path('zoo_picasso_tickets_main', root / 'generar_para_email' / 'tickets_main.py'),
        _load_module_from_path('zoo_picasso_web_app', root / 'generar_para_email' / 'web' / 'app.py'),
    ]

    for module in modules:
        assert module is not None


def test_login_hash_matches_production_credential():
    expected_hash = '2aa2d838b21d5fe3fe9819640d83e40aea9f899d93b25a0ef9858ba9f83effda'
    assert hashlib.sha256('Gisellepicasso'.encode()).hexdigest() == expected_hash


def test_invoice_generation_writes_xlsx_to_target(tmp_path):
    from src.factura_model import Factura, LineaFactura
    import src.factura_writer as factura_writer

    target_dir = tmp_path / 'facturas'
    factura_writer.RUTA_FACTURAS = target_dir

    factura = Factura(
        numero=999,
        fecha=date.today(),
        cliente_nombre='Cliente prueba',
        cliente_nif='00000000T',
        lineas=[LineaFactura(concepto='Prueba', cantidad=1, precio_unitario=10.0, categoria='General')],
    )

    ruta = factura_writer.generar_factura_xlsx(factura)

    assert ruta.exists()
    assert ruta.parent == target_dir
    assert ruta.suffix == '.xlsx'


def test_ticket_generation_writes_xlsx_to_target(tmp_path):
    from tickets_src.excel_writer import guardar_ticket
    from tickets_src.ticket_model import LineaTicket, Ticket
    import tickets_src.excel_writer as ticket_writer

    target_file = tmp_path / 'tickets.xlsx'
    ticket_writer.RUTA_EXCEL = target_file

    ticket = Ticket(numero=1, lineas=[LineaTicket(nombre='Servicio prueba', cantidad=1, precio_unitario=15.0)])

    guardar_ticket(ticket)

    assert target_file.exists()


def test_sales_database_gate(tmp_path):
    import src.ventas_store as ventas_store
    from src.factura_model import Factura, LineaFactura, PagoInfo

    target_db = tmp_path / 'ventas.db'
    ventas_store.RUTA_DB_VENTAS = target_db

    factura = Factura(
        numero=123,
        fecha=date.today(),
        cliente_nombre='Cliente prueba',
        cliente_nif='00000000T',
        lineas=[LineaFactura(concepto='Prueba', cantidad=2, precio_unitario=12.5, categoria='General')],
    )
    pago = PagoInfo(
        monto_total=factura.total_con_iva,
        monto_efectivo=factura.total_con_iva,
        monto_tarjeta=0.0,
        metodo_pago='efectivo',
        efectivo_entregado=factura.total_con_iva,
        cambio=0.0,
    )

    ventas_store.registrar_ventas_factura(factura, 'tester', pago)
    resumen = ventas_store.resumen_ventas_activas(date.today().strftime('%Y-%m'))

    assert target_db.exists()
    assert resumen['cantidad_ventas'] == 1
    assert round(resumen['total'], 2) == factura.total_con_iva
