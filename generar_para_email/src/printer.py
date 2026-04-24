import os
import sys
from datetime import datetime

from src.factura_model import EMAIL_EMISOR
from src.factura_model import TELEFONO_EMISOR
from src.factura_model import Factura


def _normalizar_importe(valor: float) -> str:
    return f"{valor:.2f} EUR"


def _comprimir_texto(texto: str, max_chars: int) -> str:
    texto = " ".join(texto.split())
    if len(texto) <= max_chars:
        return texto
    if max_chars <= 3:
        return texto[:max_chars]
    return texto[: max_chars - 3] + "..."


def _centrar_texto(texto: str, ancho: int) -> str:
    texto = " ".join(texto.split())
    if len(texto) > ancho:
        texto = _comprimir_texto(texto, ancho)
    return texto.center(ancho)


def _alinear_izq_der(izquierda: str, derecha: str, ancho: int) -> str:
    izq = " ".join(izquierda.split())
    der = " ".join(derecha.split())
    espacio = max(1, ancho - len(izq) - len(der))
    if len(izq) + len(der) + espacio <= ancho:
        return izq + (" " * espacio) + der
    izq_max = max(1, ancho - len(der) - 1)
    izq = _comprimir_texto(izq, izq_max)
    espacio = max(1, ancho - len(izq) - len(der))
    return izq + (" " * espacio) + der


def generar_ticket_escpos(factura: Factura, ancho: int = 42) -> bytes:
    """Construye ticket ESC/POS para papel de 80mm usando maquetado de 72mm."""
    lineas: list[bytes] = []

    def cmd(x: bytes) -> None:
        lineas.append(x)

    def txt(s: str = "") -> None:
        lineas.append((s + "\n").encode("cp850", errors="replace"))

    def separador(char: str = "-") -> None:
        txt(char * ancho)

    fecha_impresion = datetime.now().strftime("%d/%m/%Y %H:%M")

    cmd(b"\x1b@")
    cmd(b"\x1ba\x01")
    cmd(b"\x1bE\x01")
    txt(_centrar_texto("ZOO PICASSO", ancho))
    cmd(b"\x1bE\x00")
    txt(_centrar_texto("C/ Pablo Picasso 59", ancho))
    txt(_centrar_texto(f"Tel: {TELEFONO_EMISOR}", ancho))
    txt(_centrar_texto(EMAIL_EMISOR, ancho))
    separador()
    txt("Ticket de venta")
    txt(_alinear_izq_der("Factura:", factura.numero_formateado, ancho))
    txt(_alinear_izq_der("Fecha:", fecha_impresion, ancho))
    cmd(b"\x1ba\x00")
    separador()

    if factura.cliente_nombre:
        txt("Cliente: " + _comprimir_texto(factura.cliente_nombre, ancho - 9))
    if factura.cliente_nif:
        txt("NIF/CIF: " + _comprimir_texto(factura.cliente_nif, ancho - 9))
    if factura.cliente_nombre or factura.cliente_nif:
        separador()

    txt("Concepto")
    txt("Cant x P.Unit                      Total")
    separador()

    for linea in factura.lineas:
        txt(_comprimir_texto(linea.concepto, ancho))
        detalle = f"{linea.cantidad} x {_normalizar_importe(linea.precio_unitario)}"
        total = _normalizar_importe(linea.total)
        txt(_alinear_izq_der(detalle, total, ancho))

    separador()
    total = _normalizar_importe(factura.total_con_iva)
    cmd(b"\x1bE\x01")
    txt(_alinear_izq_der("TOTAL", total, ancho))
    cmd(b"\x1bE\x00")
    # Mostrar efectivo entregado y cambio si corresponde
    pago = getattr(factura, '_pago_dict', None)
    if pago:
        efectivo_entregado = pago.get('efectivo_entregado', 0)
        cambio = pago.get('cambio', 0)
        metodo = pago.get('metodo_pago', '')
        if metodo in ('efectivo', 'mixto') and efectivo_entregado > 0:
            txt(_alinear_izq_der("Efectivo entregado", _normalizar_importe(efectivo_entregado), ancho))
            if cambio > 0:
                txt(_alinear_izq_der("Cambio a devolver", _normalizar_importe(cambio), ancho))
    txt("IVA incluido")
    separador()
    cmd(b"\x1ba\x01")
    txt(_centrar_texto("Gracias por tu compra", ancho))
    txt(_centrar_texto("Zoo Picasso", ancho))
    cmd(b"\n\n\n")
    cmd(b"\x1dV\x00")
    return b"".join(lineas)


def preview_ticket(factura: Factura, ancho: int = 42) -> str:
    """Devuelve el ticket ESC/POS como texto plano para validar el layout sin impresora."""
    lineas: list[str] = []

    def txt(s: str = "") -> None:
        lineas.append(s)

    def separador(char: str = "-") -> None:
        txt(char * ancho)

    fecha_impresion = datetime.now().strftime("%d/%m/%Y %H:%M")

    txt(_centrar_texto("ZOO PICASSO", ancho))
    txt(_centrar_texto("C/ Pablo Picasso 59", ancho))
    txt(_centrar_texto(f"Tel: {TELEFONO_EMISOR}", ancho))
    txt(_centrar_texto(EMAIL_EMISOR, ancho))
    separador()
    txt("Ticket de venta")
    txt(_alinear_izq_der("Factura:", factura.numero_formateado, ancho))
    txt(_alinear_izq_der("Fecha:", fecha_impresion, ancho))
    separador()

    if factura.cliente_nombre:
        txt("Cliente: " + _comprimir_texto(factura.cliente_nombre, ancho - 9))
    if factura.cliente_nif:
        txt("NIF/CIF: " + _comprimir_texto(factura.cliente_nif, ancho - 9))
    if factura.cliente_nombre or factura.cliente_nif:
        separador()

    txt("Concepto")
    txt(_alinear_izq_der("Cant x P.Unit", "Total", ancho))
    separador()

    for linea in factura.lineas:
        txt(_comprimir_texto(linea.concepto, ancho))
        detalle = f"{linea.cantidad} x {_normalizar_importe(linea.precio_unitario)}"
        total = _normalizar_importe(linea.total)
        txt(_alinear_izq_der(detalle, total, ancho))

    separador()
    txt(_alinear_izq_der("TOTAL", _normalizar_importe(factura.total_con_iva), ancho))
    txt("IVA incluido")
    separador()
    txt(_centrar_texto("Gracias por tu compra", ancho))
    txt(_centrar_texto("Zoo Picasso", ancho))

    return "\n".join(lineas)


def imprimir_ticket_usb_windows(ticket: bytes) -> str:
    """Imprime ticket ESC/POS en impresora predeterminada de Windows por RAW."""
    if not sys.platform.startswith("win"):
        raise RuntimeError("La impresion ESC/POS USB esta habilitada solo en Windows.")

    try:
        import win32print  # type: ignore[import-not-found]
    except Exception as ex:
        raise RuntimeError(
            "No se encontro pywin32. Ejecuta sincronizacion de dependencias en Windows."
        ) from ex

    impresora = os.getenv("ESC_POS_PRINTER_NAME", "").strip() or win32print.GetDefaultPrinter()
    if not impresora:
        raise RuntimeError("No hay impresora predeterminada disponible.")

    hprinter = win32print.OpenPrinter(impresora)
    try:
        win32print.StartDocPrinter(hprinter, 1, ("Ticket factura", "", "RAW"))
        try:
            win32print.StartPagePrinter(hprinter)
            win32print.WritePrinter(hprinter, ticket)
            win32print.EndPagePrinter(hprinter)
        finally:
            win32print.EndDocPrinter(hprinter)
    finally:
        win32print.ClosePrinter(hprinter)

    return impresora