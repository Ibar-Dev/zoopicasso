import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

from escritorio.config_app import ConfigSMTP

logger = logging.getLogger(__name__)

_MIME_XLSX = "vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _texto_plantilla(plantilla: str, **kwargs) -> str:
    try:
        return plantilla.format(**kwargs)
    except (KeyError, IndexError, ValueError):
        return plantilla


def _abrir_servidor(cfg: ConfigSMTP) -> smtplib.SMTP:
    if cfg.usar_tls:
        servidor = smtplib.SMTP(cfg.servidor, cfg.puerto, timeout=30)
        servidor.ehlo()
        servidor.starttls()
        servidor.ehlo()
    else:
        servidor = smtplib.SMTP_SSL(cfg.servidor, cfg.puerto, timeout=30)
    return servidor


def _remitente(cfg: ConfigSMTP) -> str:
    return formataddr((cfg.firma or "Zoo Picasso", cfg.remitente or cfg.usuario))


def enviar_factura_por_email(
    cfg: ConfigSMTP,
    destinatario: str,
    ruta_adjunto: Path | str,
    numero_factura: str,
    cliente: str = "",
) -> None:
    if not destinatario.strip():
        raise ValueError("Indica el email del cliente para enviar la factura.")
    ruta = Path(ruta_adjunto)
    if not ruta.exists():
        raise FileNotFoundError(f"No existe el archivo adjunto: {ruta}")

    msg = EmailMessage()
    msg["Subject"] = _texto_plantilla(cfg.asunto, numero=numero_factura, cliente=cliente)
    msg["From"] = _remitente(cfg)
    msg["To"] = destinatario.strip()
    if cfg.copia_para_mi:
        msg["Bcc"] = cfg.remitente or cfg.usuario
    msg.set_content(
        _texto_plantilla(cfg.cuerpo, numero=numero_factura, cliente=cliente, firma=cfg.firma)
    )
    with ruta.open("rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype=_MIME_XLSX,
            filename=ruta.name,
        )

    servidor = _abrir_servidor(cfg)
    with servidor:
        servidor.login(cfg.usuario, cfg.contrasena)
        servidor.send_message(msg)
    logger.info("Factura %s enviada a %s", numero_factura, destinatario)


def enviar_email_prueba(cfg: ConfigSMTP, destinatario: str) -> None:
    if not destinatario.strip():
        raise ValueError("Indica el email de destino de la prueba.")
    msg = EmailMessage()
    msg["Subject"] = "Prueba de configuracion - Zoo Picasso"
    msg["From"] = _remitente(cfg)
    msg["To"] = destinatario.strip()
    msg.set_content(
        "Este es un email de prueba de la app de escritorio de Zoo Picasso.\n"
        "Si lo estas viendo, la configuracion SMTP funciona correctamente."
    )
    servidor = _abrir_servidor(cfg)
    with servidor:
        servidor.login(cfg.usuario, cfg.contrasena)
        servidor.send_message(msg)
    logger.info("Email de prueba enviado a %s", destinatario)