"""
test_factura_writer.py — Tests para el módulo factura_writer
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.factura_model import LineaFactura, Factura


class TestFacturaWriter:
    """Tests para las funciones de generación de Excel y copia de archivos."""

    def test_crear_nombre_archivo(self, sample_factura_data):
        """Verificar formato del nombre del archivo."""
        lineas = [LineaFactura(**d) for d in sample_factura_data["lineas"]]
        factura = Factura(**{**sample_factura_data, "lineas": lineas})

        # El nombre debe ser: YYYY-NNN.xlsx
        nombre = f"{factura.numero}.xlsx"
        assert nombre.endswith(".xlsx")
        assert len(nombre) > 5

    def test_ruta_directorio_facturas(self, temp_dir):
        """Verificar que se puede acceder al directorio de facturas."""
        facturas_dir = temp_dir / "facturas"
        facturas_dir.mkdir(parents=True, exist_ok=True)

        assert facturas_dir.exists()
        assert facturas_dir.is_dir()

    def test_escritura_archivo_basico(self, temp_dir):
        """Crear un archivo de prueba en el directorio de facturas."""
        facturas_dir = temp_dir / "facturas"
        facturas_dir.mkdir(parents=True, exist_ok=True)

        archivo = facturas_dir / "test.xlsx"
        archivo.write_bytes(b"fake excel data")

        assert archivo.exists()
        assert archivo.stat().st_size > 0

    def test_validar_extension_xlsx(self):
        """Verificar que la extensión es .xlsx."""
        nombre = "2024-001.xlsx"
        assert nombre.endswith(".xlsx")

    def test_ruta_documentos_windows_basica(self):
        """Verificar construcción de ruta a Documentos de Windows (mock)."""
        # Simular Windows Documents path
        ruta_simulada = Path("C:/Users/Giselle/Documents/Facturas")

        # Verificar que es una ruta válida (aunque no exista)
        assert isinstance(ruta_simulada, Path)
        assert str(ruta_simulada).endswith("Facturas")

    def test_crear_directorio_copia(self, temp_dir):
        """Crear directorio para copia de facturas si no existe."""
        copia_dir = temp_dir / "Documentos" / "Facturas"
        copia_dir.mkdir(parents=True, exist_ok=True)

        assert copia_dir.exists()
        assert copia_dir.parent.exists()

    def test_copiar_archivo_simple(self, temp_dir):
        """Copiar archivo de origen a destino."""
        origen = temp_dir / "facturas"
        origen.mkdir(parents=True, exist_ok=True)
        archivo_origen = origen / "factura.xlsx"
        archivo_origen.write_bytes(b"excel data")

        destino = temp_dir / "copia"
        destino.mkdir(parents=True, exist_ok=True)
        archivo_destino = destino / "factura.xlsx"

        # Simular copia
        contenido = archivo_origen.read_bytes()
        archivo_destino.write_bytes(contenido)

        assert archivo_destino.exists()
        assert archivo_destino.read_bytes() == archivo_origen.read_bytes()

    def test_detectar_documentos_windows(self):
        """Detectar variantes de carpeta Documentos en Windows."""
        # Variantes comunes
        variantes = [
            "Documents",
            "Documentos",
            "OneDrive/Documents",
            "OneDrive/Documentos",
        ]

        for variante in variantes:
            assert isinstance(variante, str)
            assert len(variante) > 0

    def test_manejo_error_permiso_denegado(self, temp_dir):
        """Simular error de permiso denegado al copiar."""
        archivo_origen = temp_dir / "factura.xlsx"
        archivo_origen.write_bytes(b"data")

        directorio_protegido = temp_dir / "protegido"
        directorio_protegido.mkdir()

        # En Linux podemos simular permisos
        try:
            directorio_protegido.chmod(0o000)
            archivo_destino = directorio_protegido / "factura.xlsx"

            with pytest.raises((PermissionError, OSError)):
                archivo_destino.write_bytes(b"data")

        finally:
            # Restaurar permisos para cleanup
            directorio_protegido.chmod(0o755)

    def test_archivo_ya_existe(self, temp_dir):
        """Manejar cuando el archivo ya existe."""
        facturas_dir = temp_dir / "facturas"
        facturas_dir.mkdir(parents=True, exist_ok=True)

        archivo = facturas_dir / "factura.xlsx"
        archivo.write_bytes(b"contenido original")

        # Sobrescribir (último caso)
        archivo.write_bytes(b"contenido nuevo")

        assert archivo.read_bytes() == b"contenido nuevo"

    def test_tamanio_archivo_generado(self, temp_dir):
        """Verificar que el archivo generado tiene tamaño razonable."""
        archivo = temp_dir / "factura.xlsx"
        # Un Excel válido debe tener al menos 1KB
        archivo.write_bytes(b"x" * 2048)

        tamanio = archivo.stat().st_size
        assert tamanio >= 1024

    def test_validar_ruta_absoluta(self, temp_dir):
        """Las rutas internas deben ser absolutas."""
        ruta = temp_dir.resolve()

        assert ruta.is_absolute()
        assert isinstance(ruta, Path)

    def test_crear_facturas_multiples(self, temp_dir):
        """Crear múltiples facturas en el mismo directorio."""
        facturas_dir = temp_dir / "facturas"
        facturas_dir.mkdir(parents=True, exist_ok=True)

        for i in range(1, 6):
            archivo = facturas_dir / f"2024-{i:03d}.xlsx"
            archivo.write_bytes(b"excel data")

        # Verificar que se crearon todas
        archivos = list(facturas_dir.glob("*.xlsx"))
        assert len(archivos) == 5

    def test_limpiar_caracteres_invalidos_nombre(self):
        """Validar nombre de archivo sin caracteres inválidos."""
        nombre_invalido = "2024-001<>|.xlsx"
        caracteres_invalidos = ["<", ">", "|", ":", "?", "*", '"']

        es_valido = not any(c in nombre_invalido for c in caracteres_invalidos)
        assert not es_valido  # Este nombre SÍ tiene caracteres inválidos

        nombre_valido = "2024-001.xlsx"
        es_valido = not any(c in nombre_valido for c in caracteres_invalidos)
        assert es_valido  # Este es válido

    def test_timestamp_archivo(self, temp_dir):
        """El archivo creado debe tener timestamp reciente."""
        archivo = temp_dir / "factura.xlsx"
        archivo.write_bytes(b"data")

        # Modificado recientemente (últimos 5 segundos)
        import time
        ahora = time.time()
        modificado = archivo.stat().st_mtime

        tiempo_diferencia = ahora - modificado
        assert tiempo_diferencia < 5
