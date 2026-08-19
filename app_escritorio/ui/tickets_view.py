import logging
from typing import Callable

import flet as ft

from escritorio.categorias import CATEGORIAS
from escritorio.registro import registrar_ventas_ticket
from tickets_src.counter import siguiente_numero
from tickets_src.excel_writer import guardar_ticket
from tickets_src.printer import imprimir_ticket
from tickets_src.ticket_model import LineaTicket, Ticket

logger = logging.getLogger(__name__)


class FilaServicio:
    """Una linea de servicio del ticket, con su categoria para el control de ventas."""

    def __init__(self, on_change: Callable[[], None]):
        self.nombre = ft.TextField(
            label="Servicio",
            width=240,
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
            label="P. Unit. (EUR)",
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
        self.categoria = ft.Dropdown(
            label="Categoría",
            width=150,
            options=[ft.dropdown.Option(key=v, text=v) for v in CATEGORIAS],
        )

    def _recalcular(self, on_change: Callable[[], None]):
        try:
            cantidad = int(self.cantidad.value)
            precio = float(self.precio.value.replace(",", "."))
            self.total.value = f"{round(cantidad * precio, 2):.2f}"
        except ValueError:
            self.total.value = "0.00"
        on_change()

    def como_row(self) -> ft.Row:
        return ft.Row(
            controls=[self.nombre, self.cantidad, self.precio, self.total, self.categoria],
            alignment=ft.MainAxisAlignment.START,
            spacing=8,
        )

    def a_linea_ticket(self) -> LineaTicket:
        nombre = self.nombre.value.strip()
        if not nombre:
            raise ValueError("El nombre del servicio no puede estar vacio.")
        cantidad = int(self.cantidad.value)
        precio = float(self.precio.value.replace(",", "."))
        return LineaTicket(nombre=nombre, cantidad=cantidad, precio_unitario=precio)


class TicketsView:
    """Pestana de tickets (TPV): genera, guarda en Excel, imprime y registra la venta."""

    def __init__(self, page: ft.Page, usuario: str = ""):
        self.page = page
        self.usuario = usuario
        self.filas: list[FilaServicio] = []
        self.numero_ticket = siguiente_numero()

        self.contenedor_filas = ft.Column(spacing=6)
        self.lbl_numero = ft.Text(
            value=f"Ticket #{self.numero_ticket:04d}",
            size=13,
            color=ft.Colors.GREY_700,
        )
        self.lbl_total = ft.Text(
            value="0.00 EUR",
            size=22,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.GREEN_700,
        )
        self.lbl_estado = ft.Text(value="", size=13)
        self.lbl_acumulado_dia = ft.Text(
            value="0.00 EUR",
            size=15,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.GREEN_700,
        )
        self.total_dia = 0.0
        self.tickets_dia = 0
        self.lbl_tickets_dia = ft.Text(value="0", size=15, weight=ft.FontWeight.BOLD)

    # ── Construccion ──────────────────────────────────────────────────────────
    def construir(self) -> ft.Control:
        if not self.filas:
            self.agregar_fila()
        cabecera = ft.Column(
            controls=[
                ft.Text("TICKETS", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_800),
                self.lbl_numero,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=2,
        )
        botones_filas = ft.Row(
            controls=[
                ft.Button("+ Añadir línea", icon=ft.Icons.ADD, on_click=self.agregar_fila),
                ft.OutlinedButton("- Quitar línea", icon=ft.Icons.REMOVE, on_click=self.quitar_fila),
            ],
            alignment=ft.MainAxisAlignment.START,
        )
        fila_total = ft.Row(
            controls=[
                ft.Text("TOTAL:", size=18, weight=ft.FontWeight.BOLD),
                self.lbl_total,
            ],
            alignment=ft.MainAxisAlignment.END,
        )
        resumen_dia = ft.Row(
            controls=[
                ft.Text("TICKETS DEL DÍA:", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_700),
                self.lbl_tickets_dia,
                ft.Text("ACUMULADO DEL DÍA:", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_700),
                self.lbl_acumulado_dia,
            ],
            alignment=ft.MainAxisAlignment.END,
            spacing=8,
        )
        boton_imprimir = ft.Button(
            "GUARDAR E IMPRIMIR TICKET",
            icon=ft.Icons.PRINT,
            bgcolor=ft.Colors.GREEN_700,
            color=ft.Colors.WHITE,
            height=52,
            width=320,
            on_click=self.imprimir,
        )
        return ft.Column(
            controls=[
                cabecera,
                ft.Divider(),
                self.contenedor_filas,
                botones_filas,
                ft.Divider(),
                fila_total,
                ft.Divider(),
                resumen_dia,
                ft.Divider(),
                ft.Row([boton_imprimir], alignment=ft.MainAxisAlignment.CENTER),
                self.lbl_estado,
            ],
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    # ── Acciones ──────────────────────────────────────────────────────────────
    def actualizar_total(self):
        try:
            total = sum(float(f.total.value) for f in self.filas)
            self.lbl_total.value = f"{total:.2f} EUR"
        except ValueError:
            self.lbl_total.value = "0.00 EUR"
        self.page.update()

    def agregar_fila(self, _=None):
        fila = FilaServicio(on_change=self.actualizar_total)
        self.filas.append(fila)
        self.contenedor_filas.controls.append(fila.como_row())
        self.page.update()

    def quitar_fila(self, _=None):
        if len(self.filas) <= 1:
            self._estado("El ticket debe tener al menos una línea.", ft.Colors.ORANGE_700)
            return
        self.filas.pop()
        self.contenedor_filas.controls.pop()
        self.actualizar_total()

    def resetear(self):
        self.filas.clear()
        self.contenedor_filas.controls.clear()
        self.numero_ticket = siguiente_numero()
        self.lbl_numero.value = f"Ticket #{self.numero_ticket:04d}"
        self.lbl_estado.value = ""
        self.agregar_fila()
        self.actualizar_total()

    def _estado(self, mensaje: str, color: str):
        self.lbl_estado.value = mensaje
        self.lbl_estado.color = color
        self.page.update()

    def imprimir(self, _=None):
        try:
            lineas = [f.a_linea_ticket() for f in self.filas]
        except ValueError as e:
            self._estado(str(e), ft.Colors.RED_600)
            return

        ticket = Ticket(numero=self.numero_ticket, lineas=lineas)

        try:
            guardar_ticket(ticket)
        except Exception as e:
            self._estado(f"Error al guardar en Excel: {e}", ft.Colors.RED_600)
            logger.error("Error al guardar ticket #%s: %s", ticket.numero, e)
            return

        try:
            registrar_ventas_ticket(
                ticket.numero,
                [
                    (fila.categoria.value, linea.total)
                    for fila, linea in zip(self.filas, lineas)
                ],
                self.usuario,
            )
        except Exception as e:
            logger.warning("No se pudo registrar la venta del ticket #%s: %s", ticket.numero, e)

        try:
            imprimir_ticket(ticket)
        except ConnectionError as e:
            self._estado(f"Ticket guardado, pero error de impresora: {e}", ft.Colors.ORANGE_700)
            return
        except Exception as e:
            self._estado(f"Ticket guardado, pero error al imprimir: {e}", ft.Colors.ORANGE_700)
            return

        self.tickets_dia += 1
        self.total_dia = round(self.total_dia + ticket.total, 2)
        self.lbl_tickets_dia.value = str(self.tickets_dia)
        self.lbl_acumulado_dia.value = f"{self.total_dia:.2f} EUR"
        self.resetear()
        self._estado(f"✓ Ticket #{ticket.numero:04d} impreso y guardado correctamente.", ft.Colors.GREEN_700)