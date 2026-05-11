import json
import logging
import sqlite3
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from src.ventas_store import RUTA_DB_VENTAS

logger = logging.getLogger(__name__)

_ARCHIVOS_JSON = ["contador_facturas.json", "precios_categorias.json"]
_ESTADO_FILE = "backup_estado.json"


def hacer_backup(backup_dir: Path, retener: int = 7) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    nombre = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    destino = backup_dir / nombre
    data_dir = RUTA_DB_VENTAS.parent

    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as zf:
        _backup_sqlite(zf)
        for nombre_json in _ARCHIVOS_JSON:
            ruta = data_dir / nombre_json
            if ruta.exists():
                zf.write(ruta, nombre_json)

    _purgar_viejos(backup_dir, retener)
    logger.info("Backup creado: %s", destino)
    return destino


def _backup_sqlite(zf: zipfile.ZipFile) -> None:
    tmp = RUTA_DB_VENTAS.parent / "_backup_tmp.db"
    try:
        src = sqlite3.connect(str(RUTA_DB_VENTAS))
        dst = sqlite3.connect(str(tmp))
        src.backup(dst)
        src.close()
        dst.close()
        zf.write(tmp, "ventas.db")
    finally:
        if tmp.exists():
            tmp.unlink()


def _purgar_viejos(backup_dir: Path, retener: int) -> None:
    zips = sorted(backup_dir.glob("backup_*.zip"))
    for viejo in zips[:-retener] if retener > 0 else []:
        viejo.unlink(missing_ok=True)
        logger.info("Backup antiguo eliminado: %s", viejo)


def leer_estado(data_dir: Path) -> dict:
    ruta = data_dir / _ESTADO_FILE
    if not ruta.exists():
        return {"ultimo": None, "backup_ok": None, "mensaje": ""}
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:
        return {"ultimo": None, "backup_ok": None, "mensaje": ""}


def guardar_estado(data_dir: Path, ok: bool, mensaje: str = "") -> None:
    ruta = data_dir / _ESTADO_FILE
    estado = {
        "ultimo": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "backup_ok": ok,
        "mensaje": mensaje,
    }
    ruta.write_text(json.dumps(estado, ensure_ascii=False), encoding="utf-8")
