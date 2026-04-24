import base64
import json
import logging
import os
from datetime import date
from pathlib import Path
from typing import Optional, Literal

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware

# Carga configuración de logging y rutas de facturas.
import src.settings  # noqa: F401
from src.factura_counter import siguiente_numero_factura
from src.factura_model import Factura, LineaFactura
from src.monthly_closure import process_monthly_closure
from src.printer import generar_ticket_escpos
from src.ventas_store import inicializar_db_ventas, registrar_ventas_factura, resumen_ventas_activas
from src.factura_writer import RUTA_FACTURAS, generar_factura_xlsx

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
PRECIOS_CATEGORIAS_PATH = BASE_DIR / "../data/precios_categorias.json"

USUARIO_VALIDO = "Giselle"
HASH_PASSWORD = "2aa2d838b21d5fe3fe9819640d83e40aea9f899d93b25a0ef9858ba9f83effda"

# Garantizar que el directorio data existe
PRECIOS_CATEGORIAS_PATH.parent.mkdir(parents=True, exist_ok=True)

def cargar_precios_categorias() -> dict:
    if not PRECIOS_CATEGORIAS_PATH.exists():
        return {}
    try:
        with open(PRECIOS_CATEGORIAS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error("No se pudo leer precios_categorias.json: %s", e)
        return {}

def guardar_precios_categorias(data: dict) -> None:
    with open(PRECIOS_CATEGORIAS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

class PreciosCategoriasPayload(BaseModel):
    precios: dict[str, float]

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
    categoria: str = ""


# Extensión: método de pago y montos
class FacturaPayload(BaseModel):
    cliente_nombre: Optional[str] = ""
    cliente_nif: Optional[str] = ""
    lineas: list[LineaPayload] = Field(min_length=1)
    imprimir_ticket: bool = False
    metodo_pago: Optional[Literal["efectivo", "tarjeta", "mixto"]] = None
    monto_efectivo: Optional[float] = None
    monto_tarjeta: Optional[float] = None


class MonthlyClosurePayload(BaseModel):
    confirmacion: bool = False

app = FastAPI(title="Facturas Gisselle API", version="1.0.0")

cola_impresion: list[bytes] = []

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("WEB_SESSION_SECRET", "cambia-esta-clave-en-produccion"),
    max_age=60 * 60 * 10,
    same_site=os.getenv("WEB_SESSION_SAME_SITE", "lax"),  # type: ignore
    https_only=_bool_env("WEB_SESSION_HTTPS_ONLY", False),
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
inicializar_db_ventas()


def _anio_mes_actual() -> str:
    return date.today().strftime("%Y-%m")


def _registrar_ventas_factura_background(factura: Factura, usuario: str) -> None:
    try:
        registrar_ventas_factura(factura, usuario)
    except Exception as exc:
        logger.error(
            "Error registrando ventas en buffer mensual para factura %s: %s",
            factura.numero_formateado,
            exc,
            exc_info=True,
        )

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

@app.get("/api/precios_categorias")
def get_precios_categorias(request: Request) -> dict:
    _requiere_login(request)
    return {"precios": cargar_precios_categorias()}

@app.post("/api/precios_categorias")
def set_precios_categorias(payload: PreciosCategoriasPayload, request: Request) -> dict:
    _requiere_login(request)
    usuario = request.session.get("usuario", "(desconocido)")
    precios_anteriores = cargar_precios_categorias()
    nuevos_precios = payload.precios
    guardar_precios_categorias(nuevos_precios)
    for cat, nuevo in nuevos_precios.items():
        anterior = precios_anteriores.get(cat)
        if anterior != nuevo:
            logger.info(
                "Cambio de precio: usuario=%s categoria=%s antes=%s ahora=%.2f",
                usuario, cat, f"{anterior:.2f}" if anterior is not None else "None", nuevo
            )
    return {"ok": True, "precios": nuevos_precios}


@app.get("/api/ganancias/resumen")
def get_ganancias_resumen(request: Request) -> dict:
    _requiere_login(request)
    anio_mes = _anio_mes_actual()
    resumen = resumen_ventas_activas(anio_mes)
    return {
        "ok": True,
        "resumen": resumen,
    }


@app.post("/api/ganancias/cierre-mes")
def cierre_mensual(payload: MonthlyClosurePayload, request: Request) -> dict:
    _requiere_login(request)
    if not payload.confirmacion:
        raise HTTPException(status_code=400, detail="Confirmación requerida para cerrar mes")
    usuario = str(request.session.get("usuario", "(desconocido)"))
    return process_monthly_closure(usuario=usuario)

@app.post("/api/generar")
def generar(payload: FacturaPayload, request: Request, background_tasks: BackgroundTasks) -> dict[str, object]:
    _requiere_login(request)
    # Validación método de pago y montos
    metodo = payload.metodo_pago
    monto_efectivo = payload.monto_efectivo
    monto_tarjeta = payload.monto_tarjeta
    tolerancia = 0.01

    if metodo not in ("efectivo", "tarjeta", "mixto"):
        raise HTTPException(status_code=400, detail="Método de pago inválido o no especificado.")

    try:
        lineas = [
            LineaFactura(
                concepto=l.concepto.strip(),
                cantidad=l.cantidad,
                precio_unitario=l.precio_unitario,
                categoria=l.categoria,
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
        total = factura.total_con_iva
        # Validaciones de montos
        if metodo == "efectivo":
            if monto_efectivo is None or monto_efectivo <= 0 or abs(monto_efectivo - total) > tolerancia:
                raise HTTPException(status_code=400, detail="El monto en efectivo debe ser igual al total.")
            if monto_tarjeta not in (None, 0):
                raise HTTPException(status_code=400, detail="El monto en tarjeta debe ser 0 para pago en efectivo.")
        elif metodo == "tarjeta":
            if monto_tarjeta is None or monto_tarjeta <= 0 or abs(monto_tarjeta - total) > tolerancia:
                raise HTTPException(status_code=400, detail="El monto en tarjeta debe ser igual al total.")
            if monto_efectivo not in (None, 0):
                raise HTTPException(status_code=400, detail="El monto en efectivo debe ser 0 para pago con tarjeta.")
        elif metodo == "mixto":
            if monto_efectivo is None or monto_efectivo < 0 or monto_efectivo > total:
                raise HTTPException(status_code=400, detail="El monto en efectivo debe ser entre 0 y el total.")
            if monto_tarjeta is None:
                raise HTTPException(status_code=400, detail="Falta el monto en tarjeta para pago mixto.")
            if monto_tarjeta < 0 or abs(monto_efectivo + monto_tarjeta - total) > tolerancia:
                raise HTTPException(status_code=400, detail="La suma de efectivo y tarjeta debe ser igual al total.")
        ruta = generar_factura_xlsx(factura)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        logger.error("Error de sistema al generar factura web: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="No se pudo generar la factura") from exc

    logger.info(
        "Factura web %s generada. Cliente: %s Total: %.2f Pago: %s Efectivo: %.2f Tarjeta: %.2f",
        factura.numero_formateado,
        factura.cliente_nombre or "(sin cliente)",
        factura.total_con_iva,
        metodo,
        monto_efectivo or 0,
        monto_tarjeta or 0,
    )
    usuario = str(request.session.get("usuario", "(desconocido)"))
    # Hack: pasar datos de pago a la función de persistencia
    pago_dict = {
        'monto_total': total,
        'monto_efectivo': monto_efectivo or 0,
        'monto_tarjeta': monto_tarjeta or 0,
        'metodo_pago': metodo,
    }
    setattr(factura, '_pago_dict', pago_dict)
    background_tasks.add_task(_registrar_ventas_factura_background, factura, usuario)
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
