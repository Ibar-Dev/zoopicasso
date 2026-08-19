import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path

RUTA_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
RUTA_SMTP_CONFIG = RUTA_CONFIG_DIR / "smtp_config.json"


@dataclass
class ConfigSMTP:
    servidor: str = "smtp.gmail.com"
    puerto: int = 587
    usar_tls: bool = True
    usuario: str = ""
    contrasena: str = ""
    remitente: str = ""
    asunto: str = "Tu factura {numero} de Zoo Picasso"
    cuerpo: str = (
        "Hola {cliente},\n\n"
        "Te adjuntamos la factura {numero} de Zoo Picasso.\n"
        "Gracias por tu confianza.\n\n{firma}"
    )
    firma: str = "Gisselle Marin Tabares"
    copia_para_mi: bool = False


def cargar_config_smtp() -> ConfigSMTP:
    if not RUTA_SMTP_CONFIG.exists():
        return ConfigSMTP()
    try:
        datos = json.loads(RUTA_SMTP_CONFIG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ConfigSMTP()
    valores = {}
    for campo in fields(ConfigSMTP):
        nombre = campo.name
        if nombre in datos:
            valor = datos[nombre]
            if campo.type == "int":
                try:
                    valor = int(valor)
                except (TypeError, ValueError):
                    valor = campo.default
            elif campo.type == "bool":
                valor = bool(valor)
            valores[nombre] = valor
    return ConfigSMTP(**valores)


def guardar_config_smtp(cfg: ConfigSMTP) -> None:
    RUTA_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    RUTA_SMTP_CONFIG.write_text(
        json.dumps(asdict(cfg), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def config_smtp_completa(cfg: ConfigSMTP) -> tuple[bool, str]:
    if not cfg.servidor:
        return False, "Falta el servidor SMTP."
    if not cfg.usuario:
        return False, "Falta el usuario de la cuenta de correo."
    if not cfg.contrasena:
        return False, "Falta la contraseña de la cuenta de correo."
    return True, ""