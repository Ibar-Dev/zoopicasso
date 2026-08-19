import logging
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Callable

import flet as ft

from escritorio.categorias import CATEGORIAS, METODOS_PAGO
from escritorio.config_app import cargar_config_smtp, config_smtp_completa
from escritorio.email_envio import enviar_factura_por_email
from src.factura_counter import siguiente_numero_factura
from src.factura_model import Factura, LineaFactura, PagoInfo
from src.factura_writer import RUTA_FACTURAS, generar_factura_xlsx
from src.printer import generar_ticket_escpos, imprimir_ticket_usb_windows
from src.ventas_store import registrar_ventas_factura

logger = logging.getLogger(__name__)

_PATRON_IMPORTE = r"^(0|[1-9]\d*)([\.,]\d{1,2})?$"


def _importe_valido(texto: str) -> bool:
    return bool(re.fullmatch(_PATRON_IMPORTE, texto.strip()))


class FilaConcepto:
    """Una linea de la factura con concepto, cantidad, precio, total y categoria."""

    def __init__(self, on_change: Callable[[], None]):
        self.concepto = ft.TextField(
            label="Concepto / Servicio",
            width=220,
            on_change=lambda _: on_change(),
        )
        self.cantidad = ft.TextField(
            label="Cant.",
            value="1",
            width=60,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=lambda _: self._recalcular(on_change),
        )
        self.precio = ft.TextField(
            label="P. Unit. (EUR, IVA incl.)",
            value="",
            hint_text="€",
            width=120,
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
            width=140,
            options=[ft.dropdown.Option(key=v, text=v) for v in CATEGORIAS],
        )

    def _recalcular(self, on_change: Callable[[], None]):
        try:
            precio_txt = self.precio.value.strip()
            if not _importe_valido(precio_txt):
                raise ValueError
            cantidad = int(self.cantidad.value)
            precio = float(precio_txt.replace(",", "."))
            self.total.value = f"{round(cantidad * precio, 2):.2f}"
        except ValueError:
            self.total.value = "0.00"
        on_change()

    def como_row(self) -> ft.Row:
        return ft.Row(
            controls=[self.concepto, self.cantidad, self.precio, self.total, self.categoria],
            alignment=ft.MainAxisAlignment.START,
            spacing=8,
        )

    def a_linea(self) -> LineaFactura:
        concepto = self.concepto.value.strip()
        if not concepto:
            raise ValueError("El concepto no puede estar vacío.")
        if not self.categoria.value:
            raise ValueError("Selecciona una categoría para cada línea.")
        cantidad = int(self.cantidad.value)
        precio_txt = self.precio.value.strip()
        if not _importe_valido(precio_txt):
            raise ValueError("Precio inválido (ej: 1100 o 1100.50).")
        precio = float(precio_txt.replace(",", "."))
        return LineaFactura(
            concepto=concepto,
            cantidad=cantidad,
            precio_unitario=precio,
            categoria=self.categoria.value,
        )


class FacturasView:
    """Pestana de facturas: genera el xlsx, registra la venta, imprime ticket
    y permite enviar la factura por email al cliente."""

    def __init__(self, page: ft.Page, usuario: str = ""):
        self.page = page
        self.usuario = usuario
        self.filas: list[FilaConcepto] = []
        self.numero_factura = siguiente_numero_factura()
        self.total_dia = 0.0
        self.facturas_dia = 0
        self.ultima_factura: Factura | None = None
        self.ultima_ruta: Path | None = None

        self.contenedor_filas = ft.Column(spacing=6)
        self.lbl_numero = ft.Text(
            value=f"Factura  {date.today().year}-{self.numero_factura:03d}",
            size=13,
            color=ft.Colors.GREY_700,
        )
        self.lbl_total = ft.Text(
            value="0.00 €",
            size=22,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.BLUE_800,
        )
        self.lbl_facturas_dia = ft.Text(value="0", size=15, weight=ft.FontWeight.BOLD)
        self.lbl_total_dia = ft.Text(value="0.00 €", size=15, weight=ft.FontWeight.BOLD)
        self.lbl_estado = ft.Text(value="", size=13)

        self.txt_cliente_nombre = ft.TextField(label="Nombre / Empresa del cliente (opcional)", width=280)
        self.txt_cliente_nif = ft.TextField(label="NIF / CIF (opcional)", width=160)
        self.txt_cliente_email = ft.TextField(
            label="Email del cliente (para enviar factura)",
            width=240,
            keyboard_type=ft.KeyboardType.EMAIL,
        )

        self.dd_metodo = ft.Dropdown(
            label="Método de pago",
            width=160,
            options=[ft.dropdown.Option(key=v, text=v.capitalize()) for v in METODOS_PAGO],
        )
        self.txt_efectivo = ft.TextField(label="Efectivo (€)", width=110, keyboard_type=ft.KeyboardType.NUMBER)
        self.txt_tarjeta = ft.TextField(label="Tarjeta (€)", width=110, keyboard_type=ft.KeyboardType.NUMBER)
        self.txt_entregado = ft.TextField(label="Efectivo entregado (€)", width=150, keyboard_type=ft.KeyboardType.NUMBER)
        self.lbl_cambio = ft.Text(value="Cambio: 0.00 €", size=13, color=ft.Colors.GREEN_800)

    # ── Construccion ──────────────────────────────────────────────────────────
    def construir(self) -> ft.Control:
        if not self.filas:
            self.agregar_fila()
        cabecera = ft.Column(
            controls=[
                ft.Text("FACTURAS", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800),
                self.lbl_numero,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=2,
        )
        bloque_cliente = ft.Column(
            controls=[
                ft.Text("DATOS DEL CLIENTE (OPCIONAL)", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_600),
                ft.Row(
                    controls=[self.txt_cliente_nombre, self.txt_cliente_nif, self.txt_cliente_email],
                    alignment=ft.MainAxisAlignment.START,
                    spacing=8,
                ),
            ],
            spacing=6,
        )
        bloque_pago = ft.Column(
            controls=[
                ft.Text("PAGO", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_600),
                ft.Row(
                    controls=[
                        self.dd_metodo,
                        self.txt_efectivo,
                        self.txt_tarjeta,
                        self.txt_entregado,
                        self.lbl_cambio,
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    spacing=8,
                ),
            ],
            spacing=6,
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
                ft.Text("FACTURAS DEL DÍA:", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_700),
                self.lbl_facturas_dia,
                ft.Text("ACUMULADO DEL DÍA:", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_700),
                self.lbl_total_dia,
            ],
            alignment=ft.MainAxisAlignment.END,
            spacing=8,
        )
        boton_generar = ft.Button(
            "GENERAR FACTURA",
            icon=ft.Icons.SAVE_ALT,
            bgcolor=ft.Colors.BLUE_800,
            color=ft.Colors.WHITE,
            height=52,
            width=280,
            on_click=self.generar,
        )
        boton_carpeta = ft.OutlinedButton(
            "ABRIR CARPETA DE FACTURAS",
            icon=ft.Icons.FOLDER_OPEN,
            height=52,
            width=280,
            on_click=self.abrir_carpeta,
        )
        return ft.Column(
            controls=[
                cabecera,
                ft.Divider(),
                bloque_cliente,
                ft.Divider(),
                ft.Text("LÍNEAS DE LA FACTURA", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_600),
                self.contenedor_filas,
                botones_filas,
                ft.Divider(),
                bloque_pago,
                ft.Divider(),
                fila_total,
                ft.Divider(),
                resumen_dia,
                ft.Divider(),
                ft.Row([boton_generar, boton_carpeta], alignment=ft.MainAxisAlignment.CENTER, spacing=12),
                self.lbl_estado,
            ],
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    # ── Acciones ──────────────────────────────────────────────────────────────
    def actualizar_totales(self):
        try:
            total = round(sum(float(f.total.value) for f in self.filas), 2)
            self.lbl_total.value = f"{total:.2f} €"
        except ValueError:
            self.lbl_total.value = "0.00 €"
        self._actualizar_cambio()
        self.page.update()

    def _actualizar_cambio(self):
        metodo = self.dd_metodo.value
        total = 0.0
        try:
            total = float(self.lbl_total.value.replace(" €", "").replace(",", "."))
        except ValueError:
            pass
        cambio = 0.0
        if metodo == "efectivo":
            try:
                entregado = float(self.txt_entregado.value.replace(",", "."))
                cambio = round(entregado - total, 2)
            except ValueError:
                cambio = 0.0
        self.lbl_cambio.value = f"Cambio: {cambio:.2f} €"
        self.lbl_cambio.color = ft.Colors.GREEN_800 if cambio >= 0 else ft.Colors.RED_700

    def agregar_fila(self, _=None):
        fila = FilaConcepto(on_change=self.actualizar_totales)
        self.filas.append(fila)
        self.contenedor_filas.controls.append(fila.como_row())
        self.page.update()

    def quitar_fila(self, _=None):
        if len(self.filas) <= 1:
            self._estado("La factura debe tener al menos una línea.", ft.Colors.ORANGE_700)
            return
        self.filas.pop()
        self.contenedor_filas.controls.pop()
        self.actualizar_totales()

    def _estado(self, mensaje: str, color: str):
        self.lbl_estado.value = mensaje
        self.lbl_estado.color = color
        self.page.update()

    def resetear(self):
        self.filas.clear()
        self.contenedor_filas.controls.clear()
        self.txt_cliente_nombre.value = ""
        self.txt_cliente_nif.value = ""
        self.txt_cliente_email.value = ""
        self.dd_metodo.value = None
        self.txt_efectivo.value = ""
        self.txt_tarjeta.value = ""
        self.txt_entregado.value = ""
        self.lbl_cambio.value = "Cambio: 0.00 €"
        self.numero_factura = siguiente_numero_factura()
        self.lbl_numero.value = f"Factura  {date.today().year}-{self.numero_factura:03d}"
        self.lbl_estado.value = ""
        self.agregar_fila()
        self.actualizar_totales()

    def abrir_carpeta(self, _=None):
        try:
            RUTA_FACTURAS.mkdir(parents=True, exist_ok=True)
            ruta = str(RUTA_FACTURAS)
            if sys.platform.startswith("win"):
                os.startfile(ruta)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", ruta], check=True)
            else:
                subprocess.run(["xdg-open", ruta], check=True)
        except Exception as e:
            self._estado(f"No se pudo abrir la carpeta: {e}", ft.Colors.RED_600)

    def _pago_info(self, total: float) -> PagoInfo | None:
        metodo = self.dd_metodo.value
        if metodo not in METODOS_PAGO:
            raise ValueError("Selecciona el método de pago.")

        def _monto(campo, nombre):
            texto = campo.value.strip()
            if not texto:
                raise ValueError(f"Indica el monto en {nombre}.")
            if not _importe_valido(texto):
                raise ValueError(f"Monto inválido en {nombre} (ej: 1100 o 1100.50).")
            return round(float(texto.replace(",", ".")), 2)

        efectivo = _monto(self.txt_efectivo, "efectivo") if metodo in ("efectivo", "mixto") else 0.0
        tarjeta = _monto(self.txt_tarjeta, "tarjeta") if metodo in ("tarjeta", "mixto") else 0.0
        tolerancia = 0.01

        if metodo == "efectivo":
            if abs(efectivo - total) > tolerancia:
                raise ValueError("El monto en efectivo debe ser igual al total.")
            entregado = _monto(self.txt_entregado, "efectivo entregado")
            if entregado < efectivo:
                raise ValueError("El efectivo entregado debe ser igual o mayor al total.")
            cambio = round(entregado - efectivo, 2)
        elif metodo == "tarjeta":
            if abs(tarjeta - total) > tolerancia:
                raise ValueError("El monto en tarjeta debe ser igual al total.")
            entregado, cambio = 0.0, 0.0
        else:  # mixto
            if abs(efectivo + tarjeta - total) > tolerancia:
                raise ValueError("La suma de efectivo y tarjeta debe ser igual al total.")
            entregado = _monto(self.txt_entregado, "efectivo entregado")
            if entregado < efectivo:
                raise ValueError("El efectivo entregado debe ser igual o mayor al efectivo a pagar.")
            cambio = round(entregado - efectivo, 2)

        return PagoInfo(
            monto_total=total,
            monto_efectivo=efectivo,
            monto_tarjeta=tarjeta,
            metodo_pago=metodo,
            efectivo_entregado=entregado,
            cambio=cambio,
        )

    def generar(self, _=None):
        try:
            lineas = [f.a_linea() for f in self.filas]
        except ValueError as e:
            self._estado(str(e), ft.Colors.RED_600)
            return

        factura = Factura(
            numero=self.numero_factura,
            fecha=date.today(),
            cliente_nombre=self.txt_cliente_nombre.value.strip(),
            cliente_nif=self.txt_cliente_nif.value.strip(),
            lineas=lineas,
        )

        try:
            pago = self._pago_info(factura.total_con_iva)
        except ValueError as e:
            self._estado(str(e), ft.Colors.RED_600)
            return

        try:
            ruta = generar_factura_xlsx(factura)
        except Exception as ex:
            self._estado(f"Error al generar factura: {ex}", ft.Colors.RED_600)
            logger.error("Error al generar factura %s: %s", factura.numero_formateado, ex, exc_info=True)
            return

        try:
            registrar_ventas_factura(factura, self.usuario, pago)
        except Exception as ex:
            logger.warning("No se pudo registrar la venta %s: %s", factura.numero_formateado, ex)

        self.facturas_dia += 1
        self.total_dia = round(self.total_dia + factura.total_con_iva, 2)
        self.lbl_facturas_dia.value = str(self.facturas_dia)
        self.lbl_total_dia.value = f"{self.total_dia:.2f} €"

        self.ultima_factura = factura
        self.ultima_ruta = ruta
        self._estado(f"✓ Factura {factura.numero_formateado} guardada en: {ruta}", ft.Colors.GREEN_700)
        self._mostrar_dialogo_opciones()

    def _mostrar_dialogo_opciones(self):
        factura = self.ultima_factura
        if factura is None:
            return

        def _cerrar():
            try:
                self.page.pop_dialog()
            except Exception:
                pass

        def _imprimir(_=None):
            _cerrar()
            try:
                ticket = generar_ticket_escpos(factura, ancho=42)
                impresora = imprimir_ticket_usb_windows(ticket)
                self.resetear()
                self._estado(f"Factura guardada y ticket impreso en: {impresora}", ft.Colors.GREEN_700)
            except Exception as ex:
                self.resetear()
                self._estado(f"Factura guardada, pero no se pudo imprimir: {ex}", ft.Colors.ORANGE_700)

        def _enviar_email(_=None):
            _cerrar()
            email_cliente = self.txt_cliente_email.value.strip()
            self.resetear()
            self._enviar_factura_email(factura, email_cliente)

        def _cerrar_y_resetear(_=None):
            _cerrar()
            self.resetear()

        acciones = [
            ft.TextButton("Cerrar", on_click=_cerrar_y_resetear),
            ft.TextButton("Enviar por email", icon=ft.Icons.EMAIL, on_click=_enviar_email),
            ft.FilledButton("Imprimir ticket", icon=ft.Icons.PRINT, on_click=_imprimir),
        ]
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Factura generada"),
            content=ft.Text(
                f"La factura {factura.numero_formateado} se guardó correctamente.\n"
                f"Cliente: {factura.cliente_nombre or '(sin cliente)'}\n"
                f"Total: {factura.total_con_iva:.2f} €\n\n"
                "¿Qué quieres hacer ahora?"
            ),
            actions=acciones,
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.show_dialog(dlg)

    def _enviar_factura_email(self, factura: Factura, email_cliente: str = ""):
        if not email_cliente:
            email_cliente = self.txt_cliente_email.value.strip()
        if not email_cliente:
            self._estado("Indica el email del cliente para enviar la factura.", ft.Colors.ORANGE_700)
            return
        cfg = cargar_config_smtp()
        ok, motivo = config_smtp_completa(cfg)
        if not ok:
            self._estado(f"Configura el envío de email primero (pestaña Configuración): {motivo}", ft.Colors.ORANGE_700)
            return
        try:
            enviar_factura_por_email(
                cfg,
                email_cliente,
                self.ultima_ruta,
                factura.numero_formateado,
                cliente=factura.cliente_nombre or "",
            )
            self._estado(f"✓ Factura {factura.numero_formateado} enviada a {email_cliente}", ft.Colors.GREEN_700)
        except Exception as ex:
            self._estado(f"No se pudo enviar la factura: {ex}", ft.Colors.RED_600)
            logger.error("Error enviando factura %s: %s", factura.numero_formateado, ex, exc_info=True)