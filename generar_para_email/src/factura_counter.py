# factura_counter.py
# Gestiona el número correlativo de facturas.
# Persiste el estado en un archivo JSON para sobrevivir reinicios de la app.
#
# Puntos CRÍTICOS de fallo:
# - Archivo contador_facturas.json corrupto o inaccesible
# - Permisos insuficientes para escribir en el directorio data/
# - Concurrencia: dos procesos leyendo/escribiendo simultáneamente

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Ruta relativa a la ubicación de este archivo, no al directorio de ejecución.
# Funciona igual en Linux (desarrollo) y Windows (instalación en casa de Gisselle).
_BASE = Path(__file__).resolve().parent.parent   # → generar_para_email/


def _ruta_contador_desde_env() -> Path:
    """Resuelve la ruta del contador desde CONTADOR_PATH o usa la ruta por defecto."""
    valor = os.getenv("CONTADOR_PATH", "").strip()
    if not valor:
        return (_BASE / "data" / "contador_facturas.json").resolve()

    ruta = Path(valor).expanduser()
    if not ruta.is_absolute():
        ruta = _BASE / ruta
    return ruta.resolve()


RUTA_CONTADOR = _ruta_contador_desde_env()


def _inicializar_contador() -> None:
    """Crea el archivo y directorio si no existen. Arranca desde 0."""
    try:
        RUTA_CONTADOR.parent.mkdir(parents=True, exist_ok=True)
        if not RUTA_CONTADOR.exists():
            logger.info(f"Contador de facturas no encontrado. Inicializando desde 0 en: {RUTA_CONTADOR}")
            _escribir(0)
        logger.debug(f"Contador inicializado/existente en: {RUTA_CONTADOR}")
    except OSError as e:
        logger.error(f"CRÍTICO: No se pudo acceder al directorio del contador: {e}", exc_info=True)
        raise


def _leer() -> int:
    try:
        with RUTA_CONTADOR.open("r", encoding="utf-8") as f:
            dato = json.load(f)
            valor = dato.get("ultima_factura", 0)
            logger.debug(f"Contador leído: {valor}")
            return valor
    except json.JSONDecodeError as e:
        logger.error(f"CRÍTICO: Archivo contador corrupto en {RUTA_CONTADOR}: {e}", exc_info=True)
        raise
    except IOError as e:
        logger.error(f"CRÍTICO: No se pudo leer el contador: {e}", exc_info=True)
        raise


def _escribir(valor: int) -> None:
    try:
        with RUTA_CONTADOR.open("w", encoding="utf-8") as f:
            json.dump({"ultima_factura": valor}, f, indent=2)
        logger.debug(f"Contador escrito: {valor} en {RUTA_CONTADOR}")
    except IOError as e:
        logger.error(f"CRÍTICO: No se pudo escribir el contador: {e}", exc_info=True)
        raise


def siguiente_numero_factura() -> int:
    """
    Incrementa el contador y devuelve el número a usar en la factura.
    Única función pública del módulo.
    
    Lanzará excepción si hay problemas con permisos o archivo corrupto.
    """
    try:
        _inicializar_contador()
        siguiente = _leer() + 1
        _escribir(siguiente)
        logger.info(f"Número de factura generado: {siguiente}")
        return siguiente
    except Exception as e:
        logger.error(f"CRÍTICO: Error fatal al generar número de factura: {e}", exc_info=True)
        raise
