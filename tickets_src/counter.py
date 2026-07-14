# counter.py
# Gestiona el número correlativo de tickets.
# Persiste el estado en un archivo JSON para sobrevivir reinicios de la app.

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Ruta del archivo donde se guarda el último número de ticket.
# Se crea automáticamente si no existe.
_BASE = Path(__file__).resolve().parent.parent   # → raíz del proyecto
RUTA_CONTADOR = _BASE / "data" / "contador.json"


def _inicializar_contador() -> None:
    """
    Crea el archivo y directorio si no existen.
    Arranca desde 0 — el primer ticket será el 1.
    """
    RUTA_CONTADOR.parent.mkdir(parents=True, exist_ok=True)
    if not RUTA_CONTADOR.exists():
        logger.info("Archivo de contador no encontrado. Inicializando desde 0.")
        _escribir(0)


def _leer() -> int:
    """Lee el valor actual del contador desde el JSON."""
    with RUTA_CONTADOR.open("r", encoding="utf-8") as f:
        datos = json.load(f)
    return datos["ultimo_ticket"]


def _escribir(valor: int) -> None:
    """Escribe el nuevo valor del contador en el JSON."""
    with RUTA_CONTADOR.open("w", encoding="utf-8") as f:
        json.dump({"ultimo_ticket": valor}, f, indent=2)


def siguiente_numero() -> int:
    """
    Incrementa el contador y devuelve el número a usar en el ticket.
    Esta función es el único punto de entrada público del módulo.

    Retorna:
        int: Número de ticket único y correlativo.
    """
    _inicializar_contador()

    numero_actual = _leer()
    siguiente = numero_actual + 1

    _escribir(siguiente)
    logger.info(f"Número de ticket generado: {siguiente}")

    return siguiente