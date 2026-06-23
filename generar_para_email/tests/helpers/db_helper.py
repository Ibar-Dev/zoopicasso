"""
Helper para acceder y validar datos en la BD SQLite
"""
import sqlite3
from pathlib import Path
from datetime import date
from typing import Optional, Dict, List


class DBHelper:
    """Helper para operaciones con BD SQLite"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
    
    def get_connection(self):
        """Obtiene conexión a BD"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_last_factura_numero(self) -> Optional[str]:
        """Obtiene el número de la última factura"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT numero_factura FROM ventas ORDER BY id DESC LIMIT 1")
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            conn.close()
    
    def get_venta_by_factura(self, numero_factura: str) -> List[Dict]:
        """Obtiene todas las líneas de venta para una factura"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, numero_factura, categoria, monto, cliente_nombre, usuario, created_at
                FROM ventas
                WHERE numero_factura = ?
                ORDER BY id ASC
                """,
                (numero_factura,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
    
    def get_pago_by_factura(self, numero_factura: str) -> Optional[Dict]:
        """Obtiene datos de pago para una factura"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, numero_factura, monto_total, monto_efectivo, monto_tarjeta, metodo_pago, created_at
                FROM pagos_factura
                WHERE numero_factura = ?
                """,
                (numero_factura,)
            )
            result = cursor.fetchone()
            return dict(result) if result else None
        finally:
            conn.close()
    
    def get_resumen_ventas_hoy(self) -> Dict:
        """Obtiene resumen de ventas de hoy"""
        conn = self.get_connection()
        today = str(date.today())
        try:
            cursor = conn.cursor()
            
            # Total y cantidad
            cursor.execute(
                "SELECT COALESCE(SUM(monto), 0) as total, COUNT(*) as cantidad FROM ventas WHERE fecha_venta = ? AND estado = 'active'",
                (today,)
            )
            result = cursor.fetchone()
            total = float(result['total']) if result else 0.0
            cantidad = int(result['cantidad']) if result else 0
            
            # Por categoría
            cursor.execute(
                """
                SELECT categoria, COALESCE(SUM(monto), 0) as total
                FROM ventas
                WHERE fecha_venta = ? AND estado = 'active'
                GROUP BY categoria
                ORDER BY categoria
                """,
                (today,)
            )
            por_categoria = {row['categoria']: float(row['total']) for row in cursor.fetchall()}
            
            return {
                'total': round(total, 2),
                'cantidad': cantidad,
                'por_categoria': por_categoria
            }
        finally:
            conn.close()
    
    def get_total_ventas(self, numero_factura: str) -> float:
        """Calcula el total de una factura sumando las líneas"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COALESCE(SUM(monto), 0) as total FROM ventas WHERE numero_factura = ?",
                (numero_factura,)
            )
            result = cursor.fetchone()
            return round(float(result['total']), 2) if result else 0.0
        finally:
            conn.close()
    
    def limpiar_facturas_hoy(self):
        """Limpia todas las facturas de hoy (para tests)"""
        conn = self.get_connection()
        today = str(date.today())
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM ventas WHERE fecha_venta = ?", (today,))
            cursor.execute("DELETE FROM pagos_factura WHERE fecha_venta = ?", (today,))
            conn.commit()
        finally:
            conn.close()
    
    def limpiar_factura(self, numero_factura: str):
        """Limpia una factura específica"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM ventas WHERE numero_factura = ?", (numero_factura,))
            cursor.execute("DELETE FROM pagos_factura WHERE numero_factura = ?", (numero_factura,))
            conn.commit()
        finally:
            conn.close()
