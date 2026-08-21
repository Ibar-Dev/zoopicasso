# main.py — App de escritorio de Zoo Picasso
# Tickets (TPV), facturas en Excel, control de ventas y envio de facturas por email.
# Ejecutar: uv run main.py  (desde esta carpeta)

import hashlib

import flet as ft

from app_escritorio.bootstrap import ensure_project_paths

ensure_project_paths()

import src.settings  # noqa: E402  # logging centralizado y rutas

from ui.email_view import EmailView  # noqa: E402
from ui.facturas_view import FacturasView  # noqa: E402
from ui.tickets_view import TicketsView  # noqa: E402
from ui.ventas_view import VentasView  # noqa: E402

# Credenciales de acceso (las mismas que la app de facturas)
_USUARIO_VALIDO = "Giselle"
_HASH_PASSWORD = "2aa2d838b21d5fe3fe9819640d83e40aea9f899d93b25a0ef9858ba9f83effda"

_TABS = [
    ("Tickets", ft.Icons.RECEIPT_LONG),
    ("Facturas", ft.Icons.DESCRIPTION),
    ("Ventas", ft.Icons.BAR_CHART),
    ("Configuración", ft.Icons.SETTINGS),
]


def main(page: ft.Page):
    page.title = "Zoo Picasso - App de escritorio"
    page.window.width = 1180
    page.window.height = 800
    page.padding = 0
    page.scroll = ft.ScrollMode.HIDDEN

    # ── Pantalla de login ────────────────────────────────────────────────────
    def mostrar_login() -> None:
        page.controls.clear()
        page.padding = 0

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
                mostrar_app(usuario)
            else:
                lbl_error.value = "Usuario o contraseña incorrectos."
                txt_password.value = ""
                page.update()

        txt_password.on_submit = login

        page.add(
            ft.Column(
                controls=[
                    ft.Text("", expand=True),
                    ft.Text(
                        "ZOO PICASSO",
                        size=28,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.GREEN_800,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Text(
                        "Tickets · Facturas · Control de ventas",
                        size=14,
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
                            bgcolor=ft.Colors.GREEN_800,
                            color=ft.Colors.WHITE,
                            width=300,
                        )],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    ft.Text("", expand=True),
                ],
                expand=True,
            )
        )
        page.update()

    # ── Aplicacion principal ─────────────────────────────────────────────────
    def mostrar_app(usuario: str) -> None:
        page.controls.clear()
        page.padding = 16
        page.scroll = ft.ScrollMode.AUTO

        # Las vistas se crean una sola vez y conservan su estado al cambiar de pestana.
        vista_tickets = TicketsView(page, usuario)
        vista_facturas = FacturasView(page, usuario)
        vista_ventas = VentasView(page)
        vista_email = EmailView(page)

        contenedor = ft.Column(expand=True)

        def _mostrar(indice: int) -> None:
            if indice == 0:
                contenedor.controls = [vista_tickets.construir()]
            elif indice == 1:
                contenedor.controls = [vista_facturas.construir()]
            elif indice == 2:
                contenedor.controls = [vista_ventas.construir()]
                vista_ventas.actualizar_resumen()
                vista_ventas.buscar()
            else:
                contenedor.controls = [vista_email.construir()]
            page.update()

        def cambiar_pestana(e: ft.ControlEvent) -> None:
            _mostrar(e.control.selected_index)

        rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=160,
            destinations=[
                ft.NavigationRailDestination(
                    icon=icon,
                    selected_icon=icon,
                    label=nombre,
                )
                for nombre, icon in _TABS
            ],
            on_change=cambiar_pestana,
            expand=False,
        )

        page.add(ft.Row(controls=[rail, ft.VerticalDivider(width=1), contenedor], expand=True))
        _mostrar(0)
        page.update()

    mostrar_login()


if __name__ == "__main__":
    ft.run(main)