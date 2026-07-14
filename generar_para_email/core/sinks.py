# core/sinks.py
# Fan-out: una TransaccionComercial → dos sinks independientes.
#
# DISEÑO (patrón Outbox):
#   Cada sink marca su flag en SQLite al completar. Si falla, el flag queda
#   en 1 y ventas_store.recuperar_pendientes() lo recoge al próximo arranque.
#
# SINKS:
#   A) encolar_impresion → ESC/POS bytes → ColaPersistente → print_pendiente=0
#   B) anexar_a_excel    → Ticket doc  → archivo xlsx    → excel_pendiente=0
#
# NOTA: Las importaciones son lazy (dentro de las funciones) para evitar
#   dependencias circulares, ya que ventas_store importa este módulo
#   indirectamente a través de app.py.

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.domain import TransaccionComercial

logger = logging.getLogger(__name__)


def _construir_factura_y_pago(t: "TransaccionComercial"):
    """
    Adapta TransaccionComercial a los tipos de infraestructura legados
    (Factura + PagoInfo) que usan factura_writer y printer.
    """
    from src.factura_model import Factura, LineaFactura, PagoInfo

    lineas = [
        LineaFactura(
            concepto=item.descripcion,
            cantidad=item.cantidad,
            precio_unitario=item.precio_unitario,
            categoria=item.categoria,
        )
        for item in t.items
    ]
    factura = Factura(
        numero=t.numero_int,
        fecha=t.fecha_hora.date(),
        cliente_nombre=t.cliente_nombre,
        cliente_nif=t.cliente_nif,
        lineas=lineas,
    )
    pago = PagoInfo(
        monto_total=t.total,
        monto_efectivo=t.monto_efectivo,
        monto_tarjeta=t.monto_tarjeta,
        metodo_pago=t.metodo_pago,
        efectivo_entregado=t.efectivo_entregado,
        cambio=t.cambio,
    )
    return factura, pago


def encolar_impresion(t: "TransaccionComercial", cola, ancho: int = 42) -> None:
    """
    Sink A: genera bytecode ESC/POS y lo añade a la cola de impresión.

    Marca print_pendiente=0 en SQLite si la operación tiene éxito.
    Si falla, la excepción se propaga al caller (app.py) para que
    registre el estado y notifique al usuario.
    """
    from src.printer import generar_ticket_escpos
    from src.ventas_store import marcar_print_completado

    factura, pago = _construir_factura_y_pago(t)
    ticket_bytes = generar_ticket_escpos(factura, ancho=ancho, pago=pago)
    cola.append(ticket_bytes)
    marcar_print_completado(t.id_transaccion)
    logger.info(
        "✅ Ticket encolado: %s (cola: %d pendientes)",
        t.id_transaccion,
        len(cola),
    )


def anexar_a_excel(t: "TransaccionComercial") -> None:
    """
    Sink B: persiste la transacción en el archivo Excel de auditoría.

    Marca excel_pendiente=0 en SQLite al éxito.
    Si falla (archivo bloqueado, disco lleno), solo registra en logs;
    excel_pendiente=1 queda en DB para que recuperar_pendientes() lo reintente.
    """
    from tickets_src.ticket_model import Ticket, LineaTicket
    from tickets_src.excel_writer import guardar_ticket
    from src.ventas_store import marcar_excel_completado

    try:
        ticket_doc = Ticket(
            numero=t.numero_int,
            lineas=[
                LineaTicket(
                    nombre=item.descripcion,
                    cantidad=item.cantidad,
                    precio_unitario=item.precio_unitario,
                )
                for item in t.items
            ],
            fecha_hora=t.fecha_hora,
        )
        guardar_ticket(ticket_doc)
        marcar_excel_completado(t.id_transaccion)
        logger.info("✅ Excel de auditoría actualizado: %s", t.id_transaccion)
    except PermissionError as exc:
        logger.warning(
            "⚠️  Excel bloqueado para %s (excel_pendiente=1, se reintentará): %s",
            t.id_transaccion,
            exc,
        )
    except Exception as exc:
        logger.error(
            "❌ Error Excel para %s (excel_pendiente=1 en DB): %s",
            t.id_transaccion,
            exc,
            exc_info=True,
        )
