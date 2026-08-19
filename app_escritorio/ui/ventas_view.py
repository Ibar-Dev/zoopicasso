import logging
from datetime import date, timedelta

import flet as ft

from escritorio.categorias import CATEGORIAS, METODOS_PAGO
from escritorio.reportes import generar_reporte_historial, generar_reporte_mensual
from src.ventas_store import (
    historial_ventas,
    resumen_ventas_activas,
    resumen_ventas_dia,
)

logger = logging.getLogger(__name__)

_COLUMNAS = [
    ft.DataColumn(label=ft.Text("Nº", weight=ft.FontWeight.BOLD)),
    ft.DataColumn(label=ft.Text("Fecha", weight=ft.FontWeight.BOLD)),
    ft.DataColumn(label=ft.Text("Cliente", weight=ft.FontWeight.BOLD)),
    ft.DataColumn(label=ft.Text("Categorías", weight=ft.FontWeight.BOLD)),
    ft.DataColumn(label=ft.Text("Total (€)", weight=ft.FontWeight.BOLD), numeric=True),
    ft.DataColumn(label=ft.Text("Pago", weight=ft.FontWeight.BOLD)),
    ft.DataColumn(label=ft.Text("Estado", weight=ft.FontWeight.BOLD)),
]


class VentasView:
    """Pestana de control de ventas: resumen, historial y exportacion a Excel."""

    def __init__(self, page: ft.Page):
        self.page = page
        self.ultima_busqueda: list[dict] = []

        hoy = date.today()
        self.txt_desde = ft.TextField(label="Desde (AAAA-MM-DD)", value=(hoy - timedelta(days=30)).isoformat(), width=150)
        self.txt_hasta = ft.TextField(label="Hasta (AAAA-MM-DD)", value=hoy.isoformat(), width=150)
        self.dd_categoria = ft.Dropdown(
            label="Categoría",
            width=160,
            options=[ft.dropdown.Option(key="", text="Todas")] + [ft.dropdown.Option(key=v, text=v) for v in CATEGORIAS],
        )
        self.dd_pago = ft.Dropdown(
            label="Método de pago",
            width=150,
            options=[ft.dropdown.Option(key="", text="Todos")] + [ft.dropdown.Option(key=v, text=v.capitalize()) for v in METODOS_PAGO],
        )

        self.lbl_resumen_hoy = ft.Text(value="—", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800)
        self.lbl_total_mes = ft.Text(value="—", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_800)
        self.lbl_ventas_mes = ft.Text(value="—", size=13)
        self.lbl_efectivo = ft.Text(value="—", size=13)
        self.lbl_tarjeta = ft.Text(value="—", size=13)
        self.tabla = ft.DataTable(columns=_COLUMNAS, rows=[], border=ft.Border.all(1, ft.Colors.GREY_300), border_radius=8)
        self.contenedor_tabla = ft.Column(controls=[self.tabla], scroll=ft.ScrollMode.AUTO)
        self.lbl_estado = ft.Text(value="", size=13)

    def construir(self) -> ft.Control:
        self.actualizar_resumen()
        self.buscar()
        filtros = ft.Row(
            controls=[
                self.txt_desde,
                self.txt_hasta,
                self.dd_categoria,
                self.dd_pago,
                ft.Button("Buscar", icon=ft.Icons.SEARCH, on_click=self.buscar),
            ],
            alignment=ft.MainAxisAlignment.START,
            spacing=8,
        )
        tarjetas = ft.Row(
            controls=[
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text("VENTAS DE HOY", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_600),
                            self.lbl_resumen_hoy,
                        ],
                        spacing=2,
                    ),
                    padding=12,
                    border_radius=8,
                    bgcolor=ft.Colors.BLUE_50,
                ),
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text("TOTAL DEL MES", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_600),
                            self.lbl_total_mes,
                            self.lbl_ventas_mes,
                            ft.Row(
                                controls=[
                                    ft.Text("Efectivo:", size=12),
                                    self.lbl_efectivo,
                                    ft.Text("Tarjeta:", size=12),
                                    self.lbl_tarjeta,
                                ],
                                spacing=6,
                            ),
                        ],
                        spacing=2,
                    ),
                    padding=12,
                    border_radius=8,
                    bgcolor=ft.Colors.GREEN_50,
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
            spacing=12,
        )
        exportar = ft.Row(
            controls=[
                ft.Button("Exportar reporte del mes (Excel)", icon=ft.Icons.DESCRIPTION, on_click=self.exportar_mes),
                ft.OutlinedButton("Exportar historial filtrado (Excel)", icon=ft.Icons.TABLE_VIEW, on_click=self.exportar_historial),
            ],
            alignment=ft.MainAxisAlignment.START,
            spacing=8,
        )
        return ft.Column(
            controls=[
                ft.Text("CONTROL DE VENTAS", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
                ft.Divider(),
                tarjetas,
                ft.Divider(),
                filtros,
                ft.Divider(),
                self.contenedor_tabla,
                ft.Divider(),
                exportar,
                self.lbl_estado,
            ],
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    def _fecha_valida(self, texto: str) -> str:
        try:
            date.fromisoformat(texto.strip())
        except ValueError as e:
            raise ValueError("Las fechas deben tener formato AAAA-MM-DD.") from e
        return texto.strip()

    def actualizar_resumen(self):
        try:
            mes = date.today().strftime("%Y-%m")
            resumen = resumen_ventas_activas(mes)
            hoy = resumen_ventas_dia(date.today().isoformat())
            self.lbl_resumen_hoy.value = f"{hoy['total']:.2f} € ({hoy['cantidad_ventas']} ventas)"
            self.lbl_total_mes.value = f"{resumen['total']:.2f} €"
            self.lbl_ventas_mes.value = f"{resumen['cantidad_ventas']} ventas registradas"
            self.lbl_efectivo.value = f"{resumen['total_efectivo']:.2f} €"
            self.lbl_tarjeta.value = f"{resumen['total_tarjeta']:.2f} €"
        except Exception as e:
            logger.error("Error al calcular resumen: %s", e)
        self.page.update()

    def buscar(self, _=None):
        try:
            desde = self._fecha_valida(self.txt_desde.value)
            hasta = self._fecha_valida(self.txt_hasta.value)
        except ValueError as e:
            self._estado(str(e), ft.Colors.RED_600)
            return
        if desde > hasta:
            self._estado("La fecha 'desde' no puede ser mayor que 'hasta'.", ft.Colors.RED_600)
            return
        try:
            filas = historial_ventas(
                desde,
                hasta,
                self.dd_categoria.value or None,
                self.dd_pago.value or None,
            )
        except Exception as e:
            self._estado(f"Error al consultar el historial: {e}", ft.Colors.RED_600)
            return
        self.ultima_busqueda = filas
        self.tabla.rows = [
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(str(f["numero_factura"]))),
                    ft.DataCell(ft.Text(str(f["fecha_venta"]))),
                    ft.DataCell(ft.Text(str(f["cliente_nombre"] or "—"))),
                    ft.DataCell(ft.Text(str(f["categorias"] or "—"))),
                    ft.DataCell(ft.Text(f"{f['monto_lineas']:.2f}")),
                    ft.DataCell(ft.Text(str(f["metodo_pago"] or "—"))),
                    ft.DataCell(ft.Text(str(f["estado"] or "—"))),
                ]
            )
            for f in filas
        ]
        self._estado(f"{len(filas)} ventas encontradas en el periodo.", ft.Colors.BLUE_700)
        self.page.update()

    def exportar_mes(self, _=None):
        try:
            mes = date.today().strftime("%Y-%m")
            ruta = generar_reporte_mensual(mes)
            self._estado(f"✓ Reporte del mes guardado en: {ruta}", ft.Colors.GREEN_700)
        except Exception as e:
            self._estado(f"Error al generar el reporte: {e}", ft.Colors.RED_600)
            logger.error("Error al exportar reporte mensual: %s", e, exc_info=True)

    def exportar_historial(self, _=None):
        if not self.ultima_busqueda:
            self._estado("Primero haz una búsqueda para exportar su resultado.", ft.Colors.ORANGE_700)
            return
        try:
            ruta = generar_reporte_historial(self.ultima_busqueda)
            self._estado(f"✓ Historial exportado en: {ruta}", ft.Colors.GREEN_700)
        except Exception as e:
            self._estado(f"Error al exportar el historial: {e}", ft.Colors.RED_600)
            logger.error("Error al exportar historial: %s", e, exc_info=True)

    def _estado(self, mensaje: str, color: str):
        self.lbl_estado.value = mensaje
        self.lbl_estado.color = color
        self.page.update()