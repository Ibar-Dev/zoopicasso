import logging
import os
import sys
from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware

# Carga configuración de logging y rutas de facturas.
import src.settings  # noqa: F401
from src.factura_counter import siguiente_numero_factura
from src.factura_model import Factura, LineaFactura
from src.factura_writer import RUTA_FACTURAS, generar_factura_xlsx

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

USUARIO_VALIDO = "Giselle"
HASH_PASSWORD = "2aa2d838b21d5fe3fe9819640d83e40aea9f899d93b25a0ef9858ba9f83effda"


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
        win32print.StartDocPrinter(hprinter, 1, ("Ticket factura", "", "RAW"))
        try:
            win32print.StartPagePrinter(hprinter)
            win32print.WritePrinter(hprinter, ticket)
            win32print.EndPagePrinter(hprinter)
        finally:
            win32print.EndDocPrinter(hprinter)
    finally:
        win32print.ClosePrinter(hprinter)

    return impresora


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class LoginPayload(BaseModel):
    usuario: str
    password_hash: str = Field(min_length=64, max_length=64)


class LineaPayload(BaseModel):
    concepto: str = Field(min_length=1)
    cantidad: int = Field(gt=0)
    precio_unitario: float = Field(ge=0)


class FacturaPayload(BaseModel):
    cliente_nombre: Optional[str] = ""
    cliente_nif: Optional[str] = ""
    lineas: list[LineaPayload] = Field(min_length=1)
    imprimir_ticket: bool = False


app = FastAPI(title="Facturas Gisselle API", version="1.0.0")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("WEB_SESSION_SECRET", "cambia-esta-clave-en-produccion"),
    max_age=60 * 60 * 10,
    same_site=os.getenv("WEB_SESSION_SAME_SITE", "lax"),
    https_only=_bool_env("WEB_SESSION_HTTPS_ONLY", False),
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _requiere_login(request: Request) -> None:
    if not request.session.get("logged_in"):
        logger.warning("Acceso no autenticado a endpoint protegido.")
        raise HTTPException(status_code=401, detail="No autenticado")


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/login")
def login(payload: LoginPayload, request: Request) -> JSONResponse:
    usuario = payload.usuario.strip()
    if usuario == USUARIO_VALIDO and payload.password_hash == HASH_PASSWORD:
        request.session["logged_in"] = True
        request.session["usuario"] = usuario
        logger.info("Inicio de sesión correcto (web).")
        return JSONResponse({"ok": True})

    logger.warning("Intento de acceso web fallido.")
    raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")


@app.post("/api/logout")
def logout(request: Request) -> dict[str, bool]:
    usuario = request.session.get("usuario", "(desconocido)")
    request.session.clear()
    logger.info("Cierre de sesión web: %s", usuario)
    return {"ok": True}


@app.get("/api/session")
def session_status(request: Request) -> dict[str, bool]:
    return {"logged_in": bool(request.session.get("logged_in"))}


@app.post("/api/generar")
def generar(payload: FacturaPayload, request: Request) -> dict[str, str | bool]:
    _requiere_login(request)

    try:
        lineas = [
            LineaFactura(
                concepto=l.concepto.strip(),
                cantidad=l.cantidad,
                precio_unitario=l.precio_unitario,
            )
            for l in payload.lineas
        ]

        factura = Factura(
            numero=siguiente_numero_factura(),
            fecha=date.today(),
            cliente_nombre=(payload.cliente_nombre or "").strip(),
            cliente_nif=(payload.cliente_nif or "").strip(),
            lineas=lineas,
        )
        ruta = generar_factura_xlsx(factura)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        logger.error("Error de sistema al generar factura web: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="No se pudo generar la factura") from exc

    logger.info(
        "Factura web %s generada. Cliente: %s Total: %.2f",
        factura.numero_formateado,
        factura.cliente_nombre or "(sin cliente)",
        factura.total_con_iva,
    )

    ticket_impreso = False
    ticket_estado = "Ticket no solicitado."
    if payload.imprimir_ticket:
        try:
            ticket = _generar_ticket_escpos(factura, ancho=42)
            impresora = _imprimir_ticket_usb_windows(ticket)
            ticket_impreso = True
            ticket_estado = f"Ticket enviado a impresora: {impresora}"
            logger.info(
                "Ticket impreso para factura web %s en impresora %s",
                factura.numero_formateado,
                impresora,
            )
        except Exception as exc:
            ticket_estado = f"No se pudo imprimir ticket: {exc}"
            logger.warning(
                "Fallo de impresion ticket para factura web %s: %s",
                factura.numero_formateado,
                exc,
                exc_info=True,
            )

    return {
        "ok": True,
        "numero": factura.numero_formateado,
        "archivo": ruta.name,
        "total": f"{factura.total_con_iva:.2f}",
        "download_url": f"/api/descargar/{ruta.name}",
        "ticket_impreso": ticket_impreso,
        "ticket_estado": ticket_estado,
    }


@app.get("/api/descargar/{nombre_archivo}")
def descargar(nombre_archivo: str, request: Request) -> FileResponse:
    _requiere_login(request)

    ruta = (RUTA_FACTURAS / nombre_archivo).resolve()
    if not str(ruta).startswith(str(RUTA_FACTURAS.resolve())):
        logger.warning("Intento de descarga con nombre inválido: %s", nombre_archivo)
        raise HTTPException(status_code=400, detail="Nombre de archivo inválido")
    if not ruta.exists():
        logger.warning("Archivo solicitado no encontrado: %s", ruta)
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    logger.info("Descarga de factura: %s", ruta.name)

    return FileResponse(
        path=ruta,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=ruta.name,
    )
