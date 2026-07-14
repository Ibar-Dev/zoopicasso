from __future__ import annotations

import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from src.factura_model import Factura, PagoInfo

if TYPE_CHECKING:
    from core.domain import TransaccionComercial

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


@contextmanager
def _connect_exclusive():
    """Conexión con transacción EXCLUSIVE para operaciones que requieren atomicidad.
    Usa isolation_level=None para control manual de transacciones.
    """
    RUTA_DB_VENTAS.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(RUTA_DB_VENTAS, isolation_level=None, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("BEGIN EXCLUSIVE")
        yield conn
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def inicializar_db_ventas() -> None:
    with _connect() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
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
        # Tablas de cierres eliminadas en favor de auditoría Excel en tiempo real
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_ventas_mes
            ON ventas (anio_mes)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_pagos_mes
            ON pagos_factura (anio_mes)
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
            CREATE INDEX IF NOT EXISTS idx_ajustes_mes
            ON ajustes_manuales (anio_mes)
            """
        )
        # Migración: agregar columna tipo_cierre si no existe (mantenido por compatibilidad legacy)
        try:
            conn.execute("ALTER TABLE cierres_diarios ADD COLUMN tipo_cierre TEXT DEFAULT 'full_day'")
        except sqlite3.OperationalError:
            pass

        # Contador atómico (reemplaza contador_facturas.json y contador.json)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS contadores (
                nombre TEXT PRIMARY KEY,
                valor INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        # Tabla principal de transacciones para el patrón Outbox
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transacciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_transaccion TEXT UNIQUE NOT NULL,
                fecha_hora TEXT NOT NULL,
                anio_mes TEXT NOT NULL,
                cliente_nombre TEXT NOT NULL DEFAULT '',
                cliente_nif TEXT NOT NULL DEFAULT '',
                total REAL NOT NULL,
                metodo_pago TEXT NOT NULL,
                monto_efectivo REAL NOT NULL DEFAULT 0,
                monto_tarjeta REAL NOT NULL DEFAULT 0,
                efectivo_entregado REAL NOT NULL DEFAULT 0,
                cambio REAL NOT NULL DEFAULT 0,
                usuario TEXT NOT NULL DEFAULT '',
                items_json TEXT NOT NULL DEFAULT '[]',
                excel_pendiente INTEGER NOT NULL DEFAULT 1,
                print_pendiente INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_transacciones_pendientes
            ON transacciones (excel_pendiente, print_pendiente)
            WHERE excel_pendiente = 1 OR print_pendiente = 1
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
            WHERE anio_mes = ?
            """,
            (anio_mes,),
        ).fetchone()
        cat_rows = conn.execute(
            """
            SELECT categoria, COALESCE(SUM(monto), 0) AS total
            FROM ventas
            WHERE anio_mes = ?
            GROUP BY categoria
            ORDER BY categoria ASC
            """,
            (anio_mes,),
        ).fetchall()
        pago_row = conn.execute(
            """
            SELECT COALESCE(SUM(monto_efectivo), 0) AS total_efectivo, COALESCE(SUM(monto_tarjeta), 0) AS total_tarjeta
            FROM pagos_factura
            WHERE anio_mes = ?
            """,
            (anio_mes,),
        ).fetchone()
        ajuste_row = conn.execute(
            """
            SELECT COALESCE(SUM(monto), 0) AS ajuste_total
            FROM ajustes_manuales
            WHERE anio_mes = ?
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
    """Resumen de ventas para un día concreto (formato YYYY-MM-DD)."""
    inicializar_db_ventas()
    with _connect() as conn:
        total_row = conn.execute(
            """
            SELECT COALESCE(SUM(monto), 0) AS total, COUNT(*) AS cantidad
            FROM ventas
            WHERE DATE(fecha_venta) = ?
            """,
            (fecha,),
        ).fetchone()
        cat_rows = conn.execute(
            """
            SELECT categoria, COALESCE(SUM(monto), 0) AS total
            FROM ventas
            WHERE DATE(fecha_venta) = ?
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


def cerrar_mes_atomico(
    anio_mes: str,
    cierre_id: str,
    archived_at: str,
    usuario: str,
    total: float,
    archivo_excel: str,
) -> int:
    """Archiva ventas y ajustes del mes y registra el cierre en una sola transacción."""
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
        actualizadas = int(cur.rowcount)
        conn.execute(
            """
            UPDATE ajustes_manuales
            SET estado = 'archived', archived_at = ?, cierre_id = ?
            WHERE estado = 'active' AND anio_mes = ?
            """,
            (archived_at, cierre_id, anio_mes),
        )
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
                archived_at,
                float(total),
                actualizadas,
                archivo_excel,
            ),
        )
    return actualizadas


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


def resumen_ventas_mañana(fecha: str) -> dict:
    """Resumen de ventas en MAÑANA (06:00-14:00) para una fecha (YYYY-MM-DD).
    
    NOTA: Las horas se convierten a hora local usando datetime(..., 'localtime')
    ya que created_at se almacena en UTC.
    """
    inicializar_db_ventas()
    with _connect() as conn:
        total_row = conn.execute(
            """
            SELECT COALESCE(SUM(monto), 0) AS total, COUNT(*) AS cantidad
            FROM ventas
            WHERE DATE(fecha_venta) = ?
              AND CAST(strftime('%H', datetime(created_at, 'localtime')) AS INTEGER) >= 6
              AND CAST(strftime('%H', datetime(created_at, 'localtime')) AS INTEGER) < 14
            """,
            (fecha,),
        ).fetchone()
        cat_rows = conn.execute(
            """
            SELECT categoria, COALESCE(SUM(monto), 0) AS total
            FROM ventas
            WHERE DATE(fecha_venta) = ?
              AND CAST(strftime('%H', datetime(created_at, 'localtime')) AS INTEGER) >= 6
              AND CAST(strftime('%H', datetime(created_at, 'localtime')) AS INTEGER) < 14
            GROUP BY categoria
            ORDER BY categoria ASC
            """,
            (fecha,),
        ).fetchall()
    por_categoria = {row["categoria"]: round(float(row["total"]), 2) for row in cat_rows}
    return {
        "fecha": fecha,
        "periodo": "mañana",
        "total": round(float(total_row["total"]), 2),
        "cantidad_ventas": int(total_row["cantidad"]),
        "por_categoria": por_categoria,
    }


def resumen_ventas_tarde(fecha: str) -> dict:
    """Resumen de ventas en TARDE (14:00-22:00) para una fecha (YYYY-MM-DD).
    
    NOTA: Las horas se convierten a hora local usando datetime(..., 'localtime')
    ya que created_at se almacena en UTC.
    """
    inicializar_db_ventas()
    with _connect() as conn:
        total_row = conn.execute(
            """
            SELECT COALESCE(SUM(monto), 0) AS total, COUNT(*) AS cantidad
            FROM ventas
            WHERE DATE(fecha_venta) = ?
              AND CAST(strftime('%H', datetime(created_at, 'localtime')) AS INTEGER) >= 14
              AND CAST(strftime('%H', datetime(created_at, 'localtime')) AS INTEGER) < 22
            """,
            (fecha,),
        ).fetchone()
        cat_rows = conn.execute(
            """
            SELECT categoria, COALESCE(SUM(monto), 0) AS total
            FROM ventas
            WHERE DATE(fecha_venta) = ?
              AND CAST(strftime('%H', datetime(created_at, 'localtime')) AS INTEGER) >= 14
              AND CAST(strftime('%H', datetime(created_at, 'localtime')) AS INTEGER) < 22
            GROUP BY categoria
            ORDER BY categoria ASC
            """,
            (fecha,),
        ).fetchall()
    por_categoria = {row["categoria"]: round(float(row["total"]), 2) for row in cat_rows}
    return {
        "fecha": fecha,
        "periodo": "tarde",
        "total": round(float(total_row["total"]), 2),
        "cantidad_ventas": int(total_row["cantidad"]),
        "por_categoria": por_categoria,
    }



def obtener_cierres_hoy(fecha: str) -> dict:
    """
    Obtiene los cierres registrados para un día específico.
    
    Retorna diccionario con:
    {
        'fecha': 'YYYY-MM-DD',
        'hizo_mañana': bool,
        'hizo_tarde': bool,
        'hizo_dia_completo': bool,
        'cierres': [lista de registros con tipo_cierre]
    }
    """
    inicializar_db_ventas()
    with _connect() as conn:
        cierres = conn.execute(
            """
            SELECT cierre_id, tipo_cierre, created_at, total, cantidad_ventas
            FROM cierres_diarios
            WHERE fecha = ?
            ORDER BY created_at ASC
            """,
            (fecha,),
        ).fetchall()
    
    hizo_mañana = any(row["tipo_cierre"] == "morning" for row in cierres)
    hizo_tarde = any(row["tipo_cierre"] == "afternoon" for row in cierres)
    hizo_dia = any(row["tipo_cierre"] == "full_day" for row in cierres)
    
    return {
        "fecha": fecha,
        "hizo_mañana": hizo_mañana,
        "hizo_tarde": hizo_tarde,
        "hizo_dia_completo": hizo_dia,
        "cierres": [dict(row) for row in cierres],
    }


def puede_hacer_cierre(tipo_cierre: str, fecha: str) -> tuple[bool, str]:
    """
    Valida si se puede hacer un cierre del tipo especificado para la fecha dada.
    
    Retorna (puede_hacer: bool, motivo: str)
    
    Lógica:
    - morning: siempre se puede hacer (si no fue hecho hoy)
    - afternoon: solo si morning fue hecho
    - full_day: solo si morning Y afternoon fueron hechos
    """
    estado = obtener_cierres_hoy(fecha)
    
    if tipo_cierre == "morning":
        if estado["hizo_mañana"]:
            return False, "Ya completaste el cierre de mañana hoy"
        return True, ""
    
    elif tipo_cierre == "afternoon":
        if not estado["hizo_mañana"]:
            return False, "Primero debes hacer el cierre de mañana"
        if estado["hizo_tarde"]:
            return False, "Ya completaste el cierre de tarde hoy"
        return True, ""
    
    elif tipo_cierre == "full_day":
        if not estado["hizo_mañana"]:
            return False, "Primero debes hacer el cierre de mañana"
        if not estado["hizo_tarde"]:
            return False, "Primero debes hacer el cierre de tarde"
        if estado["hizo_dia_completo"]:
            return False, "Ya completaste el cierre del día completo hoy"
        return True, ""
    
    return False, f"Tipo de cierre inválido: {tipo_cierre}"


def registrar_cierre_diario(
    cierre_id: str,
    fecha: str,
    anio_mes: str,
    usuario: str,
    created_at: str,
    total: float,
    cantidad_ventas: int,
    archivo_excel: str,
    tipo_cierre: str = "full_day",
) -> None:
    inicializar_db_ventas()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO cierres_diarios (
                cierre_id, fecha, anio_mes, usuario, created_at,
                total, cantidad_ventas, archivo_excel, tipo_cierre
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                tipo_cierre,
            ),
        )


# ════════════════════════════════════════════════════════════════════════════════
# DOMINIO UNIFICADO — Registro atómico y patrón Outbox
# ════════════════════════════════════════════════════════════════════════════════

def registrar_transaccion(t: "TransaccionComercial", usuario: str) -> str:
    """
    Registra una venta de forma completamente atómica usando BEGIN EXCLUSIVE.

    Una sola transacción SQLite:
      1. Incrementa el contador de transacciones en la tabla 'contadores'.
      2. Inserta la fila en 'transacciones' con excel_pendiente=1, print_pendiente=1.
      3. Inserta las líneas en 'ventas' (compatibilidad con resúmenes y cierres).
      4. Inserta el pago en 'pagos_factura'.

    Si cualquier paso falla, el ROLLBACK deja la DB sin cambios y el contador
    no avanza — ningún número se "quema".

    Retorna:
        id_transaccion asignado, formato "YYYY-NNN".
    """
    inicializar_db_ventas()
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    fecha_str = t.fecha_hora.date().isoformat()
    anio_mes = t.anio_mes
    year = t.fecha_hora.year
    items_json = t.items_as_json()

    with _connect_exclusive() as conn:
        # ── Contador atómico ──────────────────────────────────────────────────
        conn.execute(
            "INSERT OR IGNORE INTO contadores (nombre, valor) VALUES ('transacciones', 0)"
        )
        conn.execute(
            "UPDATE contadores SET valor = valor + 1 WHERE nombre = 'transacciones'"
        )
        numero = int(
            conn.execute(
                "SELECT valor FROM contadores WHERE nombre = 'transacciones'"
            ).fetchone()["valor"]
        )
        id_transaccion = f"{year}-{numero:03d}"

        # ── Transacción principal (Outbox) ────────────────────────────────────
        conn.execute(
            """
            INSERT INTO transacciones (
                id_transaccion, fecha_hora, anio_mes, cliente_nombre, cliente_nif,
                total, metodo_pago, monto_efectivo, monto_tarjeta, efectivo_entregado,
                cambio, usuario, items_json, excel_pendiente, print_pendiente, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?)
            """,
            (
                id_transaccion,
                t.fecha_hora.isoformat(),
                anio_mes,
                (t.cliente_nombre or "").strip(),
                (t.cliente_nif or "").strip(),
                float(t.total),
                t.metodo_pago,
                float(t.monto_efectivo),
                float(t.monto_tarjeta),
                float(t.efectivo_entregado),
                float(t.cambio),
                (usuario or "").strip(),
                items_json,
                created_at,
            ),
        )

        # ── Líneas de ventas (para resúmenes y cierres existentes) ────────────
        filas_ventas = [
            (
                id_transaccion,
                fecha_str,
                anio_mes,
                (item.categoria or "sin_categoria").strip() or "sin_categoria",
                float(item.total),
                (t.cliente_nombre or "").strip(),
                (usuario or "").strip(),
                created_at,
            )
            for item in t.items
        ]
        conn.executemany(
            """
            INSERT INTO ventas (
                numero_factura, fecha_venta, anio_mes, categoria, monto,
                cliente_nombre, usuario, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            filas_ventas,
        )

        # ── Pago ──────────────────────────────────────────────────────────────
        conn.execute(
            """
            INSERT INTO pagos_factura (
                numero_factura, fecha_venta, anio_mes, monto_total, monto_efectivo,
                monto_tarjeta, metodo_pago, usuario, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                id_transaccion,
                fecha_str,
                anio_mes,
                float(t.total),
                float(t.monto_efectivo),
                float(t.monto_tarjeta),
                t.metodo_pago,
                (usuario or "").strip(),
                created_at,
            ),
        )

    logger.info(
        "Transacción %s registrada atómicamente. Líneas: %d, Total: %.2f, Método: %s",
        id_transaccion,
        len(t.items),
        t.total,
        t.metodo_pago,
    )
    return id_transaccion


def recuperar_pendientes() -> list[dict]:
    """
    Patrón Outbox: retorna transacciones cuyos sinks no se completaron.

    Se llama al arrancar la app para reintentar sinks fallidos.
    Cada fila contiene todos los campos necesarios para reconstruir
    una TransaccionComercial mediante TransaccionComercial.from_db_row().
    """
    inicializar_db_ventas()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id_transaccion, fecha_hora, anio_mes, cliente_nombre, cliente_nif,
                   total, metodo_pago, monto_efectivo, monto_tarjeta, efectivo_entregado,
                   cambio, usuario, items_json, excel_pendiente, print_pendiente
            FROM transacciones
            WHERE excel_pendiente = 1 OR print_pendiente = 1
            ORDER BY created_at ASC
            """,
        ).fetchall()
    return [dict(row) for row in rows]


def marcar_excel_completado(id_transaccion: str) -> None:
    """Marca el sink de Excel como completado para la transacción dada."""
    with _connect() as conn:
        conn.execute(
            "UPDATE transacciones SET excel_pendiente = 0 WHERE id_transaccion = ?",
            (id_transaccion,),
        )
    logger.debug("excel_pendiente=0 para transacción %s", id_transaccion)


def marcar_print_completado(id_transaccion: str) -> None:
    """Marca el sink de impresión como completado para la transacción dada."""
    with _connect() as conn:
        conn.execute(
            "UPDATE transacciones SET print_pendiente = 0 WHERE id_transaccion = ?",
            (id_transaccion,),
        )
    logger.debug("print_pendiente=0 para transacción %s", id_transaccion)
