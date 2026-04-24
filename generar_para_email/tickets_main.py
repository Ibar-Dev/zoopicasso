# tickets_main.py
# Interfaz principal de tickets de Zoo Picasso usando Flet en modo web.
# Ejecutar desde esta carpeta: uv run tickets_main.py

import logging
from typing import Callable

import flet as ft

from tickets_src.counter import siguiente_numero
from tickets_src.excel_writer import guardar_ticket
from tickets_src.printer import imprimir_ticket
from tickets_src.ticket_model import LineaTicket, Ticket

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class FilaServicio:
    """Encapsula los controles de una linea de servicio en el formulario."""

    def __init__(self, on_change: Callable[[], None]):
        self.nombre = ft.TextField(
            label="Servicio",
            width=280,
            on_change=lambda _: on_change(),
        )
        self.cantidad = ft.TextField(
            label="Cant.",
            value="1",
            width=70,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=lambda _: self._recalcular(on_change),
        )
        self.precio = ft.TextField(
            label="P. Unit.",
            value="0.00",
            width=100,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=lambda _: self._recalcular(on_change),
        )
        self.total = ft.TextField(
            label="Total",
            value="0.00",
            width=100,
            read_only=True,
            bgcolor=ft.Colors.GREY_200,
        )

    def _recalcular(self, on_change: Callable[[], None]):
        try:
            cantidad = int(self.cantidad.value)
            precio = float(self.precio.value)
            self.total.value = f"{round(cantidad * precio, 2):.2f}"
        except ValueError:
            self.total.value = "0.00"
        on_change()

    def como_row(self) -> ft.Row:
        return ft.Row(
            controls=[self.nombre, self.cantidad, self.precio, self.total],
            alignment=ft.MainAxisAlignment.START,
        )

    def a_linea_ticket(self) -> LineaTicket:
        nombre = self.nombre.value.strip()
        if not nombre:
            raise ValueError("El nombre del servicio no puede estar vacio.")
        cantidad = int(self.cantidad.value)
        precio = float(self.precio.value)
        return LineaTicket(nombre=nombre, cantidad=cantidad, precio_unitario=precio)


def main(page: ft.Page):
    page.title = "Zoo Picasso - Tickets"
    page.window.width = 700
    page.window.height = 700
    page.padding = 20
    page.scroll = ft.ScrollMode.AUTO

    filas: list[FilaServicio] = []
    numero_ticket = siguiente_numero()

    contenedor_filas = ft.Column(spacing=6)

    lbl_numero = ft.Text(
        value=f"Ticket #{numero_ticket:04d}",
        size=13,
        color=ft.Colors.GREY_700,
    )

    lbl_total = ft.Text(
        value="0.00 EUR",
        size=20,
        weight=ft.FontWeight.BOLD,
        color=ft.Colors.GREEN_700,
    )

    lbl_estado = ft.Text(value="", color=ft.Colors.RED_600, size=13)

    def actualizar_total():
        try:
            total = sum(float(f.total.value) for f in filas)
            lbl_total.value = f"{total:.2f} EUR"
        except ValueError:
            lbl_total.value = "0.00 EUR"
        page.update()

    def agregar_fila(_=None):
        fila = FilaServicio(on_change=actualizar_total)
        filas.append(fila)
        contenedor_filas.controls.append(fila.como_row())
        logger.info("Fila anadida. Total filas: %s", len(filas))
        page.update()

    def quitar_fila(_=None):
        if len(filas) <= 1:
            lbl_estado.value = "El ticket debe tener al menos una linea."
            lbl_estado.color = ft.Colors.ORANGE_700
            page.update()
            return
        filas.pop()
        contenedor_filas.controls.pop()
        actualizar_total()
        logger.info("Fila eliminada. Total filas: %s", len(filas))

    def resetear():
        nonlocal numero_ticket
        filas.clear()
        contenedor_filas.controls.clear()
        numero_ticket = siguiente_numero()
        lbl_numero.value = f"Ticket #{numero_ticket:04d}"
        lbl_estado.value = ""
        agregar_fila()
        actualizar_total()
        logger.info("Formulario reseteado. Siguiente ticket: #%04d", numero_ticket)

    def imprimir(_=None):
        nonlocal numero_ticket
        try:
            lineas = [f.a_linea_ticket() for f in filas]
        except ValueError as e:
            lbl_estado.value = str(e)
            lbl_estado.color = ft.Colors.RED_600
            page.update()
            return

        ticket = Ticket(numero=numero_ticket, lineas=lineas)
        logger.info("Ticket #%s listo. Total: %.2f EUR", ticket.numero, ticket.total)

        try:
            guardar_ticket(ticket)
        except Exception as e:
            lbl_estado.value = f"Error al guardar en Excel: {e}"
            lbl_estado.color = ft.Colors.RED_600
            logger.error("Error al guardar ticket #%s: %s", ticket.numero, e)
            page.update()
            return

        try:
            imprimir_ticket(ticket)
        except ConnectionError as e:
            lbl_estado.value = f"Error de impresora: {e}"
            lbl_estado.color = ft.Colors.RED_600
            logger.error("Error de conexion con impresora: %s", e)
            page.update()
            return
        except Exception as e:
            lbl_estado.value = f"Error inesperado al imprimir: {e}"
            lbl_estado.color = ft.Colors.RED_600
            logger.error("Error inesperado al imprimir ticket #%s: %s", ticket.numero, e)
            page.update()
            return

        lbl_estado.value = f"Ticket #{ticket.numero:04d} impreso y guardado correctamente."
        lbl_estado.color = ft.Colors.GREEN_700
        page.update()
        resetear()

    cabecera = ft.Column(
        controls=[
            ft.Text("ZOO PICASSO", size=28, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
            lbl_numero,
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=2,
    )

    botones_filas = ft.Row(
        controls=[
            ft.Button("+ Anadir linea", on_click=agregar_fila),
            ft.Button("- Quitar linea", on_click=quitar_fila),
        ],
        alignment=ft.MainAxisAlignment.START,
    )

    fila_total = ft.Row(
        controls=[
            ft.Text("TOTAL:", size=18, weight=ft.FontWeight.BOLD),
            lbl_total,
        ],
        alignment=ft.MainAxisAlignment.END,
    )

    boton_imprimir = ft.Button(
        "IMPRIMIR TICKET",
        icon=ft.Icons.PRINT,
        bgcolor=ft.Colors.GREEN_700,
        color=ft.Colors.WHITE,
        height=50,
        width=260,
        on_click=imprimir,
    )

    page.add(
        cabecera,
        ft.Divider(),
        contenedor_filas,
        botones_filas,
        ft.Divider(),
        fila_total,
        ft.Divider(),
        ft.Row([boton_imprimir], alignment=ft.MainAxisAlignment.CENTER),
        lbl_estado,
    )

    agregar_fila()


ft.run(main, view=ft.AppView.WEB_BROWSER, port=8080)
