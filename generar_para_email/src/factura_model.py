# factura_model.py
# Modelo de datos para las facturas de Gisselle Marin Tabares.
# Define LineaFactura y Factura. Los precios se consideran finales (IVA incluido).

from dataclasses import dataclass, field
from datetime import date
from typing import List


# Datos del emisor. Centralizar aquí evita repetición en writer y UI.
NOMBRE_EMISOR = "Gisselle Marin Tabares"
NIF_EMISOR = "Y3806548Q"
DIRECCION_EMISOR = "Calle de Pablo Picasso 59"
TELEFONO_EMISOR = "642 342 110"
EMAIL_EMISOR = "zoopicasso07@gmail.com"

IVA_PCT = 21  # Referencia informativa para mostrar "IVA incluido"


@dataclass
class LineaFactura:
    """
    Una línea de la factura. El precio unitario es final (IVA incluido).
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
    Factura completa con datos del cliente y líneas con precios finales.
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
        """Suma de totales de todas las líneas (importe final)."""
        return round(sum(l.total for l in self.lineas), 2)

    @property
    def cuota_iva(self) -> float:
        """Con precios finales, no se suma IVA adicional al total."""
        return 0.0

    @property
    def total_con_iva(self) -> float:
        """Total final a pagar (ya incluye IVA en los precios unitarios)."""
        return self.base_imponible

    @property
    def numero_formateado(self) -> str:
        """Número de factura en formato YYYY-NNN."""
        return f"{self.fecha.year}-{self.numero:03d}"

    @property
    def fecha_formateada(self) -> str:
        return self.fecha.strftime("%d/%m/%Y")
