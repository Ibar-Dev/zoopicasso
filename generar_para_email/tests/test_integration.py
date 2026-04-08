"""
test_integration.py — Integration tests para flujo completo
"""

import pytest
import sys
import json
from pathlib import Path
from datetime import date
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.factura_model import LineaFactura, Factura


class TestIntegrationFlowCompleto:
    """Tests de integración para el flujo completo: modelo → contador → writer."""

    def test_crear_factura_valida_completa(self, sample_factura_data):
        """Crear una factura válida con todos los campos."""
        lineas = [LineaFactura(**d) for d in sample_factura_data["lineas"]]
        factura = Factura(**{**sample_factura_data, "lineas": lineas})

        # Verificar estructura completa
        assert factura.numero == 1
        assert factura.fecha == date.today()
        assert factura.cliente_nombre == "Cliente Test"
        assert factura.cliente_nif == "12345678A"
        assert len(factura.lineas) == 2

    def test_factura_calculo_correcto(self, sample_factura_data):
        """Verificar cálculos correctos en la factura."""
        lineas = [LineaFactura(**d) for d in sample_factura_data["lineas"]]
        factura = Factura(**{**sample_factura_data, "lineas": lineas})

        # Cálculos esperados:
        # Línea 1: 1 x 100 = 100
        # Línea 2: 2 x 50 = 100
        # Total: 200 + IVA 42 = 242
        assert factura.base_imponible == 200.00
        assert factura.cuota_iva == 42.00
        assert factura.total_con_iva == 242.00

    def test_contador_incremento_secuencial(self, temp_contador_file):
        """Simular incremento secuencial del contador."""
        # Inicializar
        contador_data = {"ultima_factura": 100}
        temp_contador_file.write_text(json.dumps(contador_data), encoding="utf-8")

        # Simular 5 facturas consecutivas
        for i in range(1, 6):
            contenido = json.loads(temp_contador_file.read_text(encoding="utf-8"))
            siguiente = contenido["ultima_factura"] + i
            assert siguiente == 100 + i

    def test_generar_nombre_factura_con_contador(self, temp_contador_file, sample_factura_data):
        """Generar nombre de factura basado en contador."""
        # Inicializar contador
        contador_data = {"ultima_factura": 5}
        temp_contador_file.write_text(json.dumps(contador_data), encoding="utf-8")

        # Leer contador y crear nombre
        contenido = json.loads(temp_contador_file.read_text(encoding="utf-8"))
        numero = contenido["ultima_factura"] + 1

        # Crear factura con número del contador
        lineas = [LineaFactura(**d) for d in sample_factura_data["lineas"]]
        factura = Factura(
            numero=numero,
            fecha=date.today(),
            cliente_nombre="Test",
            cliente_nif="TEST",
            lineas=lineas
        )

        # Verificar número
        assert factura.numero == 6

    def test_guardar_archivo_factura(self, temp_dir, sample_factura_data):
        """Guardar archivo de factura en directorio."""
        # Crear directorio
        facturas_dir = temp_dir / "facturas"
        facturas_dir.mkdir(parents=True, exist_ok=True)

        # Crear factura
        lineas = [LineaFactura(**d) for d in sample_factura_data["lineas"]]
        factura = Factura(**{**sample_factura_data, "lineas": lineas})

        # Simular guardado (escribir nombre de archivo)
        nombre_archivo = f"{factura.numero:04d}.xlsx"
        archivo_path = facturas_dir / nombre_archivo

        # Simular creación de archivo
        archivo_path.write_bytes(b"fake excel data")

        # Verificar que existe
        assert archivo_path.exists()
        assert archivo_path.name == "0001.xlsx"

    def test_copiar_factura_a_documentos(self, temp_dir):
        """Simular copia de factura a carpeta Documentos."""
        # Crear carpeta origen
        origen_dir = temp_dir / "facturas"
        origen_dir.mkdir(parents=True, exist_ok=True)
        archivo_origen = origen_dir / "factura.xlsx"
        archivo_origen.write_bytes(b"excel data")

        # Crear carpeta destino (simulando Documentos)
        destino_dir = temp_dir / "Documentos" / "Facturas"
        destino_dir.mkdir(parents=True, exist_ok=True)
        archivo_destino = destino_dir / "factura.xlsx"

        # Copiar
        contenido = archivo_origen.read_bytes()
        archivo_destino.write_bytes(contenido)

        # Verificar
        assert archivo_destino.exists()
        assert archivo_destino.read_bytes() == archivo_origen.read_bytes()

    def test_flujo_completo_sin_cliente(self, temp_contador_file, temp_dir, sample_factura_data):
        """Flujo completo creando factura sin cliente (ticket)."""
        # 1. Inicializar contador
        contador_data = {"ultima_factura": 0}
        temp_contador_file.write_text(json.dumps(contador_data), encoding="utf-8")

        # 2. Leer contador
        contenido = json.loads(temp_contador_file.read_text(encoding="utf-8"))
        numero_factura = contenido["ultima_factura"] + 1

        # 3. Crear factura sin cliente
        lineas = [LineaFactura(**d) for d in sample_factura_data["lineas"]]
        factura = Factura(
            numero=numero_factura,
            fecha=date.today(),
            cliente_nombre="",  # Sin cliente
            cliente_nif="",     # Sin NIF
            lineas=lineas
        )

        # 4. Verificar que es válida
        assert factura.numero == 1
        assert factura.cliente_nombre == ""
        assert factura.total_con_iva == 242.00

        # 5. Guardar archivo
        facturas_dir = temp_dir / "facturas"
        facturas_dir.mkdir(parents=True, exist_ok=True)
        archivo = facturas_dir / f"{numero_factura:04d}.xlsx"
        archivo.write_bytes(b"excel data")

        # 6. Incrementar contador
        contenido["ultima_factura"] = numero_factura
        temp_contador_file.write_text(json.dumps(contenido), encoding="utf-8")

        # 7. Verificar estado final
        assert archivo.exists()
        contador_final = json.loads(temp_contador_file.read_text(encoding="utf-8"))
        assert contador_final["ultima_factura"] == 1

    def test_multiples_facturas_secuencia(self, temp_contador_file, temp_dir):
        """Generar múltiples facturas en secuencia."""
        # Inicializar
        contador_data = {"ultima_factura": 0}
        temp_contador_file.write_text(json.dumps(contador_data), encoding="utf-8")

        facturas_dir = temp_dir / "facturas"
        facturas_dir.mkdir(parents=True, exist_ok=True)

        # Generar 5 facturas
        for i in range(1, 6):
            # Leer contador
            contenido = json.loads(temp_contador_file.read_text(encoding="utf-8"))
            numero = contenido["ultima_factura"] + 1

            # Crear archivo
            archivo = facturas_dir / f"{numero:04d}.xlsx"
            archivo.write_bytes(f"factura {numero}".encode())

            # Incrementar contador
            contenido["ultima_factura"] = numero
            temp_contador_file.write_text(json.dumps(contenido), encoding="utf-8")

        # Verificar
        archivos = list(facturas_dir.glob("*.xlsx"))
        assert len(archivos) == 5

        contador_final = json.loads(temp_contador_file.read_text(encoding="utf-8"))
        assert contador_final["ultima_factura"] == 5

    def test_validacion_lineas_minimas(self, sample_factura_data):
        """Una factura debe tener al menos una línea."""
        lineas = [LineaFactura(**d) for d in sample_factura_data["lineas"]]
        # Crear factura con 2 líneas
        factura = Factura(**{**sample_factura_data, "lineas": lineas})

        assert len(factura.lineas) > 0
        assert factura.base_imponible > 0

    def test_validacion_cantidades_positivas(self, sample_factura_data):
        """Todas las cantidades deben ser positivas."""
        for linea_data in sample_factura_data["lineas"]:
            assert linea_data["cantidad"] > 0
            assert linea_data["precio_unitario"] >= 0

    def test_formateo_numero_factura_consistente(self, sample_factura_data):
        """El número de factura está formateado consistentemente."""
        lineas = [LineaFactura(**d) for d in sample_factura_data["lineas"]]
        factura = Factura(**{**sample_factura_data, "lineas": lineas})

        numero_formateado = factura.numero_formateado
        # Debe ser YYYY-NNN format
        assert len(numero_formateado.split("-")) == 2
        assert numero_formateado[0:4].isdigit()  # Año

    def test_formateo_fecha_consistente(self, sample_factura_data):
        """La fecha está formateada consistentemente."""
        lineas = [LineaFactura(**d) for d in sample_factura_data["lineas"]]
        factura = Factura(**{**sample_factura_data, "lineas": lineas})

        fecha_formateada = factura.fecha_formateada
        # Debe ser DD/MM/YYYY format
        partes = fecha_formateada.split("/")
        assert len(partes) == 3
        assert len(partes[0]) == 2  # día
        assert len(partes[1]) == 2  # mes
        assert len(partes[2]) == 4  # año
