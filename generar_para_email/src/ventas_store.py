import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from factura_model import Factura, PagoInfo

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


@contextmanager
def _connect():
    RUTA_DB_VENTAS.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(RUTA_DB_VENTAS)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()


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
            CREATE TABLE IF NOT EXISTS pagos_factura (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_factura TEXT NOT NULL,
                fecha_venta TEXT NOT NULL,
                anio_mes TEXT NOT NULL,
                monto_total REAL NOT NULL,
                monto_efectivo REAL NOT NULL,
                monto_tarjeta REAL NOT NULL,
                metodo_pago TEXT NOT NULL,
                estado TEXT NOT NULL DEFAULT 'active',
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
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_pagos_estado_mes
            ON pagos_factura (estado, anio_mes)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ajustes_manuales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                anio_mes TEXT NOT NULL,
                usuario TEXT NOT NULL,
                monto REAL NOT NULL,
                estado TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                archived_at TEXT,
                cierre_id TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_ajustes_estado_mes
            ON ajustes_manuales (estado, anio_mes)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cierres_diarios (
                cierre_id TEXT PRIMARY KEY,
                fecha TEXT NOT NULL,
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
            CREATE INDEX IF NOT EXISTS idx_cierres_diarios_fecha
            ON cierres_diarios (fecha)
            """
        )


def registrar_ventas_factura(factura: Factura, usuario: str, pago: PagoInfo | None = None) -> None:
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
        if pago:
            conn.execute(
                """
                INSERT INTO pagos_factura (
                    numero_factura, fecha_venta, anio_mes, monto_total, monto_efectivo, monto_tarjeta, metodo_pago, usuario, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    factura.numero_formateado,
                    factura.fecha.isoformat(),
                    anio_mes,
                    pago.monto_total,
                    pago.monto_efectivo,
                    pago.monto_tarjeta,
                    pago.metodo_pago,
                    (usuario or '').strip(),
                    created_at,
                )
            )
    logger.info(
        "Ventas registradas en buffer mensual. factura=%s filas=%d pago=%s",
        factura.numero_formateado,
        len(filas),
        pago,
    )


def registrar_ajuste(anio_mes: str, usuario: str, monto: float) -> None:
    inicializar_db_ventas()
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO ajustes_manuales (anio_mes, usuario, monto, estado, created_at)
            VALUES (?, ?, ?, 'active', ?)
            """,
            (anio_mes, usuario, round(monto, 2), created_at),
        )


def archivar_ajustes_activos(anio_mes: str, cierre_id: str, archived_at: str) -> None:
    inicializar_db_ventas()
    with _connect() as conn:
        conn.execute(
            """
            UPDATE ajustes_manuales
            SET estado = 'archived', archived_at = ?, cierre_id = ?
            WHERE estado = 'active' AND anio_mes = ?
            """,
            (archived_at, cierre_id, anio_mes),
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
        pago_row = conn.execute(
            """
            SELECT COALESCE(SUM(monto_efectivo), 0) AS total_efectivo, COALESCE(SUM(monto_tarjeta), 0) AS total_tarjeta
            FROM pagos_factura
            WHERE estado = 'active' AND anio_mes = ?
            """,
            (anio_mes,),
        ).fetchone()
        ajuste_row = conn.execute(
            """
            SELECT COALESCE(SUM(monto), 0) AS ajuste_total
            FROM ajustes_manuales
            WHERE estado = 'active' AND anio_mes = ?
            """,
            (anio_mes,),
        ).fetchone()

    total_bruto = round(float(total_row["total"]), 2)
    ajuste_total = round(float(ajuste_row["ajuste_total"]), 2)
    por_categoria = {row["categoria"]: round(float(row["total"]), 2) for row in cat_rows}
    return {
        "anio_mes": anio_mes,
        "total": round(total_bruto - ajuste_total, 2),
        "total_bruto": total_bruto,
        "ajuste_total": ajuste_total,
        "cantidad_ventas": int(total_row["cantidad"]),
        "por_categoria": por_categoria,
        "total_efectivo": round(float(pago_row["total_efectivo"]), 2),
        "total_tarjeta": round(float(pago_row["total_tarjeta"]), 2),
    }


def resumen_ventas_dia(fecha: str) -> dict:
    """Resumen de ventas activas para un día concreto (formato YYYY-MM-DD)."""
    inicializar_db_ventas()
    with _connect() as conn:
        total_row = conn.execute(
            """
            SELECT COALESCE(SUM(monto), 0) AS total, COUNT(*) AS cantidad
            FROM ventas
            WHERE estado = 'active' AND DATE(fecha_venta) = ?
            """,
            (fecha,),
        ).fetchone()
        cat_rows = conn.execute(
            """
            SELECT categoria, COALESCE(SUM(monto), 0) AS total
            FROM ventas
            WHERE estado = 'active' AND DATE(fecha_venta) = ?
            GROUP BY categoria
            ORDER BY categoria ASC
            """,
            (fecha,),
        ).fetchall()
    por_categoria = {row["categoria"]: round(float(row["total"]), 2) for row in cat_rows}
    return {
        "fecha": fecha,
        "total": round(float(total_row["total"]), 2),
        "cantidad_ventas": int(total_row["cantidad"]),
        "por_categoria": por_categoria,
    }


def historial_ventas(
    fecha_desde: str,
    fecha_hasta: str,
    categoria: str | None = None,
    metodo_pago: str | None = None,
) -> list[dict]:
    """Devuelve una fila por factura para el rango de fechas indicado.
    Incluye ventas activas y archivadas."""
    inicializar_db_ventas()
    params: list = [fecha_desde, fecha_hasta]
    filtros = "DATE(v.fecha_venta) BETWEEN ? AND ?"
    if categoria:
        filtros += " AND v.categoria = ?"
        params.append(categoria)
    if metodo_pago:
        filtros += " AND p.metodo_pago = ?"
        params.append(metodo_pago)
    with _connect() as conn:
        rows = conn.execute(
            f"""
            SELECT
                v.numero_factura,
                MAX(v.fecha_venta)             AS fecha_venta,
                MAX(v.cliente_nombre)          AS cliente_nombre,
                GROUP_CONCAT(DISTINCT v.categoria) AS categorias,
                ROUND(SUM(v.monto), 2)         AS monto_lineas,
                p.monto_total,
                p.metodo_pago,
                v.estado
            FROM ventas v
            LEFT JOIN pagos_factura p ON v.numero_factura = p.numero_factura
            WHERE {filtros}
            GROUP BY v.numero_factura
            ORDER BY fecha_venta DESC, v.numero_factura DESC
            """,
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def listar_ajustes_activos(anio_mes: str) -> list[dict]:
    inicializar_db_ventas()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, monto, created_at
            FROM ajustes_manuales
            WHERE estado = 'active' AND anio_mes = ?
            ORDER BY id ASC
            """,
            (anio_mes,),
        ).fetchall()
    return [dict(row) for row in rows]


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


def registrar_cierre_diario(
    cierre_id: str,
    fecha: str,
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
            INSERT INTO cierres_diarios (
                cierre_id, fecha, anio_mes, usuario, created_at,
                total, cantidad_ventas, archivo_excel
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cierre_id,
                fecha,
                anio_mes,
                (usuario or "").strip(),
                created_at,
                float(total),
                int(cantidad_ventas),
                archivo_excel,
            ),
        )
