# main.py — Generador de Facturas · Gisselle Marin Tabares
# Ejecutar desde la raíz del proyecto: uv run generar_para_email/main.py
# Abre el navegador en localhost:8081

import hashlib
import logging
import os
import shutil
import subprocess
import sys
import re
from datetime import date
from pathlib import Path
from typing import Callable

import flet as ft

# ── Credenciales de acceso ────────────────────────────────────────────────────
_USUARIO_VALIDO = "Giselle"
_HASH_PASSWORD = "2aa2d838b21d5fe3fe9819640d83e40aea9f899d93b25a0ef9858ba9f83effda"

# Permite importar src.* relativo a esta carpeta cuando se ejecuta
# desde la raíz del proyecto (uv run generar_para_email/main.py).
sys.path.insert(0, str(Path(__file__).parent))

# Carga la configuración centralizada de logging
import src.settings  # noqa: E402
from src.factura_counter import siguiente_numero_factura
from src.factura_model import LineaFactura
from src.factura_model import Factura
from src.factura_writer import RUTA_FACTURAS
from src.factura_writer import generar_factura_xlsx

logger = logging.getLogger(__name__)


def _normalizar_importe(valor: float) -> str:
    return f"{valor:.2f} EUR"


def _comprimir_texto(texto: str, max_chars: int) -> str:
    texto = " ".join(texto.split())
    if len(texto) <= max_chars:
        return texto
    if max_chars <= 3:
        return texto[:max_chars]
    return texto[: max_chars - 3] + "..."


def _generar_ticket_escpos(factura: Factura, ancho: int = 42) -> bytes:
    """Construye ticket ESC/POS para papel de 80mm usando maquetado de 72mm."""
    lineas: list[bytes] = []

    def cmd(x: bytes) -> None:
        lineas.append(x)

    def txt(s: str = "") -> None:
        lineas.append((s + "\n").encode("cp850", errors="replace"))

    def separador(char: str = "-") -> None:
        txt(char * ancho)

    # Init + centrado cabecera
    cmd(b"\x1b@")
    cmd(b"\x1ba\x01")
    cmd(b"\x1bE\x01")
    txt("ZOO PICASSO")
    cmd(b"\x1bE\x00")
    txt("Ticket de venta")
    txt(f"Factura {factura.numero_formateado}")
    txt(f"Fecha {factura.fecha_formateada}")
    cmd(b"\x1ba\x00")
    separador()

    if factura.cliente_nombre:
        txt("Cliente: " + _comprimir_texto(factura.cliente_nombre, ancho - 9))
    if factura.cliente_nif:
        txt("NIF/CIF: " + _comprimir_texto(factura.cliente_nif, ancho - 9))
    if factura.cliente_nombre or factura.cliente_nif:
        separador()

    txt("Concepto")
    txt("Cant x P.Unit                      Total")
    separador()

    for linea in factura.lineas:
        txt(_comprimir_texto(linea.concepto, ancho))
        detalle = f"{linea.cantidad} x {_normalizar_importe(linea.precio_unitario)}"
        total = _normalizar_importe(linea.total)
        espacio = max(1, ancho - len(detalle) - len(total))
        txt(detalle + (" " * espacio) + total)

    separador()
    total = _normalizar_importe(factura.total_con_iva)
    etiqueta = "TOTAL"
    espacio_total = max(1, ancho - len(etiqueta) - len(total))
    cmd(b"\x1bE\x01")
    txt(etiqueta + (" " * espacio_total) + total)
    cmd(b"\x1bE\x00")
    txt("IVA incluido")
    separador()
    cmd(b"\x1ba\x01")
    txt("Gracias por tu compra")
    txt("Zoo Picasso")

    # Avance y corte total
    cmd(b"\n\n\n")
    cmd(b"\x1dV\x00")
    return b"".join(lineas)


def _imprimir_ticket_usb_windows(ticket: bytes) -> str:
    """Imprime ticket ESC/POS en impresora predeterminada de Windows por RAW."""
    if not sys.platform.startswith("win"):
        raise RuntimeError("La impresion ESC/POS USB esta habilitada solo en Windows.")

    try:
        import win32print  # type: ignore[import-not-found]
    except Exception as ex:
        raise RuntimeError(
            "No se encontro pywin32. Ejecuta sincronizacion de dependencias en Windows."
        ) from ex

    impresora = os.getenv("ESC_POS_PRINTER_NAME", "").strip() or win32print.GetDefaultPrinter()
    if not impresora:
        raise RuntimeError("No hay impresora predeterminada disponible.")

    hprinter = win32print.OpenPrinter(impresora)
    try:
        hjob = win32print.StartDocPrinter(hprinter, 1, ("Ticket factura", "", "RAW"))
        try:
            win32print.StartPagePrinter(hprinter)
            win32print.WritePrinter(hprinter, ticket)
            win32print.EndPagePrinter(hprinter)
        finally:
            win32print.EndDocPrinter(hprinter)
    finally:
        win32print.ClosePrinter(hprinter)

    return impresora


class FilaConcepto:
    """
    Encapsula los controles de una línea de concepto en el formulario.
    El precio unitario es final (IVA incluido).
    """

    def __init__(self, on_change: Callable[[], None]):
        self.concepto = ft.TextField(
            label="Concepto / Servicio",
            width=300,
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
            label="P. Unit. (EUR, IVA incluido)",
            value="",
            hint_text="€",
            width=130,
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=lambda _: self._recalcular(on_change),
        )
        self.total = ft.TextField(
            label="Total",
            value="0.00",
            width=120,
            read_only=True,
            bgcolor=ft.Colors.GREY_200,
        )

    def _precio_valido(self, texto: str) -> bool:
        patron = r"^(0|[1-9]\d*)([\.,]\d{1,2})?$"
        return bool(re.fullmatch(patron, texto))

    def _recalcular(self, on_change: Callable[[], None]):
        try:
            precio_txt = self.precio.value.strip()
            if not self._precio_valido(precio_txt):
                raise ValueError("Formato de precio invalido")
            cantidad = int(self.cantidad.value)
            precio = float(precio_txt.replace(",", "."))
            self.total.value = f"{round(cantidad * precio, 2):.2f}"
        except ValueError:
            self.total.value = "0.00"
        on_change()

    def como_row(self) -> ft.Row:
        return ft.Row(
            controls=[self.concepto, self.cantidad, self.precio, self.total],
            alignment=ft.MainAxisAlignment.START,
        )

    def a_linea_factura(self) -> LineaFactura:
        concepto = self.concepto.value.strip()
        if not concepto:
            raise ValueError("El concepto no puede estar vacío.")
        cantidad = int(self.cantidad.value)
        precio_txt = self.precio.value.strip()
        if not self._precio_valido(precio_txt):
            raise ValueError(
                "Precio inválido: usa formato EUR sin ceros a la izquierda (ej: 1100 o 1100.50)."
            )
        precio = float(precio_txt.replace(",", "."))
        return LineaFactura(concepto=concepto, cantidad=cantidad, precio_unitario=precio)


def main(page: ft.Page):
    page.title = "Facturas — Gisselle Marin Tabares"
    page.window.width = 780
    page.window.height = 800

    # ── Pantalla de login ─────────────────────────────────────────────────────
    def mostrar_login() -> None:
        page.scroll = ft.ScrollMode.HIDDEN
        page.padding = 0
        page.controls.clear()

        txt_usuario = ft.TextField(
            label="Usuario",
            width=300,
            autofocus=True,
            on_submit=lambda _: txt_password.focus(),
        )
        txt_password = ft.TextField(
            label="Contraseña",
            password=True,
            can_reveal_password=True,
            width=300,
        )
        lbl_error = ft.Text(value="", color=ft.Colors.RED_600, size=13)

        def login(_=None) -> None:
            usuario = txt_usuario.value.strip()
            pwd_hash = hashlib.sha256(txt_password.value.encode()).hexdigest()
            if usuario == _USUARIO_VALIDO and pwd_hash == _HASH_PASSWORD:
                logger.info("Inicio de sesión correcto.")
                mostrar_app()
            else:
                logger.warning("Intento de acceso fallido.")
                lbl_error.value = "Usuario o contraseña incorrectos."
                txt_password.value = ""
                page.update()

        txt_password.on_submit = login

        page.add(
            ft.Column(
                controls=[
                    ft.Text("", expand=True),
                    ft.Text(
                        "GENERADOR DE FACTURAS",
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE_900,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        "Gisselle Marin Tabares",
                        size=13,
                        color=ft.Colors.GREY_600,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Divider(),
                    ft.Row([txt_usuario], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Row([txt_password], alignment=ft.MainAxisAlignment.CENTER),
                    lbl_error,
                    ft.Row(
                        [ft.Button(
                            "Entrar",
                            on_click=login,
                            bgcolor=ft.Colors.BLUE_800,
                            color=ft.Colors.WHITE,
                            width=300,
                        )],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    ft.Text("", expand=True),
                ],
            )
        )
        page.update()

    # ── Aplicación principal (se muestra tras el login) ───────────────────────
    def mostrar_app() -> None:
        page.scroll = ft.ScrollMode.AUTO
        page.padding = 24
        page.controls.clear()
        page.window.prevent_close = True
        page.window.on_event = None

        # ── Estado ────────────────────────────────────────────────────────────
        filas: list[FilaConcepto] = []
        numero_factura = siguiente_numero_factura()
        total_dia = 0.0
        facturas_dia = 0

        # ── Controles dinámicos ───────────────────────────────────────────────
        contenedor_filas = ft.Column(spacing=6)

        lbl_numero = ft.Text(
            value=f"Factura  {date.today().year}-{numero_factura:03d}",
            size=13,
            color=ft.Colors.GREY_700,
        )

        lbl_iva = ft.Text(value="0.00 €", size=13, color=ft.Colors.GREY_800)
        lbl_total = ft.Text(
            value="0.00 €",
            size=22,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.BLUE_800,
        )
        lbl_facturas_dia = ft.Text(value="0", size=15, weight=ft.FontWeight.BOLD)
        lbl_total_dia = ft.Text(value="0.00 €", size=15, weight=ft.FontWeight.BOLD)
        lbl_estado = ft.Text(value="", size=13)
        txt_ajuste = ft.TextField(
            label="Ajuste manual (- EUR)",
            hint_text="Ej: 12.50 EUR",
            width=170,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        def _importe_eur_valido(texto: str) -> bool:
            patron = r"^(0|[1-9]\d*)([\.,]\d{1,2})?$"
            return bool(re.fullmatch(patron, texto))

        txt_cliente_nombre = ft.TextField(
            label="Nombre / Empresa del cliente (opcional)",
            width=340,
            autofocus=True,
        )
        txt_cliente_nif = ft.TextField(
            label="NIF / CIF del cliente (opcional)",
            width=200,
        )

        selector_guardado = ft.FilePicker()

        def _ruta_guardado_con_extension(path_str: str) -> Path:
            ruta = Path(path_str)
            if ruta.suffix.lower() != ".xlsx":
                ruta = ruta.with_suffix(".xlsx")
            return ruta

        async def _guardar_factura_con_dialogo(factura: Factura) -> None:
            nonlocal total_dia, facturas_dia
            try:
                destino_path = await selector_guardado.save_file(
                    dialog_title="Guardar factura Calc",
                    file_name=f"factura_{factura.fecha.year}_{factura.numero:03d}.xlsx",
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["xlsx"],
                )
            except Exception as ex:
                lbl_estado.value = f"No se pudo abrir el selector de guardado: {ex}"
                lbl_estado.color = ft.Colors.RED_600
                logger.error("Error al abrir diálogo de guardado: %s", ex, exc_info=True)
                page.update()
                return

            if not destino_path:
                lbl_estado.value = "Generación cancelada. No se seleccionó carpeta de guardado."
                lbl_estado.color = ft.Colors.ORANGE_700
                page.update()
                return

            destino = _ruta_guardado_con_extension(destino_path)
            try:
                ruta_generada = generar_factura_xlsx(factura)
                destino.parent.mkdir(parents=True, exist_ok=True)
                if ruta_generada.resolve() != destino.resolve():
                    shutil.copy2(ruta_generada, destino)
                else:
                    logger.info(
                        "La factura %s ya estaba en la ruta seleccionada: %s",
                        factura.numero_formateado,
                        destino,
                    )
            except Exception as ex:
                lbl_estado.value = f"Error al generar/guardar el archivo: {ex}"
                lbl_estado.color = ft.Colors.RED_600
                logger.error(
                    "Error al generar factura %s en destino %s: %s",
                    factura.numero_formateado,
                    destino,
                    ex,
                    exc_info=True,
                )
                page.update()
                return

            logger.info("Factura %s guardada en %s", factura.numero_formateado, destino)
            facturas_dia += 1
            total_dia = round(total_dia + factura.total_con_iva, 2)
            lbl_facturas_dia.value = str(facturas_dia)
            lbl_total_dia.value = f"{total_dia:.2f} €"
            lbl_estado.value = f"✓  Factura {factura.numero_formateado} guardada en: {destino}"
            lbl_estado.color = ft.Colors.GREEN_700
            page.update()

            def _cerrar_dialogo_si_abierto() -> None:
                try:
                    page.pop_dialog()
                except Exception:
                    pass

            def _no_imprimir(_=None) -> None:
                _cerrar_dialogo_si_abierto()
                resetear()

            def _imprimir(_=None) -> None:
                _cerrar_dialogo_si_abierto()
                try:
                    ticket = _generar_ticket_escpos(factura, ancho=42)
                    impresora = _imprimir_ticket_usb_windows(ticket)
                    logger.info(
                        "Ticket impreso para factura %s en impresora %s",
                        factura.numero_formateado,
                        impresora,
                    )
                except Exception as ex:
                    lbl_estado.value = (
                        "Factura guardada, pero no se pudo imprimir ticket: "
                        f"{ex}"
                    )
                    lbl_estado.color = ft.Colors.ORANGE_700
                    logger.warning(
                        "Fallo de impresion ticket para factura %s: %s",
                        factura.numero_formateado,
                        ex,
                        exc_info=True,
                    )
                    page.update()
                resetear()

            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("Imprimir ticket"),
                content=ft.Text(
                    "La factura Calc se guardo correctamente. ¿Deseas imprimir ticket ahora?"
                ),
                actions=[
                    ft.TextButton("No", on_click=_no_imprimir),
                    ft.FilledButton("Si, imprimir", on_click=_imprimir),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.show_dialog(dlg)

        page.overlay.append(selector_guardado)

        async def _confirmar_cierre(evento: ft.WindowEvent) -> None:
            if evento.type != ft.WindowEventType.CLOSE:
                return

            def _salir(_=None) -> None:
                page.pop_dialog()
                page.run_task(page.window.destroy)

            def _cancelar(_=None) -> None:
                page.pop_dialog()

            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("Confirmar cierre"),
                content=ft.Text(
                    "Si cierras ahora, se reiniciará la sumatoria diaria de esta sesión."
                ),
                actions=[
                    ft.TextButton("Cancelar", on_click=_cancelar),
                    ft.FilledButton("Salir", on_click=_salir),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.show_dialog(dlg)

        page.window.on_event = _confirmar_cierre

        # ── Callbacks ─────────────────────────────────────────────────────────
        def actualizar_totales():
            try:
                total = round(sum(float(f.total.value) for f in filas), 2)
                lbl_iva.value = "Incluido"
                lbl_total.value = f"{total:.2f} €"
            except ValueError:
                lbl_iva.value = "Incluido"
                lbl_total.value = "0.00 €"
            page.update()

        def agregar_fila(_=None):
            fila = FilaConcepto(on_change=actualizar_totales)
            filas.append(fila)
            contenedor_filas.controls.append(fila.como_row())
            logger.info(f"Línea añadida. Total: {len(filas)}")
            page.update()

        def quitar_fila(_=None):
            if len(filas) <= 1:
                lbl_estado.value = "La factura debe tener al menos una línea."
                lbl_estado.color = ft.Colors.ORANGE_700
                page.update()
                return
            filas.pop()
            contenedor_filas.controls.pop()
            actualizar_totales()
            logger.info(f"Línea eliminada. Total: {len(filas)}")

        def resetear():
            nonlocal numero_factura
            filas.clear()
            contenedor_filas.controls.clear()
            txt_cliente_nombre.value = ""
            txt_cliente_nif.value = ""
            numero_factura = siguiente_numero_factura()
            lbl_numero.value = f"Factura  {date.today().year}-{numero_factura:03d}"
            lbl_estado.value = ""
            agregar_fila()
            actualizar_totales()
            logger.info(f"Formulario reseteado. Siguiente factura: {numero_factura:03d}")

        def abrir_carpeta_facturas(_=None):
            try:
                RUTA_FACTURAS.mkdir(parents=True, exist_ok=True)
                ruta_str = str(RUTA_FACTURAS)
                if sys.platform.startswith("win"):
                    os.startfile(ruta_str)  # type: ignore[attr-defined]
                elif sys.platform == "darwin":
                    subprocess.run(["open", ruta_str], check=True)
                else:
                    subprocess.run(["xdg-open", ruta_str], check=True)
            except Exception as e:
                lbl_estado.value = f"No se pudo abrir la carpeta: {e}"
                lbl_estado.color = ft.Colors.RED_600
                logger.error("Error al abrir carpeta de facturas: %s", e, exc_info=True)
                page.update()

        def generar(_=None):
            # Validar y construir líneas
            try:
                lineas = [f.a_linea_factura() for f in filas]
            except ValueError as e:
                lbl_estado.value = str(e)
                lbl_estado.color = ft.Colors.RED_600
                page.update()
                return

            factura = Factura(
                numero=numero_factura,
                fecha=date.today(),
                cliente_nombre=txt_cliente_nombre.value.strip(),
                cliente_nif=txt_cliente_nif.value.strip(),
                lineas=lineas,
            )
            cliente_log = factura.cliente_nombre or "(sin cliente)"
            logger.info(
                f"Factura {factura.numero_formateado} · "
                f"Cliente: {cliente_log} · "
                f"Total: {factura.total_con_iva:.2f} €"
            )
            lbl_estado.value = "Selecciona dónde guardar el archivo Calc (.xlsx)..."
            lbl_estado.color = ft.Colors.BLUE_700
            page.update()
            page.run_task(_guardar_factura_con_dialogo, factura)

        def restar_acumulado(_=None):
            nonlocal total_dia

            valor_txt = txt_ajuste.value.strip().replace(",", ".")
            if not _importe_eur_valido(valor_txt):
                lbl_estado.value = (
                    "Importe invalido: usa formato EUR sin ceros a la izquierda (ej: 1100 o 1100.50)."
                )
                lbl_estado.color = ft.Colors.RED_600
                page.update()
                return

            try:
                ajuste = float(valor_txt)
            except ValueError:
                lbl_estado.value = "Introduce un importe válido para restar del acumulado."
                lbl_estado.color = ft.Colors.RED_600
                page.update()
                return

            if ajuste <= 0:
                lbl_estado.value = "El ajuste debe ser mayor que 0."
                lbl_estado.color = ft.Colors.RED_600
                page.update()
                return

            if ajuste > total_dia:
                lbl_estado.value = "El ajuste no puede superar el acumulado del día."
                lbl_estado.color = ft.Colors.RED_600
                page.update()
                return

            total_dia = round(total_dia - ajuste, 2)
            lbl_total_dia.value = f"{total_dia:.2f} €"
            txt_ajuste.value = ""
            lbl_estado.value = f"Ajuste aplicado: -{ajuste:.2f} € al acumulado diario."
            lbl_estado.color = ft.Colors.BLUE_700
            page.update()

        txt_ajuste.on_submit = restar_acumulado

        # ── Construcción de la UI ─────────────────────────────────────────────

        cabecera = ft.Column(
            controls=[
                ft.Text(
                    "GENERADOR DE FACTURAS",
                    size=26,
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER,
                    color=ft.Colors.BLUE_900,
                ),
                ft.Text(
                    "Gisselle Marin Tabares",
                    size=14,
                    text_align=ft.TextAlign.CENTER,
                    color=ft.Colors.GREY_600,
                ),
                lbl_numero,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=2,
        )

        bloque_cliente = ft.Column(
            controls=[
                ft.Text("DATOS DEL CLIENTE (OPCIONAL)", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_600),
                ft.Row(
                    controls=[txt_cliente_nombre, txt_cliente_nif],
                    alignment=ft.MainAxisAlignment.START,
                    spacing=12,
                ),
            ],
            spacing=6,
        )

        botones_filas = ft.Row(
            controls=[
                ft.Button("+ Añadir línea", on_click=agregar_fila),
                ft.Button("- Quitar línea", on_click=quitar_fila),
            ],
            alignment=ft.MainAxisAlignment.START,
        )

        bloque_totales = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("IVA:", size=13, color=ft.Colors.GREY_700),
                        lbl_iva,
                    ],
                    alignment=ft.MainAxisAlignment.END,
                    spacing=8,
                ),
                ft.Row(
                    controls=[
                        ft.Text("TOTAL:", size=18, weight=ft.FontWeight.BOLD),
                        lbl_total,
                    ],
                    alignment=ft.MainAxisAlignment.END,
                    spacing=8,
                ),
                ft.Row(
                    controls=[
                        ft.Text(
                            "FACTURAS DEL DÍA:",
                            size=13,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.GREY_700,
                        ),
                        lbl_facturas_dia,
                    ],
                    alignment=ft.MainAxisAlignment.END,
                    spacing=8,
                ),
                ft.Row(
                    controls=[
                        ft.Text(
                            "ACUMULADO DEL DÍA:",
                            size=13,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.GREY_700,
                        ),
                        lbl_total_dia,
                    ],
                    alignment=ft.MainAxisAlignment.END,
                    spacing=8,
                ),
                ft.Row(
                    controls=[
                        txt_ajuste,
                        ft.OutlinedButton(
                            "Restar",
                            icon=ft.Icons.REMOVE,
                            on_click=restar_acumulado,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.END,
                    spacing=8,
                ),
            ],
            spacing=4,
        )

        boton_generar = ft.Button(
            "GENERAR FACTURA",
            icon=ft.Icons.SAVE_ALT,
            bgcolor=ft.Colors.BLUE_800,
            color=ft.Colors.WHITE,
            height=52,
            width=280,
            on_click=generar,
        )
        boton_abrir_carpeta = ft.OutlinedButton(
            "ABRIR CARPETA DE FACTURAS",
            icon=ft.Icons.FOLDER_OPEN,
            height=52,
            width=280,
            on_click=abrir_carpeta_facturas,
        )

        page.add(
            cabecera,
            ft.Divider(),
            bloque_cliente,
            ft.Divider(),
            ft.Text("LÍNEAS DE LA FACTURA", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_600),
            contenedor_filas,
            botones_filas,
            ft.Divider(),
            bloque_totales,
            ft.Divider(),
            ft.Row([boton_generar, boton_abrir_carpeta], alignment=ft.MainAxisAlignment.CENTER, spacing=12),
            lbl_estado,
        )
        page.update()
        agregar_fila()

    # ── Arranque ──────────────────────────────────────────────────────────────
    mostrar_login()


ft.run(main)
