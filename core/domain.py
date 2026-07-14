# core/domain.py
# Modelo de dominio unificado para Zoo Picasso.
#
# DISEÑO:
#   Una sola TransaccionComercial reemplaza Factura + Ticket como entidades
#   de dominio separadas. Los módulos de infraestructura (factura_writer,
#   excel_writer, printer) construyen sus propias vistas a partir de este modelo.
#
# NOTA sobre id_transaccion:
#   El campo se deja vacío al crear la instancia. Se asigna DESPUÉS del
#   commit atómico en SQLite (ventas_store.registrar_transaccion). Esto
#   garantiza que ningún número se "quema" si la validación o el commit fallan.

from __future__ import annotations

import json
from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel, Field


class VentaItem(BaseModel):
    """Artículo único dentro de una transacción comercial."""

    descripcion: str = Field(min_length=1)
    cantidad: int = Field(gt=0)
    precio_unitario: float = Field(ge=0)
    categoria: str = ""

    @property
    def total(self) -> float:
        return round(self.cantidad * self.precio_unitario, 2)


class TransaccionComercial(BaseModel):
    """
    Entidad de dominio central. Representa una venta completa con todos los
    datos necesarios para los dos sinks (impresora térmica y Excel de auditoría).

    FLUJO DE VIDA:
      1. Creada sin id_transaccion en el endpoint.
      2. ventas_store.registrar_transaccion() le asigna el id_transaccion
         de forma atómica junto con el incremento del contador en SQLite.
      3. Se despacha a core.sinks.encolar_impresion() y core.sinks.anexar_a_excel().
    """

    id_transaccion: str = ""
    fecha_hora: datetime = Field(default_factory=datetime.now)
    items: List[VentaItem] = Field(min_length=1)
    total: float
    cliente_nombre: str = ""
    cliente_nif: str = ""
    metodo_pago: Literal["efectivo", "tarjeta", "mixto"]
    monto_efectivo: float = 0.0
    monto_tarjeta: float = 0.0
    efectivo_entregado: float = 0.0
    cambio: float = 0.0
    usuario: str = ""

    @property
    def anio_mes(self) -> str:
        return self.fecha_hora.strftime("%Y-%m")

    @property
    def numero_int(self) -> int:
        """Parte numérica del id_transaccion (YYYY-NNN → NNN)."""
        if self.id_transaccion and "-" in self.id_transaccion:
            return int(self.id_transaccion.split("-", 1)[1])
        return 0

    def items_as_json(self) -> str:
        """Serializa los items para persistencia en SQLite."""
        return json.dumps(
            [item.model_dump() for item in self.items],
            ensure_ascii=False,
        )

    @classmethod
    def from_db_row(cls, row: dict) -> "TransaccionComercial":
        """Reconstruye una TransaccionComercial desde una fila de la tabla transacciones."""
        items_raw = json.loads(row.get("items_json") or "[]")
        items = [VentaItem(**i) for i in items_raw]
        return cls(
            id_transaccion=row["id_transaccion"],
            fecha_hora=datetime.fromisoformat(row["fecha_hora"]),
            items=items,
            total=float(row["total"]),
            cliente_nombre=row.get("cliente_nombre") or "",
            cliente_nif=row.get("cliente_nif") or "",
            metodo_pago=row["metodo_pago"],
            monto_efectivo=float(row.get("monto_efectivo") or 0),
            monto_tarjeta=float(row.get("monto_tarjeta") or 0),
            efectivo_entregado=float(row.get("efectivo_entregado") or 0),
            cambio=float(row.get("cambio") or 0),
            usuario=row.get("usuario") or "",
        )
