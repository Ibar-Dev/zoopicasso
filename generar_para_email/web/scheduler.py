"""
Sistema automático de cierres de Zoo Picasso.

Ejecuta automáticamente:
- Cierre de mañana: 14:00 diario
- Cierre de tarde: 22:00 diario
- Cierre de día completo: 22:05 diario
- Cierre de mes: 22:00 último día del mes
"""

import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.monthly_closure import (
    cerrar_mañana,
    cerrar_tarde,
    cerrar_día_completo,
    cerrar_mes,
)

logger = logging.getLogger(__name__)

# Instancia global del scheduler
scheduler = BackgroundScheduler()

# Estado global de automatización
automation_state = {
    "enabled": True,
    "last_execution": {},
    "last_error": {},
}


def _wrap_cierre(cierre_type: str, cierre_func):
    """Envuelve una función de cierre para agregar logging y manejo de errores."""

    def wrapper():
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


def init_scheduler():
    """Inicializa el scheduler con los cierres automáticos."""

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

        scheduler.start()
        logger.info("✅ Scheduler de cierres automáticos iniciado")

    except Exception as e:
        logger.error(f"❌ Error al inicializar scheduler: {e}")
        raise


def stop_scheduler():
    """Detiene el scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("⏹️ Scheduler de cierres detenido")


def pause_automation():
    """Pausa los cierres automáticos sin detener el scheduler."""
    automation_state["enabled"] = False
    for job in scheduler.get_jobs():
        job.pause()
    logger.warning("⏸️ Cierres automáticos pausados")


def resume_automation():
    """Reanuda los cierres automáticos."""
    automation_state["enabled"] = True
    for job in scheduler.get_jobs():
        job.resume()
    logger.warning("▶️ Cierres automáticos reanudados")


def get_automation_status():
    """Retorna el estado actual de la automatización."""
    jobs = []
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
        "enabled": automation_state["enabled"],
        "scheduler_running": scheduler.running,
        "jobs": jobs,
        "last_execution": automation_state["last_execution"],
        "last_error": automation_state["last_error"],
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
