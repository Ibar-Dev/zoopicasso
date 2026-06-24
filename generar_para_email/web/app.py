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
from typing import Optional, Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask
from starlette.middleware.sessions import SessionMiddleware

# Carga configuración de logging y rutas de facturas.
import src.settings  # noqa: F401
from src.factura_counter import siguiente_numero_factura
from src.factura_model import Factura, LineaFactura, PagoInfo
from src.monthly_closure import (
    cerrar_mes, cerrar_dia, cerrar_mañana, cerrar_tarde, cerrar_día_completo,
    obtener_resumen_cierre_mañana, obtener_resumen_cierre_tarde, obtener_resumen_cierre_dia_completo,
    RUTA_CIERRES
)
from web.scheduler import init_scheduler, stop_scheduler, get_automation_status, pause_automation, resume_automation, force_execution, get_routes_health
from src.printer import generar_ticket_escpos
from src.backup import guardar_estado, hacer_backup, leer_estado
from src.ventas_store import (
    historial_ventas,
    inicializar_db_ventas,
    listar_ajustes_activos,
    registrar_ajuste,
    registrar_ventas_factura,
    resumen_ventas_activas,
    resumen_ventas_activas_por_periodo,
    resumen_ventas_dia,
    resumen_ventas_dia_por_periodo,
    resumen_ventas_dia_completo,
)
from src.factura_writer import RUTA_FACTURAS, generar_factura_xlsx

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
PRECIOS_CATEGORIAS_PATH = BASE_DIR / "../data/precios_categorias.json"

USUARIO_VALIDO = "Giselle"
HASH_PASSWORD = "2aa2d838b21d5fe3fe9819640d83e40aea9f899d93b25a0ef9858ba9f83effda"

DATA_DIR = PRECIOS_CATEGORIAS_PATH.resolve().parent

_backup_dir_raw = os.getenv("BACKUP_DIR", "").strip()
BACKUP_DIR: Path | None = Path(_backup_dir_raw).expanduser().resolve() if _backup_dir_raw else None
BACKUP_INTERVALO_HORAS: int = int(os.getenv("BACKUP_INTERVALO_HORAS", "24"))
BACKUP_RETENER: int = int(os.getenv("BACKUP_RETENER", "7"))

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
    efectivo_entregado: Optional[float] = None


class MonthlyClosurePayload(BaseModel):
    confirmacion: bool = False


class AjustePayload(BaseModel):
    monto: float = Field(gt=0)


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
    task = None
    if BACKUP_DIR:
        task = asyncio.create_task(_tarea_backup())
        logger.info("Backup automático activado → %s (cada %dh)", BACKUP_DIR, BACKUP_INTERVALO_HORAS)
    else:
        logger.warning("BACKUP_DIR no configurado — backup automático desactivado")
    yield
    if task:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


app = FastAPI(title="Facturas Gisselle API", version="1.0.0", lifespan=lifespan)


# ════════════════════════════════════════════════════════════════════════════════
# COLA PERSISTENTE - Almacena tickets encolados en disco (JSON + base64)
# ════════════════════════════════════════════════════════════════════════════════
class ColaPersistente:
    """
    Cola thread-safe que persiste tickets en JSON.
    
    RESPONSABILIDAD:
      Mantener cola de tickets ESC/POS que sobrevive reinicios de Render.
      Los bytes se serializan en base64 para almacenarlos en JSON.
    
    COMUNICACIÓN:
      - Entrada: bytes (ESC/POS generados por src/printer.py)
      - Persistencia: data/cola_impresion.json
      - Salida: bytes (descodificados de base64 para impresora)
    
    MÉTODOS:
      - append(item: bytes) → Añade ticket y persiste
      - pop(index=0) → Retira y devuelve ticket, persiste
      - __len__() → Cantidad de tickets en cola
      - __bool__() → True si hay tickets
    """
    
    def __init__(self, ruta: Path | str = "data/cola_impresion.json"):
        self.ruta = Path(ruta) if isinstance(ruta, str) else ruta
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        # Ahora almacenamos list[dict] en lugar de list[str] para incluir metadatos
        self._datos: list[dict] = self._cargar()
    
    def _cargar(self) -> list[dict]:
        """Carga cola desde disco JSON. Realiza migración automática de strings a dicts."""
        if self.ruta.exists():
            try:
                with open(self.ruta, "r", encoding="utf-8") as f:
                    contenido = json.load(f)
                    tickets_base = []
                    if isinstance(contenido, dict) and "tickets" in contenido:
                        tickets_base = contenido["tickets"]
                    elif isinstance(contenido, list):
                        tickets_base = contenido
                    
                    # MIGRACIÓN: Convertir items antiguos (strings) al formato nuevo (dicts)
                    cola_migrada = []
                    for item in tickets_base:
                        if isinstance(item, str):
                            cola_migrada.append({"ticket": item, "archivo_xlsx": None})
                        else:
                            cola_migrada.append(item)
                    return cola_migrada
            except Exception as e:
                logger.error("Error al cargar cola desde %s: %s", self.ruta, e)
                return []
        return []
    
    def _guardar(self) -> None:
        """Persiste cola a disco JSON."""
        try:
            with open(self.ruta, "w", encoding="utf-8") as f:
                json.dump({"tickets": self._datos}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("Error al guardar cola en %s: %s", self.ruta, e)
    
    def append(self, item: bytes, archivo_nombre: Optional[str] = None) -> None:
        """
        Añade ticket y metadatos a la cola y persiste.
        
        Args:
            item: bytes en formato ESC/POS
            archivo_nombre: Nombre del archivo .xlsx asociado (opcional)
        """
        ticket_b64 = base64.b64encode(item).decode("ascii")
        self._datos.append({
            "ticket": ticket_b64,
            "archivo_xlsx": archivo_nombre
        })
        self._guardar()
    
    def pop(self, index: int = 0) -> dict:
        """
        Retira item de la cola y lo devuelve como diccionario.
        
        Args:
            index: Índice a remover (default: 0 = FIFO)
        
        Returns:
            dict: {"ticket": "base64...", "archivo_xlsx": "nombre.xlsx" | None}
        """
        item = self._datos.pop(index)
        self._guardar()
        return item
    
    def __len__(self) -> int:
        """Cantidad de tickets en cola."""
        return len(self._datos)
    
    def __bool__(self) -> bool:
        """True si hay tickets, False si vacía."""
        return len(self._datos) > 0
    
    def clear(self) -> None:
        """Vacía la cola y persiste los cambios (para testing)."""
        self._datos.clear()
        self._guardar()


# ────────────────────────────────────────────────────────────────────────────────
# Inicializar cola persistente
COLA_IMPRESION_RUTA = Path(__file__).parent.parent / "data" / "cola_impresion.json"
cola_impresion = ColaPersistente(COLA_IMPRESION_RUTA)
logger.info("Cola persistente inicializada: %s (%d tickets pendientes)", COLA_IMPRESION_RUTA, len(cola_impresion))


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
init_scheduler()  # Inicializar scheduler de cierres automáticos


def _anio_mes_actual() -> str:
    return date.today().strftime("%Y-%m")



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

@app.get("/api/keep-alive")
def keep_alive() -> JSONResponse:
    """
    Endpoint para prevenir spin-down de Render (Free tier).
    Responde rápidamente para mantener la instancia activa.
    No requiere autenticación - solo es un ping.
    """
    return JSONResponse({"status": "ok"}, status_code=200)

@app.get("/api/automation/status")
def automation_status(request: Request) -> JSONResponse:
    """Obtiene el estado de los cierres automáticos."""
    _requiere_login(request)
    return JSONResponse(get_automation_status())

@app.post("/api/automation/pause")
def automation_pause(request: Request) -> JSONResponse:
    """Pausa los cierres automáticos."""
    _requiere_login(request)
    pause_automation()
    return JSONResponse({"status": "paused"})

@app.post("/api/automation/resume")
def automation_resume(request: Request) -> JSONResponse:
    """Reanuda los cierres automáticos."""
    _requiere_login(request)
    resume_automation()
    return JSONResponse({"status": "resumed"})

@app.post("/api/automation/force/{cierre_type}")
def automation_force(cierre_type: str, request: Request) -> JSONResponse:
    """Ejecuta un cierre de forma inmediata (forzado)."""
    _requiere_login(request)
    result = force_execution(cierre_type)
    return JSONResponse(result)

@app.get("/api/rutas/estado")
def rutas_estado(request: Request) -> JSONResponse:
    """Obtiene el estado de salud de las rutas de cierre.
    
    Valida que todas las carpetas de cierre sean accesibles.
    Retorna información sobre cada tipo de cierre (mañana, tarde, día_completo, mes).
    """
    _requiere_login(request)
    health = get_routes_health()
    return JSONResponse(health)

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


@app.get("/api/ganancias/resumen")
def get_ganancias_resumen(request: Request) -> dict:
    _requiere_login(request)
    anio_mes = _anio_mes_actual()
    resumen = resumen_ventas_activas(anio_mes)
    resumen_hoy = resumen_ventas_dia(date.today().isoformat())
    return {
        "ok": True,
        "resumen": resumen,
        "resumen_hoy": resumen_hoy,
    }


@app.get("/api/ganancias/resumen-periodo")
def get_ganancias_resumen_periodo(request: Request) -> dict:
    """
    Obtiene resumen de ventas por período (mañana/tarde/día completo) para mes actual y hoy.
    
    Períodos: Mañana (6-14h), Tarde (14-22h) y Día Completo (6-22h) en hora local.
    
    Returns:
        {
            "ok": True,
            "resumen_mes": {...mañana..., ...tarde...},
            "resumen_hoy": {...mañana..., ...tarde..., ...dia_completo...}
        }
    """
    _requiere_login(request)
    anio_mes = _anio_mes_actual()
    resumen_mes = resumen_ventas_activas_por_periodo(anio_mes)
    resumen_hoy = resumen_ventas_dia_por_periodo(date.today().isoformat())
    resumen_hoy["dia_completo"] = resumen_ventas_dia_completo(date.today().isoformat())
    
    return {
        "ok": True,
        "resumen_mes": resumen_mes,
        "resumen_hoy": resumen_hoy,
    }


@app.get("/api/ganancias/resumen-periodo-fecha")
def get_ganancias_resumen_periodo_fecha(request: Request, fecha: str = "") -> dict:
    """
    Obtiene resumen de ventas por período (mañana/tarde/día completo) para una fecha específica.
    
    Args:
        fecha: Formato YYYY-MM-DD (ej: 2026-06-11). Si no se proporciona, usa hoy.
    
    Returns:
        {
            "ok": True,
            "resumen": {
                "fecha": "2026-06-11",
                "total": 150.00,
                "mañana": {total, cantidad, por_categoria},
                "tarde": {total, cantidad, por_categoria},
                "dia_completo": {total, cantidad, por_categoria}
            }
        }
    """
    _requiere_login(request)
    if not fecha:
        fecha = date.today().isoformat()
    
    resumen = resumen_ventas_dia_por_periodo(fecha)
    resumen["dia_completo"] = resumen_ventas_dia_completo(fecha)
    
    return {
        "ok": True,
        "resumen": resumen,
    }


@app.get("/api/ganancias/resumen-periodo-mes")
def get_ganancias_resumen_periodo_mes(request: Request, anio_mes: str = "") -> dict:
    """
    Obtiene resumen de ventas por período (mañana/tarde) para un mes específico.
    
    Args:
        anio_mes: Formato YYYY-MM (ej: 2026-06). Si no se proporciona, usa mes actual.
    
    Returns:
        {
            "ok": True,
            "resumen": {
                "anio_mes": "2026-06",
                "total": 500.00,
                "mañana": {total, cantidad, total_efectivo, total_tarjeta, por_categoria},
                "tarde": {total, cantidad, total_efectivo, total_tarjeta, por_categoria}
            }
        }
    """
    _requiere_login(request)
    if not anio_mes:
        anio_mes = _anio_mes_actual()
    resumen = resumen_ventas_activas_por_periodo(anio_mes)
    return {
        "ok": True,
        "resumen": resumen,
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
    anio_mes = _anio_mes_actual()
    return {"ok": True, "ajustes": listar_ajustes_activos(anio_mes)}


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


@app.post("/api/ganancias/cierre-mes")
def cierre_mensual(payload: MonthlyClosurePayload, request: Request):
    _requiere_login(request)
    if not payload.confirmacion:
        raise HTTPException(status_code=400, detail="Confirmación requerida para cerrar mes")
    usuario = str(request.session.get("usuario", "(desconocido)"))
    meta, archivo = cerrar_mes(usuario=usuario)
    if archivo is None:
        return JSONResponse(meta)
    return FileResponse(
        path=archivo,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=archivo.name,
        headers={
            "x-cierre-mes": meta["anio_mes"],
            "x-cierre-ventas": str(meta["cantidad_ventas"]),
            "x-cierre-total": str(meta["total"]),
            "x-cierre-mensaje": meta["mensaje"],
        },
    )

@app.post("/api/ganancias/cierre-dia")
def cierre_diario(payload: MonthlyClosurePayload, request: Request):
    _requiere_login(request)
    if not payload.confirmacion:
        raise HTTPException(status_code=400, detail="Confirmación requerida para cerrar día")
    usuario = str(request.session.get("usuario", "(desconocido)"))
    meta, archivo = cerrar_dia(usuario=usuario)
    if archivo is None:
        return JSONResponse(meta)
    return FileResponse(
        path=archivo,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=archivo.name,
        headers={
            "x-cierre-fecha": meta["fecha"],
            "x-cierre-ventas": str(meta["cantidad_ventas"]),
            "x-cierre-total": str(meta["total"]),
            "x-cierre-mensaje": meta["mensaje"],
        },
    )


@app.get("/api/ganancias/estado-cierres")
def estado_cierres(request: Request):
    """Obtiene el estado de los cierres del día actual (qué tipos fueron completados)."""
    from src.ventas_store import obtener_cierres_hoy
    from datetime import datetime
    
    _requiere_login(request)
    fecha = datetime.now().strftime("%Y-%m-%d")
    estado = obtener_cierres_hoy(fecha)
    return JSONResponse(estado)


@app.post("/api/ganancias/cierre-mañana")
def cierre_mañana_endpoint(payload: MonthlyClosurePayload, request: Request):
    """Realiza el cierre de mañana en dos pasos:
    - confirmacion=false: devuelve dinero_bruto en JSON (FASE 3)
    - confirmacion=true: genera Excel y registra (FASE 4)
    """
    from datetime import datetime
    _requiere_login(request)
    usuario = str(request.session.get("usuario", "(desconocido)"))
    fecha = datetime.now().strftime("%Y-%m-%d")
    
    if not payload.confirmacion:
        # FASE 3: Mostrar ganancia bruta sin registrar
        try:
            resumen = obtener_resumen_cierre_mañana(fecha)
            return JSONResponse(resumen)
        except Exception as e:
            logger.error("Error al obtener resumen mañana: %s", e)
            return JSONResponse({"ok": False, "mensaje": str(e)}, status_code=400)
    
    # FASE 4: Si confirmacion=true, generar Excel y registrar
    meta, archivo = cerrar_mañana(usuario=usuario)
    if not meta.get("ok"):
        return JSONResponse(meta, status_code=400)
    if archivo is None:
        return JSONResponse(meta)
    return FileResponse(
        path=archivo,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=archivo.name,
        headers={
            "x-cierre-tipo": "morning",
            "x-cierre-fecha": meta["fecha"],
            "x-cierre-ventas": str(meta["cantidad_ventas"]),
            "x-cierre-total": str(meta["total"]),
            "x-cierre-mensaje": meta["mensaje"],
            "x-cierre-ruta": str(archivo),
        },
    )


@app.post("/api/ganancias/cierre-tarde")
def cierre_tarde_endpoint(payload: MonthlyClosurePayload, request: Request):
    """Realiza el cierre de tarde en dos pasos:
    - confirmacion=false: devuelve dinero_bruto en JSON (FASE 3)
    - confirmacion=true: genera Excel y registra (FASE 4)
    """
    from datetime import datetime
    _requiere_login(request)
    usuario = str(request.session.get("usuario", "(desconocido)"))
    fecha = datetime.now().strftime("%Y-%m-%d")
    
    if not payload.confirmacion:
        # FASE 3: Mostrar ganancia bruta sin registrar
        try:
            resumen = obtener_resumen_cierre_tarde(fecha)
            return JSONResponse(resumen)
        except Exception as e:
            logger.error("Error al obtener resumen tarde: %s", e)
            return JSONResponse({"ok": False, "mensaje": str(e)}, status_code=400)
    
    # FASE 4: Si confirmacion=true, generar Excel y registrar
    meta, archivo = cerrar_tarde(usuario=usuario)
    if not meta.get("ok"):
        return JSONResponse(meta, status_code=400)
    if archivo is None:
        return JSONResponse(meta)
    return FileResponse(
        path=archivo,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=archivo.name,
        headers={
            "x-cierre-tipo": "afternoon",
            "x-cierre-fecha": meta["fecha"],
            "x-cierre-ventas": str(meta["cantidad_ventas"]),
            "x-cierre-total": str(meta["total"]),
            "x-cierre-mensaje": meta["mensaje"],
            "x-cierre-ruta": str(archivo),
        },
    )


@app.post("/api/ganancias/cierre-dia-completo")
def cierre_dia_completo_endpoint(payload: MonthlyClosurePayload, request: Request):
    """Realiza el cierre del día completo en dos pasos:
    - confirmacion=false: devuelve dinero_bruto en JSON (FASE 3)
    - confirmacion=true: genera Excel y registra (FASE 4)
    """
    from datetime import datetime
    _requiere_login(request)
    usuario = str(request.session.get("usuario", "(desconocido)"))
    fecha = datetime.now().strftime("%Y-%m-%d")
    
    if not payload.confirmacion:
        # FASE 3: Mostrar ganancia bruta sin registrar
        try:
            resumen = obtener_resumen_cierre_dia_completo(fecha)
            return JSONResponse(resumen)
        except Exception as e:
            logger.error("Error al obtener resumen día completo: %s", e)
            return JSONResponse({"ok": False, "mensaje": str(e)}, status_code=400)
    
    # FASE 4: Si confirmacion=true, generar Excel y registrar
    meta, archivo = cerrar_día_completo(usuario=usuario)
    if not meta.get("ok"):
        return JSONResponse(meta, status_code=400)
    if archivo is None:
        return JSONResponse(meta)
    return FileResponse(
        path=archivo,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=archivo.name,
        headers={
            "x-cierre-tipo": "full_day",
            "x-cierre-fecha": meta["fecha"],
            "x-cierre-ventas": str(meta["cantidad_ventas"]),
            "x-cierre-total": str(meta["total"]),
            "x-cierre-mensaje": meta["mensaje"],
            "x-cierre-ruta": str(archivo),
        },
    )


@app.get("/api/ganancias/descargar-cierre/{nombre_archivo}")
def descargar_cierre(nombre_archivo: str, request: Request) -> FileResponse:
    _requiere_login(request)
    ruta = (RUTA_CIERRES / nombre_archivo).resolve()
    if not str(ruta).startswith(str(RUTA_CIERRES.resolve())):
        logger.warning("Intento de descarga de cierre con nombre inválido: %s", nombre_archivo)
        raise HTTPException(status_code=400, detail="Nombre de archivo inválido")
    if not ruta.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    logger.info("Descarga de cierre mensual: %s", ruta.name)
    return FileResponse(
        path=ruta,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=ruta.name,
    )

@app.post("/api/generar")
def generar(payload: FacturaPayload, request: Request) -> dict[str, object]:
    _requiere_login(request)
    # Validación método de pago y montos
    metodo = payload.metodo_pago
    monto_efectivo = payload.monto_efectivo
    monto_tarjeta = payload.monto_tarjeta
    tolerancia = 0.01
    efectivo_entregado = payload.efectivo_entregado if payload.efectivo_entregado is not None else 0.0
    cambio = 0.0


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
                raise HTTPException(status_code=400, detail="El Monto del Total debe ser igual al total.")
            if monto_tarjeta not in (None, 0):
                raise HTTPException(status_code=400, detail="El monto en tarjeta debe ser 0 para pago en efectivo.")
            if efectivo_entregado < monto_efectivo:
                raise HTTPException(status_code=400, detail="El efectivo entregado debe ser igual o mayor al total.")
            cambio = round(efectivo_entregado - monto_efectivo, 2)
        elif metodo == "tarjeta":
            if monto_tarjeta is None or monto_tarjeta <= 0 or abs(monto_tarjeta - total) > tolerancia:
                raise HTTPException(status_code=400, detail="El monto en tarjeta debe ser igual al total.")
            if monto_efectivo not in (None, 0):
                raise HTTPException(status_code=400, detail="El Monto del Total debe ser 0 para pago con tarjeta.")
            efectivo_entregado = 0.0
            cambio = 0.0
        elif metodo == "mixto":
            if monto_efectivo is None or monto_efectivo < 0 or monto_efectivo > total:
                raise HTTPException(status_code=400, detail="El Monto del Total debe ser entre 0 y el total.")
            if monto_tarjeta is None:
                raise HTTPException(status_code=400, detail="Falta el monto en tarjeta para pago mixto.")
            if monto_tarjeta < 0 or abs(monto_efectivo + monto_tarjeta - total) > tolerancia:
                raise HTTPException(status_code=400, detail="La suma de efectivo y tarjeta debe ser igual al total.")
            if efectivo_entregado < monto_efectivo:
                raise HTTPException(status_code=400, detail="El efectivo entregado debe ser igual o mayor al efectivo a pagar.")
            cambio = round(efectivo_entregado - monto_efectivo, 2)
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
    pago = PagoInfo(
        monto_total=total,
        monto_efectivo=monto_efectivo or 0,
        monto_tarjeta=monto_tarjeta or 0,
        metodo_pago=metodo,
        efectivo_entregado=efectivo_entregado,
        cambio=cambio,
    )
    registrar_ventas_factura(factura, usuario, pago)
    ticket_impreso = False
    ticket_estado = "Ticket no solicitado."
    if payload.imprimir_ticket:
        try:
            ticket = generar_ticket_escpos(factura, ancho=42, pago=pago)
            cola_impresion.append(ticket, archivo_nombre=ruta.name)
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
        "cambio": cambio,
        "download_url": f"/api/descargar/{ruta.name}",
        "ticket_impreso": ticket_impreso,
        "ticket_estado": ticket_estado,
        "emisor": EMISOR_FACTURA,
    }

@app.get("/api/impresion/siguiente")
def siguiente_ticket(request: Request) -> JSONResponse:
    """
    Endpoint para poll_and_print.py - Retira ticket de la cola persistente.
    
    RESPONSABILIDAD:
      Despacha tickets ESC/POS a agents Windows para impresión.
    
    AUTENTICACIÓN:
      Requiere sesión válida (login).
    
    FLUJO:
      1. Verifica si hay tickets en cola_impresion
      2. Si vacía → 204 No Content (cliente debe reintentar)
      3. Si hay → pop(0) retira primero ticket
      4. Encoda base64 para transporte JSON
      5. Responde 200 OK con ticket_b64
    
    COMUNICACIÓN:
      - Entrada: GET request (poll desde Windows)
      - Cola: cola_impresion (ColaPersistente)
      - Salida: JSON {hay_ticket: bool, ticket_b64: str}
      - Cliente: poll_and_print.py desencoda y imprime
    
    EJEMPLO CLIENTE (poll_and_print.py):
      resp = session.get("{RENDER_URL}/api/impresion/siguiente", timeout=10)
      if resp.status_code == 200:
          ticket_bytes = base64.b64decode(resp.json()["ticket_b64"])
          imprimir_ticket_usb_windows(ticket_bytes)
      elif resp.status_code == 204:
          # Nada en cola, esperar 3 segundos
    """
    if not cola_impresion:
        # Cola vacía - cliente debe reintentar más tarde
        return JSONResponse({"hay_ticket": False}, status_code=204)
    
    # Despacha ticket (FIFO)
    item = cola_impresion.pop(0)
    ticket_b64 = item["ticket"]
    archivo_xlsx = item["archivo_xlsx"]
    
    logger.info(
        "Ticket despachado (archivo: %s, quedan %d en cola)",
        archivo_xlsx,
        len(cola_impresion),
    )
    return JSONResponse({
        "hay_ticket": True,
        "ticket_b64": ticket_b64,
        "archivo_xlsx": archivo_xlsx
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
