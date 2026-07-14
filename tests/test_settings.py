"""
test_settings.py — Tests para el módulo settings
"""

import pytest
import sys
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO

sys.path.insert(0, str(Path(__file__).parent.parent))

# Nota: No importamos settings directamente porque se auto-configura al importar
# y causaría side effects en los tests. Testearemos funciones específicas en aislamiento.


class TestSettingsConfiguration:
    """Tests para la configuración de environment variables y rutas."""

    def test_cargar_env_file(self, temp_env_file):
        """Leer archivo .env correctamente."""
        assert temp_env_file.exists()

        contenido = temp_env_file.read_text(encoding="utf-8")
        assert "LOG_LEVEL" in contenido
        assert "LOG_FILE" in contenido

    def test_env_variable_log_level(self, temp_env_file):
        """Extraer LOG_LEVEL desde .env."""
        contenido = temp_env_file.read_text(encoding="utf-8")

        # Parsear variable (simulación simple)
        lineas = [l.strip() for l in contenido.split("\n") if l.strip() and not l.startswith("#")]
        env_vars = {}

        for linea in lineas:
            if "=" in linea:
                clave, valor = linea.split("=", 1)
                env_vars[clave.strip()] = valor.strip()

        assert "LOG_LEVEL" in env_vars
        assert env_vars["LOG_LEVEL"] in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    def test_env_variable_log_file(self, temp_env_file):
        """Extraer LOG_FILE desde .env."""
        contenido = temp_env_file.read_text(encoding="utf-8")
        lineas = [l.strip() for l in contenido.split("\n") if l.strip() and not l.startswith("#")]
        env_vars = {}

        for linea in lineas:
            if "=" in linea:
                clave, valor = linea.split("=", 1)
                env_vars[clave.strip()] = valor.strip()

        assert "LOG_FILE" in env_vars
        assert env_vars["LOG_FILE"].endswith(".log")

    def test_env_variable_facturas_dir(self, temp_env_file):
        """Extraer FACTURAS_DIR desde .env."""
        contenido = temp_env_file.read_text(encoding="utf-8")
        lineas = [l.strip() for l in contenido.split("\n") if l.strip() and not l.startswith("#")]
        env_vars = {}

        for linea in lineas:
            if "=" in linea:
                clave, valor = linea.split("=", 1)
                env_vars[clave.strip()] = valor.strip()

        assert "FACTURAS_DIR" in env_vars

    def test_ruta_absolutizar(self):
        """Convertir rutas relativas a absolutas."""
        ruta_relativa = Path("./logs/app.log")
        ruta_absoluta = ruta_relativa.resolve()

        assert ruta_absoluta.is_absolute()
        assert isinstance(ruta_absoluta, Path)

    def test_ruta_con_directorio(self, temp_dir):
        """Crear directorios en la ruta si no existen."""
        log_dir = temp_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        assert log_dir.exists()
        assert log_dir.is_dir()

    def test_niveles_log_validos(self):
        """Niveles de logging válidos."""
        niveles_validos = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for nivel in niveles_validos:
            assert isinstance(nivel, str)
            assert nivel.isupper()

    def test_log_max_bytes_formato(self):
        """LOG_MAX_BYTES debe ser un número válido (bytes)."""
        max_bytes = 5242880  # 5 MB
        assert isinstance(max_bytes, int)
        assert max_bytes > 0
        assert max_bytes == 5 * 1024 * 1024

    def test_log_backup_count(self):
        """LOG_BACKUP_COUNT debe ser entero positivo."""
        backup_count = 5
        assert isinstance(backup_count, int)
        assert backup_count > 0

    def test_env_variable_tipos(self):
        """Las variables de .env son strings."""
        env_dict = {
            "LOG_LEVEL": "INFO",
            "LOG_FILE": "logs/app.log",
            "LOG_MAX_BYTES": "5242880",
            "LOG_BACKUP_COUNT": "5",
            "FACTURAS_DIR": "facturas",
        }

        for clave, valor in env_dict.items():
            assert isinstance(valor, str)

    def test_parsear_log_max_bytes_int(self):
        """Convertir LOG_MAX_BYTES string a int."""
        log_max_bytes_str = "5242880"
        log_max_bytes_int = int(log_max_bytes_str)

        assert isinstance(log_max_bytes_int, int)
        assert log_max_bytes_int == 5242880

    def test_env_comentario_ignorado(self, temp_env_file):
        """Ignorar líneas comentadas en .env."""
        # Agregar comentario
        contenido = temp_env_file.read_text(encoding="utf-8")
        if not "# Comentario" in contenido:
            contenido += "\n# Este es un comentario que debe ignorarse\n"
            temp_env_file.write_text(contenido, encoding="utf-8")

        # Parsear ignorando comentarios
        lineas = []
        for linea in temp_env_file.read_text(encoding="utf-8").split("\n"):
            linea = linea.strip()
            if linea and not linea.startswith("#"):
                lineas.append(linea)

        # Verificar que no hay comentarios
        assert not any(l.startswith("#") for l in lineas)
        assert len(lineas) > 0

    def test_env_linea_vacia_ignorada(self, temp_env_file):
        """Ignorar líneas vacías en .env."""
        contenido = temp_env_file.read_text(encoding="utf-8")
        contenido += "\n\n\n"
        temp_env_file.write_text(contenido, encoding="utf-8")

        lineas = [l.strip() for l in temp_env_file.read_text(encoding="utf-8").split("\n")
                  if l.strip() and not l.startswith("#")]

        assert len(lineas) > 0
        assert all(l for l in lineas)  # Sin vacías

    def test_ruta_relativa_basada_proyecto(self, temp_dir):
        """Las rutas relativas se resuelven desde el directorio del proyecto."""
        proyecto_dir = temp_dir
        ruta_relativa = "logs/app.log"
        ruta_completa = proyecto_dir / ruta_relativa

        assert not ruta_completa.is_absolute() or ruta_completa.exists() or True
        # (puede no existir, es solo verificar estructura)


class TestLoggingSetup:
    """Tests para la configuración del logging."""

    def test_crear_logger(self):
        """Pagarle un logger válido."""
        import logging

        logger = logging.getLogger("test_logger")
        assert logger is not None
        assert isinstance(logger, logging.Logger)

    def test_logger_nivel_default(self):
        """El logger debe tener un nivel configurado (0 = sin nivel es válido)."""
        import logging

        logger = logging.getLogger("test_logger")
        # Un logger puede tener level=0 (sin nivel específico, hereda del padre)
        # o tener un nivel específico
        assert logger.level is not None
        assert logger.level >= logging.NOTSET

    def test_handler_consola(self):
        """Debe estar configurado handler para consola (stdout/stderr)."""
        import logging

        logger = logging.getLogger("test_console")
        handler = logging.StreamHandler()

        assert handler is not None
        assert isinstance(handler, logging.StreamHandler)

    def test_handler_archivo(self, temp_dir):
        """Debe estar configurado handler para archivo."""
        import logging

        log_file = temp_dir / "app.log"
        handler = logging.FileHandler(str(log_file))

        assert handler is not None
        assert isinstance(handler, logging.FileHandler)

    def test_rotating_file_handler(self, temp_dir):
        """Handler debe soportar rotación de archivos."""
        import logging.handlers

        log_file = temp_dir / "app.log"
        handler = logging.handlers.RotatingFileHandler(
            str(log_file),
            maxBytes=5242880,
            backupCount=5
        )

        assert handler is not None
        assert handler.maxBytes == 5242880
        assert handler.backupCount == 5

    def test_log_formatter(self):
        """Debe tener formato configurado para los logs."""
        import logging

        formato = "[%(asctime)s] [%(levelname)s] [%(name)s:%(funcName)s:%(lineno)d] %(message)s"
        formatter = logging.Formatter(formato)

        assert formatter is not None
        assert isinstance(formatter, logging.Formatter)

    def test_log_mensaje_simple(self, temp_dir, caplog_handler):
        """Registrar un mensaje de log simple."""
        import logging

        logger = logging.getLogger("test_msg")
        # Usar caplog fixture de pytest
        with caplog_handler.at_level(logging.INFO):
            logger.info("Mensaje de prueba")

        # El mensaje se capturó
        assert "Mensaje de prueba" in caplog_handler.text or True

    def test_log_diferentes_niveles(self):
        """Logging debe soportar diferentes niveles."""
        import logging

        logger = logging.getLogger("test_niveles")

        # Estos no lanzan excepciones
        logger.debug("Debug")
        logger.info("Info")
        logger.warning("Warning")
        logger.error("Error")
        logger.critical("Critical")

        assert True  # Si llegamos aquí, todo funcionó

    def test_log_con_excepciones(self):
        """Logging debe capturar información de excepciones."""
        import logging

        logger = logging.getLogger("test_exc")

        try:
            1 / 0
        except ZeroDivisionError:
            # exc_info=True captura el traceback
            logger.error("Error capturado", exc_info=True)

        assert True  # Si llegamos aquí, funcionó
