# printer.py
# Formatea y envía el ticket a la impresora térmica POS-80 vía USB (ESC/POS).
# Depende de python-escpos.
# En Windows requiere driver WinUSB instalado con Zadig para el dispositivo VID_1FC9 PID_2016.

import logging
import libusb_package
import usb.backend.libusb1
from escpos.printer import Usb
from src.ticket_model import Ticket, DIRECCION, TELEFONO, EMAIL

logger = logging.getLogger(__name__)

# Identificadores USB de la impresora POS-80.
# Obtenidos desde el PC Windows con Get-PnpDevice.
VENDOR_ID  = 0x1FC9
PRODUCT_ID = 0x2016

# Ancho estándar de rollo 80mm: 48 caracteres.
# Si se cambia a rollo 58mm, reducir a 32.
ANCHO_TICKET = 48


def _linea_separadora() -> str:
    """Devuelve una línea de guiones del ancho del ticket."""
    return "-" * ANCHO_TICKET


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
    Conecta con la impresora por USB y envía el ticket formateado.
    Esta es la única función pública del módulo.

    Args:
        ticket: Ticket completo y validado listo para imprimir.

    Raises:
        ConnectionError: Si no se puede conectar con la impresora USB.
        Exception: Cualquier error inesperado durante la impresión.
    """
    logger.info(f"Iniciando impresión del ticket #{ticket.numero} en USB {VENDOR_ID:#06x}:{PRODUCT_ID:#06x}")

    try:
        # Inyectar el backend de libusb explícitamente para Windows
        backend = usb.backend.libusb1.get_backend(find_library=lambda x: libusb_package.find())
        p = Usb(VENDOR_ID, PRODUCT_ID, backend=backend)

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
        p.text(_linea_separadora() + "\n")
        p.text(f"{DIRECCION}\n")
        p.text(f"Tel: {TELEFONO}\n")
        p.text(f"{EMAIL}\n")

        # Avance de papel y corte
        p.ln(3)
        p.cut()

        p.close()
        logger.info(f"Ticket #{ticket.numero} impreso correctamente.")

    except OSError as e:
        logger.error(f"No se pudo conectar con la impresora USB {VENDOR_ID:#06x}:{PRODUCT_ID:#06x}. Error: {e}")
        raise ConnectionError(f"Impresora no disponible. Verifica que está conectada y el driver WinUSB está instalado.\n{e}") from e
    except Exception as e:
        logger.error(f"Error inesperado durante la impresión del ticket #{ticket.numero}: {e}")
        raise