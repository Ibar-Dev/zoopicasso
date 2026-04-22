import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from src.factura_model import Factura

logger = logging.getLogger(__name__)

_BASE = Path(__file__).resolve().parent.parent


def _ruta_db_ventas() -> Path:
    valor = os.getenv("VENTAS_DB_PATH", "").strip()
    if not valor:
        return (_BASE / "data" / "ventas.db").resolve()
    ruta = Path(valor).expanduser()
    if not ruta.is_absolute():
        ruta = _BASE / ruta
    return ruta.resolve()


RUTA_DB_VENTAS = _ruta_db_ventas()


def _connect() -> sqlite3.Connection:
    RUTA_DB_VENTAS.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(RUTA_DB_VENTAS)
    conn.row_factory = sqlite3.Row
    return conn


def inicializar_db_ventas() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_factura TEXT NOT NULL,
                fecha_venta TEXT NOT NULL,
                anio_mes TEXT NOT NULL,
                categoria TEXT NOT NULL,
                monto REAL NOT NULL,
                estado TEXT NOT NULL DEFAULT 'active',
                cliente_nombre TEXT NOT NULL DEFAULT '',
                usuario TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                archived_at TEXT,
                cierre_id TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cierres_mensuales (
                cierre_id TEXT PRIMARY KEY,
                anio_mes TEXT NOT NULL,
                usuario TEXT NOT NULL,
                created_at TEXT NOT NULL,
                total REAL NOT NULL,
                cantidad_ventas INTEGER NOT NULL,
                archivo_excel TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_ventas_estado_mes
            ON ventas (estado, anio_mes)
            """
        )


def registrar_ventas_factura(factura: Factura, usuario: str) -> None:
    inicializar_db_ventas()
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    anio_mes = factura.fecha.strftime("%Y-%m")
    filas = [
        (
            factura.numero_formateado,
            factura.fecha.isoformat(),
            anio_mes,
            (linea.categoria or "sin_categoria").strip() or "sin_categoria",
            float(linea.total),
            (factura.cliente_nombre or "").strip(),
            (usuario or "").strip(),
            created_at,
        )
        for linea in factura.lineas
    ]
    with _connect() as conn:
        conn.executemany(
            """
            INSERT INTO ventas (
                numero_factura, fecha_venta, anio_mes, categoria, monto,
                cliente_nombre, usuario, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            filas,
        )
    logger.info(
        "Ventas registradas en buffer mensual. factura=%s filas=%d",
        factura.numero_formateado,
        len(filas),
    )


def resumen_ventas_activas(anio_mes: str) -> dict:
    inicializar_db_ventas()
    with _connect() as conn:
        total_row = conn.execute(
            """
            SELECT COALESCE(SUM(monto), 0) AS total, COUNT(*) AS cantidad
            FROM ventas
            WHERE estado = 'active' AND anio_mes = ?
            """,
            (anio_mes,),
        ).fetchone()
        cat_rows = conn.execute(
            """
            SELECT categoria, COALESCE(SUM(monto), 0) AS total
            FROM ventas
            WHERE estado = 'active' AND anio_mes = ?
            GROUP BY categoria
            ORDER BY categoria ASC
            """,
            (anio_mes,),
        ).fetchall()

    por_categoria = {row["categoria"]: round(float(row["total"]), 2) for row in cat_rows}
    return {
        "anio_mes": anio_mes,
        "total": round(float(total_row["total"]), 2),
        "cantidad_ventas": int(total_row["cantidad"]),
        "por_categoria": por_categoria,
    }


def ventas_activas_detalle(anio_mes: str) -> list[dict]:
    inicializar_db_ventas()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, numero_factura, fecha_venta, categoria, monto, cliente_nombre, usuario
            FROM ventas
            WHERE estado = 'active' AND anio_mes = ?
            ORDER BY id ASC
            """,
            (anio_mes,),
        ).fetchall()
    return [dict(row) for row in rows]


def archivar_ventas_activas(anio_mes: str, cierre_id: str, archived_at: str) -> int:
    inicializar_db_ventas()
    with _connect() as conn:
        cur = conn.execute(
            """
            UPDATE ventas
            SET estado = 'archived', archived_at = ?, cierre_id = ?
            WHERE estado = 'active' AND anio_mes = ?
            """,
            (archived_at, cierre_id, anio_mes),
        )
        return int(cur.rowcount)


def registrar_cierre(
    cierre_id: str,
    anio_mes: str,
    usuario: str,
    created_at: str,
    total: float,
    cantidad_ventas: int,
    archivo_excel: str,
) -> None:
    inicializar_db_ventas()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO cierres_mensuales (
                cierre_id, anio_mes, usuario, created_at, total, cantidad_ventas, archivo_excel
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cierre_id,
                anio_mes,
                (usuario or "").strip(),
                created_at,
                float(total),
                int(cantidad_ventas),
                archivo_excel,
            ),
        )
