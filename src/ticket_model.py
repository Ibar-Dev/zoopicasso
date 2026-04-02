# ticket_model.py
# Modelo de datos para el ticket de Zoo Picasso.
# Define las estructuras LineaTicket y Ticket usando dataclasses.

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

_logger = logging.getLogger(__name__)

# Datos constantes del negocio.
# Centralizar aquí evita repetición y facilita futuros cambios.
NOMBRE_NEGOCIO = "Zoo Picasso"
NIF = os.getenv("ZOO_PICASSO_NIF", "XXXXXXXXX")

if "X" in NIF:
    _logger.warning(
        "NIF no configurado. Define la variable de entorno ZOO_PICASSO_NIF antes de usar en producción."
    )


@dataclass
class LineaTicket:
    """
    Representa una línea individual dentro del ticket.
    El total se calcula automáticamente al instanciar.
    """
    nombre: str          # Nombre del servicio o producto
    cantidad: int        # Número de unidades
    precio_unitario: float  # Precio por unidad (IVA incluido)

    # total se calcula al crear la línea, no se pasa manualmente
    total: float = field(init=False)

    def __post_init__(self):
        # Validaciones básicas para evitar datos incoherentes
        if self.cantidad <= 0:
            raise ValueError(f"La cantidad debe ser mayor que 0. Recibido: {self.cantidad}")
        if self.precio_unitario < 0:
            raise ValueError(f"El precio unitario no puede ser negativo. Recibido: {self.precio_unitario}")

        # Redondeamos a 2 decimales para evitar errores de punto flotante
        self.total = round(self.cantidad * self.precio_unitario, 2)


@dataclass
class Ticket:
    """
    Representa un ticket completo con su cabecera y sus líneas.
    El total general se calcula dinámicamente a partir de las líneas.
    """
    numero: int                  # Número correlativo persistido
    lineas: List[LineaTicket]    # Lista de líneas del ticket
    fecha_hora: datetime = field(default_factory=datetime.now)

    # Campos constantes del negocio, accesibles desde el ticket
    nombre_negocio: str = field(default=NOMBRE_NEGOCIO, init=False)
    nif: str = field(default=NIF, init=False)

    def __post_init__(self):
        if not self.lineas:
            raise ValueError("Un ticket debe tener al menos una línea.")

    @property
    def total(self) -> float:
        """Suma de los totales de todas las líneas."""
        return round(sum(linea.total for linea in self.lineas), 2)

    @property
    def fecha_formateada(self) -> str:
        """Fecha y hora en formato legible para imprimir y guardar."""
        return self.fecha_hora.strftime("%d/%m/%Y %H:%M:%S")