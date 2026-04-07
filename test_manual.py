# test_manual.py
# Prueba de integración manual de todos los módulos antes de conectar la UI.
# Ejecutar desde la terminal: uv run test_manual.py
# No requiere Reflex. Valida modelo, contador, Excel e impresora de forma aislada.

import logging
import os

from src.ticket_model import Ticket, LineaTicket
from src.counter import siguiente_numero
from src.excel_writer import guardar_ticket
from src.printer import imprimir_ticket

# Configuración básica de logging para ver el comportamiento en consola
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


def construir_ticket_prueba() -> Ticket:
    """Construye un ticket de ejemplo con datos ficticios."""
    lineas = [
        LineaTicket(nombre="Baño completo", cantidad=1, precio_unitario=35.00),
        LineaTicket(nombre="Corte de pelo", cantidad=1, precio_unitario=20.00),
        LineaTicket(nombre="Limpieza de oídos", cantidad=2, precio_unitario=5.00),
    ]
    numero = siguiente_numero()
    return Ticket(numero=numero, lineas=lineas)


def main():
    logger.info("=== Iniciando test manual de integración ===")

    # 1. Construir el ticket
    ticket = construir_ticket_prueba()
    logger.info(f"Ticket construido: #{ticket.numero} | Total: {ticket.total:.2f} EUR")
    logger.info(f"Fecha: {ticket.fecha_formateada}")
    for linea in ticket.lineas:
        logger.info(f"  - {linea.nombre} | {linea.cantidad} x {linea.precio_unitario:.2f} = {linea.total:.2f}")

    # 2. Guardar en Excel
    logger.info("Guardando en Excel...")
    guardar_ticket(ticket)

    # 3. Imprimir
    if os.getenv("ZOO_PICASSO_TEST_PRINT", "0") == "1":
        logger.info("Enviando a impresora...")
        try:
            imprimir_ticket(ticket)
        except ConnectionError as error:
            logger.warning(f"No se pudo imprimir el ticket: {error}")
    else:
        logger.info(
            "Impresion omitida en el test manual. "
            "Usa ZOO_PICASSO_TEST_PRINT=1 para probar la impresora USB."
        )

    logger.info("=== Test completado ===")


if __name__ == "__main__":
    main()