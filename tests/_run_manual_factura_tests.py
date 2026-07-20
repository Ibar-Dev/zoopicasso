#!/usr/bin/env python3
import sys
import os
import tempfile
from pathlib import Path
import importlib

print("Running manual factura xlsx tests")

# Asegurar que el repo raíz está en sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import src.factura_model as fm
import src.factura_writer as fw
import openpyxl
from datetime import date
from src.factura_model import LineaFactura, Factura

# Crear tmpdir
tmpdir = Path(tempfile.mkdtemp(prefix="factura_test_"))
print("tmpdir:", tmpdir)

# Forzar ruta de facturas al tmpdir
fw.RUTA_FACTURAS = tmpdir
print("RUTA_FACTURAS set to", fw.RUTA_FACTURAS)

# Caso exitoso
lineas = [LineaFactura(concepto="Item", cantidad=1, precio_unitario=10.0, categoria="General")]
factura = Factura(numero=1, fecha=date.today(), cliente_nombre="Test", cliente_nif="123", lineas=lineas)
ruta = fw.generar_factura_xlsx(factura)
print("Generated", ruta)
if not ruta.exists():
    print("FAIL: file not created")
    sys.exit(2)

wb = openpyxl.load_workbook(ruta)
print("Workbook title:", wb.active.title)
assert wb.active.title == f"Factura {factura.numero_formateado}"

# Simular PermissionError
orig_save = openpyxl.workbook.workbook.Workbook.save

def fake_save(self, *args, **kwargs):
    raise PermissionError("simulated permission error")

openpyxl.workbook.workbook.Workbook.save = fake_save
try:
    factura2 = Factura(numero=2, fecha=date.today(), cliente_nombre="T2", cliente_nif="456", lineas=lineas)
    try:
        fw.generar_factura_xlsx(factura2)
        print("FAIL: expected PermissionError")
        sys.exit(3)
    except PermissionError:
        print("PermissionError propagated as expected")
finally:
    openpyxl.workbook.workbook.Workbook.save = orig_save

print("OK")
sys.exit(0)
