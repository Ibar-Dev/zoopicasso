import logging
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timezone

from src.ventas_store import RUTA_DB_VENTAS, inicializar_db_ventas

logger = logging.getLogger(__name__)


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


def registrar_ventas_ticket(
    numero_ticket: int,
    filas: list[tuple[str, float]],
    usuario: str = "",
) -> None:
    """Registra las lineas de un ticket en ventas.db para el control de ventas.

    filas: lista de tuplas (categoria, monto).
    El numero se guarda como T-#### para distinguirlo de las facturas.
    """
    inicializar_db_ventas()
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    fecha = date.today()
    anio_mes = fecha.strftime("%Y-%m")
    numero_factura = f"T-{numero_ticket:04d}"
    registros = [
        (
            numero_factura,
            fecha.isoformat(),
            anio_mes,
            (categoria or "sin_categoria").strip() or "sin_categoria",
            round(float(monto), 2),
            "",
            (usuario or "").strip(),
            created_at,
        )
        for categoria, monto in filas
    ]
    if not registros:
        return
    with _connect() as conn:
        conn.executemany(
            """
            INSERT INTO ventas (
                numero_factura, fecha_venta, anio_mes, categoria, monto,
                cliente_nombre, usuario, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            registros,
        )
    logger.info(
        "Ventas de ticket T-%04d registradas (%d lineas)",
        numero_ticket,
        len(registros),
    )