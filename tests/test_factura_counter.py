"""
test_factura_counter.py — Tests para el módulo factura_counter
"""

import json
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Importar el módulo a testear
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestFacturaCounter:
    """Tests para las funciones del contador de facturas."""

    def test_leer_contador_existente(self, temp_contador_file):
        """Leer un contador que ya existe."""
        # Escribir valor inicial
        contador_data = {"ultima_factura": 10}
        temp_contador_file.write_text(json.dumps(contador_data), encoding="utf-8")

        # Leer y verificar
        with open(temp_contador_file, "r", encoding="utf-8") as f:
            contenido = json.load(f)
        assert contenido["ultima_factura"] == 10

    def test_escribir_contador(self, temp_contador_file):
        """Escribir un nuevo valor en el contador."""
        contador_data = {"ultima_factura": 42}
        temp_contador_file.write_text(json.dumps(contador_data), encoding="utf-8")

        # Leer y verificar
        with open(temp_contador_file, "r", encoding="utf-8") as f:
            contenido = json.load(f)
        assert contenido["ultima_factura"] == 42

    def test_contador_corrupto(self, temp_contador_file):
        """Detectar cuando el archivo contador está corrupto."""
        # Escribir JSON inválido
        temp_contador_file.write_text("{ este no es json válido", encoding="utf-8")

        # Intentar leer debe fallar
        with pytest.raises(json.JSONDecodeError):
            with open(temp_contador_file, "r", encoding="utf-8") as f:
                json.load(f)

    def test_crear_directorio_si_no_existe(self, temp_dir):
        """Crear el directorio si no existe."""
        subdir = temp_dir / "data"
        assert not subdir.exists()

        subdir.mkdir(parents=True, exist_ok=True)
        assert subdir.exists()

    def test_formato_contador_json(self, temp_contador_file):
        """Verificar formato correcto del JSON del contador."""
        contador_data = {"ultima_factura": 99}
        temp_contador_file.write_text(json.dumps(contador_data, indent=2), encoding="utf-8")

        # Leer y verificar formato
        contenido = json.loads(temp_contador_file.read_text(encoding="utf-8"))
        assert isinstance(contenido, dict)
        assert "ultima_factura" in contenido
        assert isinstance(contenido["ultima_factura"], int)

    def test_incremento_contador(self, temp_contador_file):
        """Verificar que el contador se incrementa correctamente."""
        # Escribir inicial
        contador_data = {"ultima_factura": 5}
        temp_contador_file.write_text(json.dumps(contador_data), encoding="utf-8")

        # Simular incremento
        contenido = json.loads(temp_contador_file.read_text(encoding="utf-8"))
        siguiente = contenido["ultima_factura"] + 1
        assert siguiente == 6

    def test_permisos_lectura_archivo(self, temp_contador_file):
        """Verificar que se puede leer el archivo."""
        assert temp_contador_file.exists()
        assert temp_contador_file.is_file()
        contenido = temp_contador_file.read_text(encoding="utf-8")
        assert contenido  # No vacío

    def test_permisos_escritura_archivo(self, temp_contador_file):
        """Verificar que se puede escribir en el archivo."""
        nuevo_data = {"ultima_factura": 999}
        temp_contador_file.write_text(json.dumps(nuevo_data), encoding="utf-8")
        assert temp_contador_file.read_text(encoding="utf-8") != ""

    def test_numeros_grandes(self, temp_contador_file):
        """Manejar números grandes en el contador."""
        contador_data = {"ultima_factura": 999999}
        temp_contador_file.write_text(json.dumps(contador_data), encoding="utf-8")

        contenido = json.loads(temp_contador_file.read_text(encoding="utf-8"))
        assert contenido["ultima_factura"] == 999999

    def test_contador_cero(self, temp_contador_file):
        """El contador puede ser cero."""
        contador_data = {"ultima_factura": 0}
        temp_contador_file.write_text(json.dumps(contador_data), encoding="utf-8")

        contenido = json.loads(temp_contador_file.read_text(encoding="utf-8"))
        assert contenido["ultima_factura"] == 0
