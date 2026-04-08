# factura_model.py
# Modelo de datos para las facturas de Gisselle Marin Tabares.
# Define LineaFactura y Factura. Los precios son sin IVA; el IVA se desglosa en Factura.

from dataclasses import dataclass, field
from datetime import date
from typing import List


# Datos del emisor. Centralizar aquí evita repetición en writer y UI.
NOMBRE_EMISOR = "Gisselle Marin Tabares"
NIF_EMISOR = "Y3806548Q"
DIRECCION_EMISOR = "Calle de Pablo Picasso 59"
TELEFONO_EMISOR = "604 300 492"
EMAIL_EMISOR = "zoopicasso07@gmail.com"

IVA_PCT = 21  # Porcentaje de IVA aplicado a todas las facturas


@dataclass
class LineaFactura:
    """
    Una línea de la factura. El precio unitario es sin IVA.
    El total se calcula automáticamente.
    """
    concepto: str
    cantidad: int
    precio_unitario: float  # Sin IVA

    total: float = field(init=False)

    def __post_init__(self):
        if self.cantidad <= 0:
            raise ValueError(f"La cantidad debe ser mayor que 0. Recibido: {self.cantidad}")
        if self.precio_unitario < 0:
            raise ValueError(f"El precio unitario no puede ser negativo. Recibido: {self.precio_unitario}")
        self.total = round(self.cantidad * self.precio_unitario, 2)


@dataclass
class Factura:
    """
    Factura completa con datos del cliente, líneas y desglose de IVA.
    """
    numero: int
    fecha: date
    cliente_nombre: str
    cliente_nif: str
    lineas: List[LineaFactura]

    def __post_init__(self):
        if not self.lineas:
            raise ValueError("La factura debe tener al menos una línea.")

    @property
    def base_imponible(self) -> float:
        """Suma de totales de todas las líneas (sin IVA)."""
        return round(sum(l.total for l in self.lineas), 2)

    @property
    def cuota_iva(self) -> float:
        """Importe del IVA sobre la base imponible."""
        return round(self.base_imponible * IVA_PCT / 100, 2)

    @property
    def total_con_iva(self) -> float:
        """Total final a pagar."""
        return round(self.base_imponible + self.cuota_iva, 2)

    @property
    def numero_formateado(self) -> str:
        """Número de factura en formato YYYY-NNN."""
        return f"{self.fecha.year}-{self.numero:03d}"

    @property
    def fecha_formateada(self) -> str:
        return self.fecha.strftime("%d/%m/%Y")
