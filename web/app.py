import asyncio
import base64
import json
import logging
import os
import shutil
import tempfile
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Literal, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask
from starlette.middleware.sessions import SessionMiddleware

import src.settings  # noqa: F401 — Configura logging y rutas al importarse
import src.factura_writer as factura_writer
from core.domain import TransaccionComercial, VentaItem
from core.sinks import anexar_a_excel, encolar_impresion, generar_xlsx
from src.backup import guardar_estado, hacer_backup, leer_estado
from src.settings import RUTA_EXCEL_AUDITORIA
from src.ventas_store import (
    historial_ventas,
    inicializar_db_ventas,
    listar_ajustes_activos,
    recuperar_pendientes,
    registrar_ajuste,
    registrar_transaccion,
    resumen_ventas_activas,
    resumen_ventas_dia,
)

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

USUARIO_VALIDO = "Giselle"
HASH_PASSWORD = "2aa2d838b21d5fe3fe9819640d83e40aea9f899d93b25a0ef9858ba9f83effda"

_backup_dir_raw = os.getenv("BACKUP_DIR", "").strip()
BACKUP_DIR: Path | None = (
    Path(_backup_dir_raw).expanduser().resolve() if _backup_dir_raw else None
)
BACKUP_INTERVALO_HORAS: int = int(os.getenv("BACKUP_INTERVALO_HORAS", "24"))
BACKUP_RETENER: int = int(os.getenv("BACKUP_RETENER", "7"))

DATA_DIR = (BASE_DIR / ".." / "data").resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Path para precios por categoría (archivo JSON). Usado en tests.
PRECIOS_CATEGORIAS_PATH = DATA_DIR / "precios_categorias.json"


def _env_or_default(name: str, default: str) -> str:
    return os.getenv(name, "").strip() or default


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


# ════════════════════════════════════════════════════════════════════════════
# COLA PERSISTENTE — Tickets ESC/POS en JSON + base64
# ════════════════════════════════════════════════════════════════════════════

class ColaPersistente:
    """Cola que persiste tickets ESC/POS en JSON. Sobrevive reinicios de Render."""

    def __init__(self, ruta: Path | str = "data/cola_impresion.json"):
        self.ruta = Path(ruta) if isinstance(ruta, str) else ruta
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self._datos: list[str] = self._cargar()

    def _cargar(self) -> list[str]:
        if self.ruta.exists():
            try:
                with open(self.ruta, "r", encoding="utf-8") as f:
                    contenido = json.load(f)
                    if isinstance(contenido, dict) and "tickets" in contenido:
                        return contenido["tickets"]
                    if isinstance(contenido, list):
                        return contenido
            except Exception as exc:
                logger.error("Error al cargar cola desde %s: %s", self.ruta, exc)
        return []

    def _guardar(self) -> None:
        try:
            with open(self.ruta, "w", encoding="utf-8") as f:
                json.dump({"tickets": self._datos}, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.error("Error al guardar cola en %s: %s", self.ruta, exc)

    def append(self, item: bytes) -> None:
        self._datos.append(base64.b64encode(item).decode("ascii"))
        self._guardar()

    def pop(self, index: int = 0) -> bytes:
        ticket_b64 = self._datos.pop(index)
        self._guardar()
        return base64.b64decode(ticket_b64)

    def __len__(self) -> int:
        return len(self._datos)

    def __bool__(self) -> bool:
        return bool(self._datos)

    def clear(self) -> None:
        self._datos.clear()
        self._guardar()


COLA_IMPRESION_RUTA = BASE_DIR.parent / "data" / "cola_impresion.json"
cola_impresion = ColaPersistente(COLA_IMPRESION_RUTA)
logger.info(
    "Cola persistente inicializada: %s (%d tickets pendientes)",
    COLA_IMPRESION_RUTA,
    len(cola_impresion),
)


# ════════════════════════════════════════════════════════════════════════════
# MODELOS DE REQUEST
# ════════════════════════════════════════════════════════════════════════════

class LoginPayload(BaseModel):
    usuario: str
    password_hash: str = Field(min_length=64, max_length=64)


class LineaPayload(BaseModel):
    concepto: str = Field(min_length=1)
    cantidad: int = Field(gt=0)
    precio_unitario: float = Field(ge=0)
    categoria: str = ""


class FacturaPayload(BaseModel):
    cliente_nombre: Optional[str] = ""
    cliente_nif: Optional[str] = ""
    lineas: list[LineaPayload] = Field(min_length=1)
    imprimir_ticket: bool = False
    metodo_pago: Optional[Literal["efectivo", "tarjeta", "mixto"]] = None
    monto_efectivo: Optional[float] = None
    monto_tarjeta: Optional[float] = None
    efectivo_entregado: Optional[float] = None


class AjustePayload(BaseModel):
    monto: float = Field(gt=0)


# ════════════════════════════════════════════════════════════════════════════
# LIFESPAN — Backup periódico + Outbox pattern al arrancar
# ════════════════════════════════════════════════════════════════════════════

async def _tarea_backup() -> None:
    while True:
        try:
            await asyncio.to_thread(hacer_backup, BACKUP_DIR, BACKUP_RETENER)
            guardar_estado(DATA_DIR, ok=True)
        except Exception as exc:
            guardar_estado(DATA_DIR, ok=False, mensaje=str(exc))
            logger.error("Backup automático fallido: %s", exc)
        await asyncio.sleep(BACKUP_INTERVALO_HORAS * 3600)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Patrón Outbox: reintentar sinks que no completaron en arranques anteriores
    pendientes = recuperar_pendientes()
    if pendientes:
        logger.warning("Reintentando %d transacciones pendientes...", len(pendientes))
        for row in pendientes:
            t = TransaccionComercial.from_db_row(row)
            if row.get("print_pendiente"):
                try:
                    encolar_impresion(t, cola_impresion)
                except Exception as exc:
                    logger.error("Reintento impresión fallido %s: %s", t.id_transaccion, exc)
            if row.get("excel_pendiente"):
                try:
                    anexar_a_excel(t)
                except Exception as exc:
                    logger.error("Reintento Excel fallido %s: %s", t.id_transaccion, exc)

    task = None
    if BACKUP_DIR:
        task = asyncio.create_task(_tarea_backup())
        logger.info(
            "Backup automático activado → %s (cada %dh)", BACKUP_DIR, BACKUP_INTERVALO_HORAS
        )
    else:
        logger.warning("BACKUP_DIR no configurado — backup automático desactivado")
    yield
    if task:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


app = FastAPI(title="Facturas Zoo Picasso", version="2.0.0", lifespan=lifespan)


# ════════════════════════════════════════════════════════════════════════════
# MIDDLEWARE Y MONTAJE
# ════════════════════════════════════════════════════════════════════════════

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


# ════════════════════════════════════════════════════════════════════════════
# UTILIDADES INTERNAS
# ════════════════════════════════════════════════════════════════════════════

def _anio_mes_actual() -> str:
    return date.today().strftime("%Y-%m")


def _requiere_login(request: Request) -> None:
    if not request.session.get("logged_in"):
        logger.warning("Acceso no autenticado a endpoint protegido.")
        raise HTTPException(status_code=401, detail="No autenticado")


def _ruta_facturas_efectiva() -> Path:
    """Ruta real de facturas en ejecución (puede cambiar dinámicamente)."""
    return Path(factura_writer.RUTA_FACTURAS).resolve()


# ════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — Públicos
# ════════════════════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/keep-alive")
def keep_alive() -> JSONResponse:
    """Previene spin-down de Render (Free tier). Sin autenticación."""
    return JSONResponse({"status": "ok"}, status_code=200)


# ════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — Sesión
# ════════════════════════════════════════════════════════════════════════════

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


@app.post("/api/precios_categorias")
def post_precios_categorias(payload: dict, request: Request) -> JSONResponse:
    """Endpoint de compatibilidad para guardar precios por categoría (deprecated).

    Recibe JSON: {"precios": {"aves": 25.5, ...}}
    Guarda en PRECIOS_CATEGORIAS_PATH.
    """
    _requiere_login(request)
    precios = payload.get("precios") if isinstance(payload, dict) else None
    if not isinstance(precios, dict):
        raise HTTPException(status_code=400, detail="Campo 'precios' requerido")

    try:
        PRECIOS_CATEGORIAS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(PRECIOS_CATEGORIAS_PATH, "w", encoding="utf-8") as f:
            json.dump({"precios": precios}, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.error("No se pudo guardar precios por categoría: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))

    return JSONResponse({"ok": True, "precios": precios})


@app.get("/api/session")
def session_status(request: Request) -> JSONResponse:
    return JSONResponse({"logged_in": bool(request.session.get("logged_in"))})


# ════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — Configuración
# ════════════════════════════════════════════════════════════════════════════

@app.get("/api/config")
def get_config(request: Request) -> dict:
    _requiere_login(request)
    return {
        "emisor": EMISOR_FACTURA,
        "rutas": {
            "excel_auditoria": str(RUTA_EXCEL_AUDITORIA),
            "facturas_principal": str(_ruta_facturas_efectiva()),
            "facturas_settings": str(src.settings.RUTA_FACTURAS_PRINCIPAL),
        },
    }


# ════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — Backup
# ════════════════════════════════════════════════════════════════════════════

@app.get("/api/backup/estado")
def get_backup_estado(request: Request) -> dict:
    _requiere_login(request)
    return {"ok": True, **leer_estado(DATA_DIR)}


@app.post("/api/backup/manual")
async def backup_manual(request: Request) -> FileResponse:
    _requiere_login(request)
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        archivo = await asyncio.to_thread(hacer_backup, tmp_dir, 99)
        guardar_estado(DATA_DIR, ok=True, mensaje="Manual")
    except Exception as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        logger.error("Error al generar backup manual: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al generar backup: {exc}")
    return FileResponse(
        path=archivo,
        media_type="application/zip",
        filename=archivo.name,
        background=BackgroundTask(shutil.rmtree, str(tmp_dir), True),
    )


# ════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — Ganancias
# ════════════════════════════════════════════════════════════════════════════

@app.get("/api/ganancias/resumen")
def get_ganancias_resumen(request: Request) -> dict:
    _requiere_login(request)
    anio_mes = _anio_mes_actual()
    return {
        "ok": True,
        "resumen": resumen_ventas_activas(anio_mes),
        "resumen_hoy": resumen_ventas_dia(date.today().isoformat()),
    }


@app.get("/api/ganancias/historial")
def get_historial(
    request: Request,
    fecha_desde: str,
    fecha_hasta: str,
    categoria: str = "",
    metodo_pago: str = "",
) -> dict:
    _requiere_login(request)
    filas = historial_ventas(
        fecha_desde,
        fecha_hasta,
        categoria or None,
        metodo_pago or None,
    )
    return {"ok": True, "filas": filas}


@app.get("/api/ganancias/ajustes")
def get_ajustes(request: Request) -> dict:
    _requiere_login(request)
    return {"ok": True, "ajustes": listar_ajustes_activos(_anio_mes_actual())}


@app.post("/api/ganancias/ajuste")
def registrar_ajuste_endpoint(payload: AjustePayload, request: Request) -> dict:
    _requiere_login(request)
    usuario = str(request.session.get("usuario", ""))
    anio_mes = _anio_mes_actual()
    resumen = resumen_ventas_activas(anio_mes)
    if payload.monto > resumen["total"]:
        raise HTTPException(status_code=400, detail="El ajuste supera el total acumulado.")
    registrar_ajuste(anio_mes, usuario, payload.monto)
    return {"ok": True, "resumen": resumen_ventas_activas(anio_mes)}


# ════════════════════════════════════════════════════════════════════════════
# ENDPOINT PRINCIPAL — Generar factura
# ════════════════════════════════════════════════════════════════════════════

@app.post("/api/generar")
def generar(
    payload: FacturaPayload,
    request: Request,
    bg_tasks: BackgroundTasks,
) -> dict[str, object]:
    """
    Genera una factura y la enruta a los sinks correspondientes.

    FLUJO:
      1. Valida el payload y los montos de pago.
      2. Construye TransaccionComercial.
      3. registrar_transaccion() → persiste en SQLite de forma atómica,
         asigna id_transaccion (YYYY-NNN).
      4. generar_xlsx() → genera el archivo Excel de factura.
      5. Si imprimir_ticket: encolar_impresion() → bytes ESC/POS en cola.
      6. bg_tasks: anexar_a_excel() → auditoría Excel en background.
    """
    _requiere_login(request)
    usuario = str(request.session.get("usuario", "(desconocido)"))

    metodo = payload.metodo_pago
    monto_efectivo = payload.monto_efectivo or 0.0
    monto_tarjeta = payload.monto_tarjeta or 0.0
    efectivo_entregado = payload.efectivo_entregado or 0.0
    cambio = 0.0
    tolerancia = 0.01

    if metodo not in ("efectivo", "tarjeta", "mixto"):
        raise HTTPException(status_code=400, detail="Método de pago inválido o no especificado.")

    try:
        items = [
            VentaItem(
                descripcion=l.concepto.strip(),
                cantidad=l.cantidad,
                precio_unitario=l.precio_unitario,
                categoria=l.categoria,
            )
            for l in payload.lineas
        ]
        total = round(sum(i.total for i in items), 2)

        # Validaciones de montos según método de pago
        if metodo == "efectivo":
            if monto_efectivo <= 0 or abs(monto_efectivo - total) > tolerancia:
                raise HTTPException(status_code=400, detail="El Monto del Total debe ser igual al total.")
            if payload.monto_tarjeta not in (None, 0):
                raise HTTPException(status_code=400, detail="El monto en tarjeta debe ser 0 para pago en efectivo.")
            if efectivo_entregado < monto_efectivo:
                raise HTTPException(status_code=400, detail="El efectivo entregado debe ser igual o mayor al total.")
            cambio = round(efectivo_entregado - monto_efectivo, 2)
        elif metodo == "tarjeta":
            if monto_tarjeta <= 0 or abs(monto_tarjeta - total) > tolerancia:
                raise HTTPException(status_code=400, detail="El monto en tarjeta debe ser igual al total.")
            if payload.monto_efectivo not in (None, 0):
                raise HTTPException(status_code=400, detail="El Monto del Total debe ser 0 para pago con tarjeta.")
            efectivo_entregado = 0.0
        elif metodo == "mixto":
            if monto_efectivo < 0 or monto_efectivo > total:
                raise HTTPException(status_code=400, detail="El Monto del Total debe ser entre 0 y el total.")
            if payload.monto_tarjeta is None:
                raise HTTPException(status_code=400, detail="Falta el monto en tarjeta para pago mixto.")
            if monto_tarjeta < 0 or abs(monto_efectivo + monto_tarjeta - total) > tolerancia:
                raise HTTPException(status_code=400, detail="La suma de efectivo y tarjeta debe ser igual al total.")
            if efectivo_entregado < monto_efectivo:
                raise HTTPException(
                    status_code=400,
                    detail="El efectivo entregado debe ser igual o mayor al efectivo a pagar.",
                )
            cambio = round(efectivo_entregado - monto_efectivo, 2)

        transaccion = TransaccionComercial(
            items=items,
            total=total,
            cliente_nombre=(payload.cliente_nombre or "").strip(),
            cliente_nif=(payload.cliente_nif or "").strip(),
            metodo_pago=metodo,
            monto_efectivo=monto_efectivo,
            monto_tarjeta=monto_tarjeta,
            efectivo_entregado=efectivo_entregado,
            cambio=cambio,
            usuario=usuario,
        )

        # Registro atómico: obtiene id_transaccion (YYYY-NNN)
        id_transaccion = registrar_transaccion(transaccion, usuario)
        transaccion = transaccion.model_copy(update={"id_transaccion": id_transaccion})

        # Genera archivo Excel de factura
        ruta = generar_xlsx(transaccion)

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        logger.error("Error de sistema al generar factura: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="No se pudo generar la factura") from exc

    logger.info(
        "Factura %s generada. Cliente: %s  Total: %.2f  Método: %s",
        id_transaccion,
        transaccion.cliente_nombre or "(sin cliente)",
        total,
        metodo,
    )

    # Sink A — Impresión (síncrono, crítico para el flujo inmediato)
    ticket_impreso = False
    ticket_estado = "Ticket no solicitado."
    if payload.imprimir_ticket:
        try:
            encolar_impresion(transaccion, cola_impresion)
            ticket_impreso = True
            ticket_estado = "Ticket encolado para impresión."
        except Exception as exc:
            ticket_estado = f"No se pudo encolar ticket: {exc}"
            logger.warning(
                "Fallo al encolar ticket para %s: %s", id_transaccion, exc, exc_info=True
            )

    # Sink B — Auditoría Excel (background, no bloquea la respuesta)
    bg_tasks.add_task(anexar_a_excel, transaccion)

    return {
        "ok": True,
        "numero": id_transaccion,
        "archivo": ruta.name,
        "total": f"{total:.2f}",
        "cambio": cambio,
        "download_url": f"/api/descargar/{ruta.name}",
        "ticket_impreso": ticket_impreso,
        "ticket_estado": ticket_estado,
        "emisor": EMISOR_FACTURA,
    }


# ════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — Impresión
# ════════════════════════════════════════════════════════════════════════════

@app.get("/api/impresion/siguiente")
def siguiente_ticket(request: Request) -> JSONResponse:
    """
    Endpoint para poll_and_print.py.
    Retira el primer ticket de la cola y lo devuelve en base64.
    Responde 204 si la cola está vacía.
    """
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


# ════════════════════════════════════════════════════════════════════════════
# ENDPOINTS — Descarga de archivos
# ════════════════════════════════════════════════════════════════════════════

@app.get("/api/descargar/{nombre_archivo}")
def descargar(nombre_archivo: str, request: Request) -> FileResponse:
    _requiere_login(request)
    base_ruta = _ruta_facturas_efectiva()
    ruta = (base_ruta / nombre_archivo).resolve()

    try:
        ruta.relative_to(base_ruta)
    except ValueError:
        logger.warning("Intento de descarga con nombre inválido: %s", nombre_archivo)
        raise HTTPException(status_code=400, detail="Nombre de archivo inválido")

    if not ruta.exists():
        logger.warning(
            "Archivo no encontrado para descarga: %s (base actual: %s)",
            nombre_archivo,
            base_ruta,
        )
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    logger.info("Descarga de factura: %s", ruta.name)
    return FileResponse(
        path=ruta,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=ruta.name,
    )
