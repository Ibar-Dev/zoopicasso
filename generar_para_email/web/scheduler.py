"""
Sistema automático de cierres de Zoo Picasso.

Ejecuta automáticamente:
- Cierre de mañana: 14:00 diario
- Cierre de tarde: 22:00 diario
- Cierre de día completo: 22:05 diario
- Cierre de mes: 22:00 último día del mes
"""

import json
import logging
from importlib import import_module
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    BackgroundScheduler = import_module(
        "apscheduler.schedulers.background"
    ).BackgroundScheduler
    CronTrigger = import_module("apscheduler.triggers.cron").CronTrigger
except ModuleNotFoundError as exc:
    BackgroundScheduler = None
    CronTrigger = None
    APSCHEDULER_IMPORT_ERROR = exc
else:
    APSCHEDULER_IMPORT_ERROR = None

from src.monthly_closure import (
    cerrar_mañana,
    cerrar_tarde,
    cerrar_día_completo,
    cerrar_mes,
)

logger = logging.getLogger(__name__)

APSCHEDULER_AVAILABLE = APSCHEDULER_IMPORT_ERROR is None

# Rutas para persistencia del estado
_BASE = Path(__file__).resolve().parent.parent
DATA_DIR = _BASE / "data"
AUTOMATION_STATE_FILE = DATA_DIR / "automation_state.json"

# Instancia global del scheduler
scheduler: Any | None = BackgroundScheduler() if APSCHEDULER_AVAILABLE else None

# Estado global de automatización
automation_state = {
    "available": APSCHEDULER_AVAILABLE,
    "enabled": APSCHEDULER_AVAILABLE,
    "last_execution": {},
    "last_error": {},
    "reason_unavailable": str(APSCHEDULER_IMPORT_ERROR)
    if APSCHEDULER_IMPORT_ERROR
    else None,
}


def _load_automation_state_from_file() -> bool | None:
    """Carga el estado persisti desde archivo. Retorna None si archivo no existe."""
    if not AUTOMATION_STATE_FILE.exists():
        return None
    try:
        with open(AUTOMATION_STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("enabled", APSCHEDULER_AVAILABLE)
    except Exception as e:
        logger.warning(f"No se pudo cargar estado de automatización: {e}")
        return None


def _save_automation_state_to_file(enabled: bool) -> None:
    """Guarda el estado de automatización en archivo."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(AUTOMATION_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"enabled": enabled, "timestamp": datetime.now().isoformat()}, f, indent=2)
    except Exception as e:
        logger.error(f"No se pudo guardar estado de automatización: {e}")


def _wrap_cierre(cierre_type: str, cierre_func):
    """Envuelve una función de cierre para agregar logging y manejo de errores."""

    def wrapper():
        # ✅ Verificación defensiva: si automatización está pausada, no ejecutar
        if not automation_state["enabled"]:
            logger.debug(f"⏸️ Cierre de {cierre_type} saltado (automatización pausada)")
            return
        
        try:
            logger.info(f"[AUTOMÁTICO] Iniciando cierre de {cierre_type}...")
            meta, archivo = cierre_func(usuario="SISTEMA")

            automation_state["last_execution"][cierre_type] = {
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "archivo": str(archivo) if archivo else None,
                "meta": meta,
            }
            automation_state["last_error"].pop(cierre_type, None)

            logger.info(
                f"✓ Cierre de {cierre_type} completado automáticamente"
            )
            return {"status": "success", "type": cierre_type, "meta": meta}

        except Exception as e:
            error_msg = str(e)
            automation_state["last_error"][cierre_type] = {
                "timestamp": datetime.now().isoformat(),
                "error": error_msg,
            }
            logger.error(
                f"✗ Error en cierre automático de {cierre_type}: {error_msg}"
            )
            return {"status": "error", "type": cierre_type, "error": error_msg}

    return wrapper


# Archivo para guardar estado de salud de rutas
ROUTES_HEALTH_FILE = DATA_DIR / "routes_health_check.json"


def _validar_salud_rutas():
    """Valida que todas las rutas de cierre sean accesibles.
    
    Se ejecuta periódicamente y guarda resultado en routes_health_check.json
    """
    from src.monthly_closure import (
        validar_y_crear_ruta,
        RUTA_CIERRE_MANANA,
        RUTA_CIERRE_TARDE,
        RUTA_CIERRE_DIA_COMPLETO,
        RUTA_CIERRE_MES,
    )
    
    rutas_a_validar = {
        "mañana": RUTA_CIERRE_MANANA,
        "tarde": RUTA_CIERRE_TARDE,
        "día_completo": RUTA_CIERRE_DIA_COMPLETO,
        "mes": RUTA_CIERRE_MES,
    }
    
    health_status = {
        "timestamp": datetime.now().isoformat(),
        "routes": {},
    }
    
    all_ok = True
    for tipo_cierre, ruta in rutas_a_validar.items():
        try:
            éxito, msg_usuario, msg_log = validar_y_crear_ruta(ruta)
            health_status["routes"][tipo_cierre] = {
                "ruta": str(ruta),
                "ok": éxito,
                "mensaje": msg_usuario,
                "timestamp": datetime.now().isoformat(),
            }
            if not éxito:
                all_ok = False
                logger.warning(f"⚠️ Problema con ruta de {tipo_cierre}: {msg_usuario}")
        except Exception as e:
            health_status["routes"][tipo_cierre] = {
                "ruta": str(ruta),
                "ok": False,
                "mensaje": f"Error validando: {str(e)}",
                "timestamp": datetime.now().isoformat(),
            }
            all_ok = False
            logger.error(f"❌ Error validando ruta de {tipo_cierre}: {e}")
    
    health_status["all_ok"] = all_ok
    
    # Guardar resultado
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(ROUTES_HEALTH_FILE, "w", encoding="utf-8") as f:
            json.dump(health_status, f, indent=2)
        logger.debug(f"✓ Health check de rutas guardado: {ROUTES_HEALTH_FILE}")
    except Exception as e:
        logger.error(f"❌ No se pudo guardar health check: {e}")
    
    return health_status


def init_scheduler():
    """Inicializa el scheduler con los cierres automáticos."""

    if scheduler is None:
        logger.warning(
            "APScheduler no está instalado; cierres automáticos desactivados"
        )
        automation_state["enabled"] = False
        return

    if scheduler.running:
        logger.warning("Scheduler ya está en ejecución")
        return

    try:
        # Cierre de mañana: 14:00 todos los días
        scheduler.add_job(
            _wrap_cierre("mañana", cerrar_mañana),
            trigger=CronTrigger(hour=14, minute=0),
            id="cierre_mañana",
            name="Cierre de mañana automático",
            replace_existing=True,
            max_instances=1,
        )
        logger.info("📅 Programado: Cierre de mañana a las 14:00")

        # Cierre de tarde: 22:00 todos los días
        scheduler.add_job(
            _wrap_cierre("tarde", cerrar_tarde),
            trigger=CronTrigger(hour=22, minute=0),
            id="cierre_tarde",
            name="Cierre de tarde automático",
            replace_existing=True,
            max_instances=1,
        )
        logger.info("📅 Programado: Cierre de tarde a las 22:00")

        # Cierre de día completo: 22:05 (después del cierre de tarde)
        scheduler.add_job(
            _wrap_cierre("día_completo", cerrar_día_completo),
            trigger=CronTrigger(hour=22, minute=5),
            id="cierre_dia_completo",
            name="Cierre de día completo automático",
            replace_existing=True,
            max_instances=1,
        )
        logger.info("📅 Programado: Cierre de día completo a las 22:05")

        # Cierre de mes: 22:00 último día de cada mes
        scheduler.add_job(
            _wrap_cierre("mes", cerrar_mes),
            trigger=CronTrigger(day="last", hour=22, minute=0),
            id="cierre_mes",
            name="Cierre del mes automático",
            replace_existing=True,
            max_instances=1,
        )
        logger.info("📅 Programado: Cierre del mes a las 22:00 (último día)")

        # Health check de rutas: cada 30 minutos
        from apscheduler.triggers.interval import IntervalTrigger
        scheduler.add_job(
            _validar_salud_rutas,
            trigger=IntervalTrigger(minutes=30),
            id="health_check_rutas",
            name="Validación de rutas de cierre",
            replace_existing=True,
            max_instances=1,
        )
        logger.info("📅 Programado: Health check de rutas cada 30 minutos")

        scheduler.start()
        logger.info("✅ Scheduler de cierres automáticos iniciado")
        
        # Cargar estado de automatización desde archivo (si fue pausado antes)
        saved_state = _load_automation_state_from_file()
        if saved_state is not None:
            automation_state["enabled"] = saved_state
            if not saved_state:
                logger.info("⏸️ Restituyendo estado pausado de automatización")
                pause_automation()
            else:
                logger.info("▶️ Automatización reanudada desde estado guardado")

    except Exception as e:
        logger.error(f"❌ Error al inicializar scheduler: {e}")
        raise


def stop_scheduler():
    """Detiene el scheduler."""
    if scheduler and scheduler.running:
        scheduler.shutdown()
        logger.info("⏹️ Scheduler de cierres detenido")


def pause_automation():
    """Pausa los cierres automáticos sin detener el scheduler."""
    if scheduler is None:
        automation_state["enabled"] = False
        _save_automation_state_to_file(False)
        logger.warning(
            "No se puede pausar la automatización porque APScheduler no está disponible"
        )
        return

    automation_state["enabled"] = False
    _save_automation_state_to_file(False)
    for job in scheduler.get_jobs():
        job.pause()
    logger.warning("⏸️ Cierres automáticos pausados")


def resume_automation():
    """Reanuda los cierres automáticos."""
    if scheduler is None:
        automation_state["enabled"] = False
        _save_automation_state_to_file(False)
        logger.warning(
            "No se puede reanudar la automatización porque APScheduler no está disponible"
        )
        return

    automation_state["enabled"] = True
    _save_automation_state_to_file(True)
    for job in scheduler.get_jobs():
        job.resume()
    logger.warning("▶️ Cierres automáticos reanudados")


def get_automation_status():
    """Retorna el estado actual de la automatización."""
    jobs = []
    if scheduler is not None:
        for job in scheduler.get_jobs():
            jobs.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "trigger": str(job.trigger),
                    "next_run": job.next_run_time.isoformat()
                    if job.next_run_time
                    else None,
                }
            )

    return {
        "available": automation_state["available"],
        "enabled": automation_state["enabled"],
        "scheduler_running": bool(scheduler and scheduler.running),
        "jobs": jobs,
        "last_execution": automation_state["last_execution"],
        "last_error": automation_state["last_error"],
        "reason_unavailable": automation_state["reason_unavailable"],
    }


def force_execution(cierre_type: str):
    """Ejecuta un cierre de forma inmediata (forzada)."""
    cierre_functions = {
        "mañana": cerrar_mañana,
        "tarde": cerrar_tarde,
        "día_completo": cerrar_día_completo,
        "mes": cerrar_mes,
    }

    if cierre_type not in cierre_functions:
        return {"status": "error", "error": f"Tipo de cierre inválido: {cierre_type}"}

    return _wrap_cierre(cierre_type, cierre_functions[cierre_type])()


def get_routes_health():
    """Retorna el estado de salud de las rutas de cierre.
    
    Lee el archivo generado por el health check periódico.
    """
    if not ROUTES_HEALTH_FILE.exists():
        # Si no existe el archivo, ejecutar health check ahora
        logger.info("Health check no generado aún, ejecutando ahora...")
        return _validar_salud_rutas()
    
    try:
        with open(ROUTES_HEALTH_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error leyendo health check: {e}")
        # Si hay error, ejecutar nuevamente
        return _validar_salud_rutas()
