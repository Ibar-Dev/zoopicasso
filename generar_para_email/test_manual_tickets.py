# test_manual_tickets.py
# Prueba de integracion manual de modulos de tickets.
# Ejecutar desde esta carpeta: uv run test_manual_tickets.py

import logging
import os

from tickets_src.ticket_model import Ticket, LineaTicket
from tickets_src.counter import siguiente_numero
from tickets_src.excel_writer import guardar_ticket
from tickets_src.printer import imprimir_ticket

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


def construir_ticket_prueba() -> Ticket:
    lineas = [
        LineaTicket(nombre="Bano completo", cantidad=1, precio_unitario=35.00),
        LineaTicket(nombre="Corte de pelo", cantidad=1, precio_unitario=20.00),
        LineaTicket(nombre="Limpieza de oidos", cantidad=2, precio_unitario=5.00),
    ]
    numero = siguiente_numero()
    return Ticket(numero=numero, lineas=lineas)


def main() -> None:
    logger.info("=== Iniciando test manual de integracion ===")

    ticket = construir_ticket_prueba()
    logger.info("Ticket construido: #%s | Total: %.2f EUR", ticket.numero, ticket.total)
    logger.info("Fecha: %s", ticket.fecha_formateada)
    for linea in ticket.lineas:
        logger.info(
            "  - %s | %s x %.2f = %.2f",
            linea.nombre,
            linea.cantidad,
            linea.precio_unitario,
            linea.total,
        )

    logger.info("Guardando en Excel...")
    guardar_ticket(ticket)

    if os.getenv("ZOO_PICASSO_TEST_PRINT", "0") == "1":
        logger.info("Enviando a impresora...")
        try:
            imprimir_ticket(ticket)
        except ConnectionError as error:
            logger.warning("No se pudo imprimir el ticket: %s", error)
    else:
        logger.info(
            "Impresion omitida en el test manual. "
            "Usa ZOO_PICASSO_TEST_PRINT=1 para probar la impresora USB."
        )

    logger.info("=== Test completado ===")


if __name__ == "__main__":
    main()
