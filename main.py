# main.py
# Interfaz gráfica principal de Zoo Picasso usando Tkinter puro.
# Gestiona la generación, impresión y registro de tickets de compra.

import logging
import tkinter as tk
from tkinter import messagebox
from typing import List

from src.counter import siguiente_numero
from src.excel_writer import guardar_ticket
from src.printer import imprimir_ticket
from src.ticket_model import LineaTicket, Ticket

# Configuración de logging visible en consola durante uso y depuración
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class FilaServicio:
    """
    Representa una fila de entrada de datos en la UI.
    Encapsula los 4 widgets (Entry) de una línea de servicio.
    """

    def __init__(self, frame: tk.Frame, fila: int, callback_total: callable):
        """
        Args:
            frame: Contenedor padre donde se insertan los widgets.
            fila: Índice de fila en el grid.
            callback_total: Función a llamar cuando cambia algún valor,
                            para recalcular el total general.
        """
        self.callback_total = callback_total

        # Variables observables de Tkinter — se sincronizan automáticamente con los Entry
        self.nombre_var = tk.StringVar()
        self.cantidad_var = tk.StringVar(value="1")
        self.precio_var = tk.StringVar(value="0.00")
        self.total_var = tk.StringVar(value="0.00")

        # Registrar el callback en cantidad y precio para recalcular al cambiar
        self.cantidad_var.trace_add("write", self._recalcular)
        self.precio_var.trace_add("write", self._recalcular)

        # --- Widgets ---
        self.entry_nombre = tk.Entry(frame, textvariable=self.nombre_var, width=20)
        self.entry_cantidad = tk.Entry(frame, textvariable=self.cantidad_var, width=5)
        self.entry_precio = tk.Entry(frame, textvariable=self.precio_var, width=8)
        # Total: solo lectura, calculado automáticamente
        self.entry_total = tk.Entry(
            frame, textvariable=self.total_var, width=8,
            state="readonly", readonlybackground="#f0f0f0"
        )

        # Posicionar en el grid del frame contenedor
        self.entry_nombre.grid(row=fila, column=0, padx=4, pady=2)
        self.entry_cantidad.grid(row=fila, column=1, padx=4, pady=2)
        self.entry_precio.grid(row=fila, column=2, padx=4, pady=2)
        self.entry_total.grid(row=fila, column=3, padx=4, pady=2)

    def _recalcular(self, *_):
        """
        Recalcula el total de la línea y notifica al callback general.
        Se ignoran errores de conversión (el usuario puede estar escribiendo).
        """
        try:
            cantidad = int(self.cantidad_var.get())
            precio = float(self.precio_var.get())
            total = round(cantidad * precio, 2)
            self.total_var.set(f"{total:.2f}")
        except ValueError:
            self.total_var.set("0.00")
        finally:
            self.callback_total()

    def destruir(self):
        """Elimina todos los widgets de esta fila del grid."""
        self.entry_nombre.destroy()
        self.entry_cantidad.destroy()
        self.entry_precio.destroy()
        self.entry_total.destroy()

    def a_linea_ticket(self) -> LineaTicket:
        """
        Convierte los valores de la fila en un objeto LineaTicket.

        Raises:
            ValueError: Si los datos son inválidos o incompletos.
        """
        nombre = self.nombre_var.get().strip()
        if not nombre:
            raise ValueError("El nombre del servicio no puede estar vacío.")
        cantidad = int(self.cantidad_var.get())
        precio = float(self.precio_var.get())
        return LineaTicket(nombre=nombre, cantidad=cantidad, precio_unitario=precio)


class AppZooPicasso:
    """Aplicación principal de generación de tickets."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Zoo Picasso — Tickets")
        self.root.resizable(False, False)

        self.filas: List[FilaServicio] = []
        self.numero_ticket = siguiente_numero()

        self._construir_ui()
        self._agregar_fila()  # Arranca con una línea vacía

    def _construir_ui(self):
        """Construye todos los widgets estáticos de la interfaz."""
        padding = {"padx": 10, "pady": 6}

        # --- Cabecera ---
        tk.Label(
            self.root, text="ZOO PICASSO",
            font=("Arial", 16, "bold")
        ).pack(**padding)

        self.lbl_ticket = tk.Label(
            self.root,
            text=self._texto_cabecera(),
            font=("Arial", 10)
        )
        self.lbl_ticket.pack()

        tk.Frame(self.root, height=1, bg="gray").pack(fill="x", padx=10, pady=4)

        # --- Cabecera de columnas ---
        frame_cols = tk.Frame(self.root)
        frame_cols.pack(padx=10)
        for col, (texto, ancho) in enumerate([
            ("Servicio", 20), ("Cant.", 5), ("P. Unit.", 8), ("Total", 8)
        ]):
            tk.Label(frame_cols, text=texto, width=ancho, font=("Arial", 9, "bold")).grid(
                row=0, column=col, padx=4
            )

        # --- Contenedor de filas dinámicas ---
        self.frame_filas = tk.Frame(self.root)
        self.frame_filas.pack(padx=10)

        # --- Botones añadir / quitar ---
        frame_botones_filas = tk.Frame(self.root)
        frame_botones_filas.pack(pady=4)
        tk.Button(
            frame_botones_filas, text="+ Añadir línea",
            command=self._agregar_fila, width=14
        ).grid(row=0, column=0, padx=6)
        tk.Button(
            frame_botones_filas, text="- Quitar línea",
            command=self._quitar_fila, width=14
        ).grid(row=0, column=1, padx=6)

        tk.Frame(self.root, height=1, bg="gray").pack(fill="x", padx=10, pady=4)

        # --- Total general ---
        frame_total = tk.Frame(self.root)
        frame_total.pack(padx=10, pady=2, anchor="e")
        tk.Label(frame_total, text="TOTAL:", font=("Arial", 12, "bold")).grid(row=0, column=0)
        self.lbl_total = tk.Label(
            frame_total, text="0.00 EUR",
            font=("Arial", 12, "bold"), fg="#1a7a1a"
        )
        self.lbl_total.grid(row=0, column=1, padx=8)

        tk.Frame(self.root, height=1, bg="gray").pack(fill="x", padx=10, pady=4)

        # --- Botón imprimir ---
        tk.Button(
            self.root, text="IMPRIMIR TICKET",
            font=("Arial", 12, "bold"),
            bg="#1a7a1a", fg="white",
            activebackground="#145e14",
            command=self._imprimir, height=2, width=24
        ).pack(pady=10)

    def _texto_cabecera(self) -> str:
        """Genera el texto de cabecera con número de ticket actualizado."""
        from datetime import datetime
        fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
        return f"Ticket #{self.numero_ticket:04d}  —  {fecha}"

    def _agregar_fila(self):
        """Añade una nueva fila de servicio al formulario."""
        indice = len(self.filas)
        fila = FilaServicio(self.frame_filas, indice, self._actualizar_total)
        self.filas.append(fila)
        logger.info(f"Fila añadida. Total filas: {len(self.filas)}")

    def _quitar_fila(self):
        """Elimina la última fila del formulario. Mínimo 1 fila."""
        if len(self.filas) <= 1:
            messagebox.showwarning("Aviso", "El ticket debe tener al menos una línea.")
            return
        fila = self.filas.pop()
        fila.destruir()
        self._actualizar_total()
        logger.info(f"Fila eliminada. Total filas: {len(self.filas)}")

    def _actualizar_total(self):
        """Recalcula y muestra el total general sumando todas las líneas."""
        try:
            total = sum(float(f.total_var.get()) for f in self.filas)
            self.lbl_total.config(text=f"{total:.2f} EUR")
        except ValueError:
            self.lbl_total.config(text="0.00 EUR")

    def _imprimir(self):
        """
        Valida los datos, construye el ticket, lo guarda en Excel y lo imprime.
        Si algo falla, muestra un mensaje de error sin perder los datos del formulario.
        """
        # Validar y construir líneas
        try:
            lineas = [f.a_linea_ticket() for f in self.filas]
        except ValueError as e:
            messagebox.showerror("Error en los datos", str(e))
            return

        # Construir ticket
        ticket = Ticket(numero=self.numero_ticket, lineas=lineas)
        logger.info(f"Ticket #{ticket.numero} listo para procesar. Total: {ticket.total:.2f} EUR")

        # Guardar en Excel
        try:
            guardar_ticket(ticket)
        except Exception as e:
            messagebox.showerror("Error al guardar", f"No se pudo guardar en Excel:\n{e}")
            logger.error(f"Error al guardar ticket #{ticket.numero} en Excel: {e}")
            return

        # Imprimir
        try:
            imprimir_ticket(ticket)
        except ConnectionError as e:
            messagebox.showerror(
                "Error de impresora",
                f"Ticket #{ticket.numero:04d} guardado en Excel, pero no se pudo imprimir:\n{e}"
            )
            logger.error(f"Error de conexión con impresora: {e}")
            return
        except Exception as e:
            messagebox.showerror(
                "Error de impresión",
                f"Ticket #{ticket.numero:04d} guardado en Excel, pero error inesperado al imprimir:\n{e}"
            )
            logger.error(f"Error inesperado al imprimir ticket #{ticket.numero}: {e}")
            return

        messagebox.showinfo("Éxito", f"Ticket #{ticket.numero:04d} impreso y guardado correctamente.")

        # Resetear formulario para el siguiente ticket
        self._resetear()

    def _resetear(self):
        """Limpia el formulario y prepara el siguiente número de ticket."""
        for fila in self.filas:
            fila.destruir()
        self.filas.clear()

        self.numero_ticket = siguiente_numero()
        self.lbl_ticket.config(text=self._texto_cabecera())
        self._agregar_fila()
        self._actualizar_total()
        logger.info(f"Formulario reseteado. Siguiente ticket: #{self.numero_ticket:04d}")


if __name__ == "__main__":
    root = tk.Tk()
    app = AppZooPicasso(root)
    root.mainloop()