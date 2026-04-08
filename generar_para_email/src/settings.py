"""
settings.py — Configuración centralizada de la aplicación

Este módulo gestiona:
1. Carga de variables de entorno desde .env
2. Configuración de rutas (facturas, logs, etc.)
3. Sistema de logging centralizado con rotación de archivos

El logging se configura automáticamente al importar este módulo.
Cada módulo debe usar: logger = logging.getLogger(__name__)

Ejemplo de uso:
    from src import settings  # Configura logging automáticamente
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Mi mensaje")

Variables de entorno (.env):
    LOG_LEVEL=INFO                  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FILE=logs/app.log           # Ruta del archivo de log
    LOG_MAX_BYTES=5242880           # Tamaño máximo antes de rotar (5MB)
    LOG_BACKUP_COUNT=5              # Cantidad de logs rotativos a mantener
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path

# ── Rutas base ────────────────────────────────────────────────────────────────
_BASE = Path(__file__).resolve().parent.parent   # → generar_para_email/
ENV_PATH = _BASE / ".env"
LOGS_DIR = _BASE / "logs"


# ── Carga de variables de entorno ─────────────────────────────────────────────
def _cargar_env(path: Path) -> None:
    """Carga variables KEY=VALUE desde un .env simple sin dependencias externas."""
    if not path.exists():
        return

    for linea in path.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        key, value = linea.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def _ruta_desde_env(key: str, relativa_por_defecto: str) -> Path:
    valor = os.getenv(key, "").strip()
    if not valor:
        return (_BASE / relativa_por_defecto).resolve()
    ruta = Path(valor).expanduser()
    if not ruta.is_absolute():
        ruta = _BASE / ruta
    return ruta.resolve()


_cargar_env(ENV_PATH)

# ── Configuración de rutas ────────────────────────────────────────────────────
RUTA_FACTURAS_PRINCIPAL = _ruta_desde_env("FACTURAS_DIR", "facturas")


# ── Sistema de logging centralizado ───────────────────────────────────────────
def _configurar_logging() -> logging.Logger:
    """
    Configura y devuelve el logger raíz para toda la aplicación.
    
    Lee las configuraciones del .env:
    - LOG_LEVEL: DEBUG, INFO, WARNING, ERROR, CRITICAL (por defecto: INFO)
    - LOG_FILE: archivo de log (por defecto: logs/app.log)
    - LOG_MAX_BYTES: tamaño máximo de archivo antes de rotar (por defecto: 5MB)
    - LOG_BACKUP_COUNT: cantidad de archivos de log a mantener (por defecto: 5)
    """
    nivel_str = os.getenv("LOG_LEVEL", "INFO").upper()
    try:
        nivel = getattr(logging, nivel_str)
    except AttributeError:
        nivel = logging.INFO

    ruta_log = _ruta_desde_env("LOG_FILE", "logs/app.log")
    ruta_log.parent.mkdir(parents=True, exist_ok=True)

    # Formato detallado para el logging
    formato = (
        "[%(asctime)s] [%(levelname)-8s] [%(name)s:%(funcName)s:%(lineno)d] %(message)s"
    )
    fecha_formato = "%Y-%m-%d %H:%M:%S"

    # Logger raíz
    logger_raiz = logging.getLogger()
    logger_raiz.setLevel(nivel)
    logger_raiz.propagate = True

    # Limpiar handlers previos
    for handler in logger_raiz.handlers[:]:
        logger_raiz.removeHandler(handler)

    # Handler para consola (stderr)
    handler_consola = logging.StreamHandler(sys.stderr)
    handler_consola.setLevel(nivel)
    formateador = logging.Formatter(formato, datefmt=fecha_formato)
    handler_consola.setFormatter(formateador)
    logger_raiz.addHandler(handler_consola)

    # Handler para archivo con rotación
    try:
        max_bytes = int(os.getenv("LOG_MAX_BYTES", "5242880"))  # 5 MB
        backup_count = int(os.getenv("LOG_BACKUP_COUNT", "5"))
    except ValueError:
        max_bytes = 5242880
        backup_count = 5

    handler_archivo = logging.handlers.RotatingFileHandler(
        ruta_log,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler_archivo.setLevel(logging.DEBUG)  # Archivo siempre en DEBUG para detalle
    formateador_archivo = logging.Formatter(formato, datefmt=fecha_formato)
    handler_archivo.setFormatter(formateador_archivo)
    logger_raiz.addHandler(handler_archivo)

    return logger_raiz


# Configurar logging al importar este módulo
_configurar_logging()

# Logger para este módulo
logger = logging.getLogger(__name__)
logger.debug(f"Settings cargados desde: {ENV_PATH}")
logger.debug(f"Directorio de facturas: {RUTA_FACTURAS_PRINCIPAL}")
logger.debug(f"Directorio de logs: {LOGS_DIR}")


# ── Funciones auxiliares para logging ──────────────────────────────────────────
def get_logger(modulo: str) -> logging.Logger:
    """
    Función auxiliar para obtener un logger configurado para un módulo.
    
    Args:
        modulo: Típicamente __name__ del módulo que lo llama
        
    Returns:
        logging.Logger configurado con el sistema centralizado
        
    Ejemplo:
        logger = get_logger(__name__)
        logger.info("Mensaje de prueba")
    """
    return logging.getLogger(modulo)