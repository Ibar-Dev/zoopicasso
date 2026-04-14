import base64
import logging
import os
from datetime import date
from pathlib import Path
from typing import Optional, Literal

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
from src.printer import generar_ticket_escpos
from src.factura_writer import RUTA_FACTURAS, generar_factura_xlsx

# Cola de impresión en memoria (puente nube → PC local)
cola_impresion: list[bytes] = []

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

USUARIO_VALIDO = "Giselle"
HASH_PASSWORD = "2aa2d838b21d5fe3fe9819640d83e40aea9f899d93b25a0ef9858ba9f83effda"


def _env_or_default(name: str, default: str) -> str:
    value = os.getenv(name, "").strip()
    return value or default


EMISOR_FACTURA = {
    "nif": _env_or_default("EMISOR_NIF", "Y3806548Q"),
    "nombre_completo": _env_or_default("EMISOR_NOMBRE", "Gisselle Marin Tabares"),
    "direccion": _env_or_default("EMISOR_DIRECCION", "Calle de Pablo Picasso 59"),
    "telefono": _env_or_default("EMISOR_TELEFONO", "642 342 110"),
    "email": _env_or_default("EMISOR_EMAIL", "zoopicasso07@gmail.com"),
    "negocio": _env_or_default("EMISOR_NEGOCIO", "Zoo Picasso"),
}


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
    same_site=os.getenv("WEB_SESSION_SAME_SITE", "lax"),  # type: ignore
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
def generar(payload: FacturaPayload, request: Request) -> dict[str, object]:
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
            ticket = generar_ticket_escpos(factura, ancho=42)
            cola_impresion.append(ticket)
            ticket_impreso = True
            ticket_estado = "Ticket encolado para impresión."
            logger.info(
                "Ticket encolado para factura web %s (cola: %d pendientes)",
                factura.numero_formateado,
                len(cola_impresion),
            )
        except Exception as exc:
            ticket_estado = f"No se pudo generar ticket: {exc}"
            logger.warning(
                "Fallo al generar ticket para factura web %s: %s",
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
        "emisor": EMISOR_FACTURA,
    }


@app.get("/api/impresion/siguiente")
def siguiente_ticket() -> JSONResponse:
    if not cola_impresion:
        return JSONResponse({"hay_ticket": False}, status_code=204)
    ticket = cola_impresion.pop(0)
    logger.info(
        "Ticket despachado (%d bytes, quedan %d en cola)",
        len(ticket),
        len(cola_impresion),
    )
    return JSONResponse({
        "hay_ticket": True,
        "ticket_b64": base64.b64encode(ticket).decode("ascii"),
    })


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
