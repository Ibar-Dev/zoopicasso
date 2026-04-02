# printer.py
# Formatea y envía el ticket a la impresora térmica pcCom Essential vía LAN (ESC/POS).
# Depende de python-escpos.

import logging
import os

from escpos.exceptions import DeviceNotFoundError
from escpos.printer import Network
from src.ticket_model import Ticket

logger = logging.getLogger(__name__)

# IP y puerto configurados en la impresora.
# Ajustar si cambia la configuración de red.
IMPRESORA_IP = os.getenv("ZOO_PICASSO_PRINTER_IP", "192.168.1.XXX")
IMPRESORA_PUERTO = int(os.getenv("ZOO_PICASSO_PRINTER_PORT", "9100"))

# Ancho estándar de rollo 58mm: 32 caracteres.
# Rollo 80mm: 48 caracteres. Ajustar según el rollo instalado.
ANCHO_TICKET = 32


def _linea_separadora() -> str:
    """Devuelve una línea de guiones del ancho del ticket."""
    return "-" * ANCHO_TICKET


def impresora_configurada() -> bool:
    """Indica si hay una IP real configurada para la impresora."""
    return bool(IMPRESORA_IP.strip()) and "XXX" not in IMPRESORA_IP


if not impresora_configurada():
    logger.warning(
        "Impresora no configurada. Define ZOO_PICASSO_PRINTER_IP con la IP real antes de imprimir."
    )


def _validar_configuracion_impresora() -> None:
    """Evita intentar imprimir con la configuración placeholder por defecto."""
    if not impresora_configurada():
        raise ConnectionError(
            "Impresora no configurada. Define ZOO_PICASSO_PRINTER_IP con la IP real antes de imprimir."
        )


def _formatear_linea_servicio(nombre: str, cantidad: int, precio_u: float, total: float) -> str:
    """
    Formatea una línea de servicio en dos subfilas:
      Fila 1: nombre del servicio
      Fila 2: cantidad x precio unitario = total (alineado a la derecha)
    """
    detalle = f"{cantidad} x {precio_u:.2f}EUR = {total:.2f}EUR"
    return f"{nombre}\n{detalle:>{ANCHO_TICKET}}"


def imprimir_ticket(ticket: Ticket) -> None:
    """
    Conecta con la impresora y envía el ticket formateado.
    Esta es la única función pública del módulo.

    Args:
        ticket: Ticket completo y validado listo para imprimir.

    Raises:
        ConnectionError: Si no se puede conectar con la impresora.
        Exception: Cualquier error durante la impresión.
    """
    _validar_configuracion_impresora()
    logger.info(f"Iniciando impresión del ticket #{ticket.numero} en {IMPRESORA_IP}:{IMPRESORA_PUERTO}")

    try:
        p = Network(IMPRESORA_IP, IMPRESORA_PUERTO)
        p.open()

        # --- CABECERA ---
        p.set(align="center", bold=True, double_height=True, double_width=True)
        p.text(ticket.nombre_negocio + "\n")

        p.set(align="center", bold=False, double_height=False, double_width=False)
        p.text(f"NIF: {ticket.nif}\n")
        p.text(f"Fecha: {ticket.fecha_formateada}\n")
        p.text(f"Ticket #: {ticket.numero:04d}\n")
        p.text(_linea_separadora() + "\n")

        # --- LÍNEAS DE SERVICIO ---
        p.set(align="left")
        for linea in ticket.lineas:
            p.text(
                _formatear_linea_servicio(
                    linea.nombre,
                    linea.cantidad,
                    linea.precio_unitario,
                    linea.total,
                ) + "\n"
            )

        # --- TOTAL ---
        p.text(_linea_separadora() + "\n")
        p.set(align="right", bold=True)
        p.text(f"TOTAL: {ticket.total:.2f} EUR\n")

        # --- PIE ---
        p.set(align="center", bold=False)
        p.text(_linea_separadora() + "\n")
        p.text("Gracias por su visita\n")
        p.text("Precios con IVA incluido\n")

        # Avance de papel y corte
        p.ln(3)
        p.cut()

        logger.info(f"Ticket #{ticket.numero} impreso correctamente.")

    except (OSError, DeviceNotFoundError) as e:
        logger.error(f"No se pudo conectar con la impresora en {IMPRESORA_IP}:{IMPRESORA_PUERTO}. Error: {e}")
        raise ConnectionError(f"Impresora no disponible: {e}") from e
    except Exception as e:
        logger.error(f"Error inesperado durante la impresión del ticket #{ticket.numero}: {e}")
        raise