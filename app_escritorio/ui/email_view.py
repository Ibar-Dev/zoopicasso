import logging

import flet as ft

from escritorio.config_app import cargar_config_smtp, config_smtp_completa, guardar_config_smtp
from escritorio.email_envio import enviar_email_prueba

logger = logging.getLogger(__name__)


class EmailView:
    """Pestana de configuracion SMTP para enviar facturas por email."""

    def __init__(self, page: ft.Page):
        self.page = page
        cfg = cargar_config_smtp()

        self.txt_servidor = ft.TextField(label="Servidor SMTP", value=cfg.servidor, width=260)
        self.txt_puerto = ft.TextField(label="Puerto", value=str(cfg.puerto), width=90, keyboard_type=ft.KeyboardType.NUMBER)
        self.sw_tls = ft.Switch(label="Usar TLS (STARTTLS)", value=cfg.usar_tls)
        self.txt_usuario = ft.TextField(label="Usuario (email de la cuenta)", value=cfg.usuario, width=260)
        self.txt_contrasena = ft.TextField(
            label="Contraseña / App Password",
            value=cfg.contrasena,
            password=True,
            can_reveal_password=True,
            width=260,
        )
        self.txt_remitente = ft.TextField(label="Remitente (email que aparecerá en el envío)", value=cfg.remitente, width=260)
        self.txt_asunto = ft.TextField(label="Asunto (usa {numero})", value=cfg.asunto, width=420)
        self.txt_cuerpo = ft.TextField(
            label="Cuerpo del mensaje (usa {numero}, {cliente}, {firma})",
            value=cfg.cuerpo,
            multiline=True,
            min_lines=4,
            max_lines=6,
            width=420,
        )
        self.txt_firma = ft.TextField(label="Firma", value=cfg.firma, width=260)
        self.sw_copia = ft.Switch(label="Enviarme una copia (BCC)", value=cfg.copia_para_mi)
        self.txt_prueba = ft.TextField(label="Email de prueba", width=260)
        self.lbl_estado = ft.Text(value="", size=13)

        self.host_puerto = ft.Row(controls=[self.txt_servidor, self.txt_puerto, self.sw_tls], alignment=ft.MainAxisAlignment.START, spacing=8)
        self.cuenta = ft.Row(controls=[self.txt_usuario, self.txt_contrasena], alignment=ft.MainAxisAlignment.START, spacing=8)
        self.mensaje = ft.Column(controls=[self.txt_asunto, self.txt_cuerpo], spacing=8)

    def _leer_config(self):
        cfg = cargar_config_smtp()
        cfg.servidor = self.txt_servidor.value.strip()
        try:
            cfg.puerto = int(self.txt_puerto.value.strip())
        except ValueError:
            raise ValueError("El puerto debe ser un número.")
        cfg.usar_tls = bool(self.sw_tls.value)
        cfg.usuario = self.txt_usuario.value.strip()
        cfg.contrasena = self.txt_contrasena.value
        cfg.remitente = self.txt_remitente.value.strip()
        cfg.asunto = self.txt_asunto.value.strip()
        cfg.cuerpo = self.txt_cuerpo.value
        cfg.firma = self.txt_firma.value.strip()
        cfg.copia_para_mi = bool(self.sw_copia.value)
        return cfg

    def construir(self) -> ft.Control:
        self.refrescar_estado()
        guardar = ft.Button("Guardar configuración", icon=ft.Icons.SAVE, on_click=self.guardar)
        probar = ft.OutlinedButton("Enviar email de prueba", icon=ft.Icons.SEND, on_click=self.probar)
        return ft.Column(
            controls=[
                ft.Text("CONFIGURACIÓN DE EMAIL", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
                ft.Text(
                    "Configura aquí tu cuenta de correo (ej: Gmail con App Password) para poder "
                    "enviar las facturas .xlsx a los clientes que las pidan.",
                    size=13,
                    color=ft.Colors.GREY_600,
                ),
                ft.Divider(),
                self.host_puerto,
                self.cuenta,
                self.txt_remitente,
                ft.Divider(),
                self.mensaje,
                self.txt_firma,
                self.sw_copia,
                ft.Divider(),
                ft.Row(controls=[guardar, probar, self.txt_prueba], alignment=ft.MainAxisAlignment.START, spacing=8),
                self.lbl_estado,
            ],
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    def refrescar_estado(self):
        cfg = cargar_config_smtp()
        ok, motivo = config_smtp_completa(cfg)
        estado = "✓ Configurado correctamente." if ok else f"Pendiente de configurar: {motivo}"
        color = ft.Colors.GREEN_700 if ok else ft.Colors.ORANGE_700
        self.lbl_estado.value = estado
        self.lbl_estado.color = color

    def guardar(self, _=None):
        try:
            cfg = self._leer_config()
        except ValueError as e:
            self._estado(str(e), ft.Colors.RED_600)
            return
        ok, motivo = config_smtp_completa(cfg)
        if not ok:
            self._estado(motivo, ft.Colors.ORANGE_700)
            return
        guardar_config_smtp(cfg)
        self._estado("✓ Configuración guardada.", ft.Colors.GREEN_700)
        logger.info("Configuracion SMTP guardada (servidor=%s)", cfg.servidor)

    def probar(self, _=None):
        try:
            cfg = self._leer_config()
        except ValueError as e:
            self._estado(str(e), ft.Colors.RED_600)
            return
        destino = self.txt_prueba.value.strip()
        if not destino:
            self._estado("Indica el email de destino de la prueba.", ft.Colors.ORANGE_700)
            return
        ok, motivo = config_smtp_completa(cfg)
        if not ok:
            self._estado(motivo, ft.Colors.ORANGE_700)
            return
        guardar_config_smtp(cfg)
        try:
            enviar_email_prueba(cfg, destino)
            self._estado(f"✓ Email de prueba enviado a {destino}.", ft.Colors.GREEN_700)
        except Exception as e:
            self._estado(f"No se pudo enviar la prueba: {e}", ft.Colors.RED_600)
            logger.error("Error en email de prueba: %s", e, exc_info=True)

    def _estado(self, mensaje: str, color: str):
        self.lbl_estado.value = mensaje
        self.lbl_estado.color = color
        self.page.update()