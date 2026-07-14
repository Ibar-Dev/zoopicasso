import os
import sys
from datetime import datetime

from src.factura_model import EMAIL_EMISOR
from src.factura_model import TELEFONO_EMISOR
from src.factura_model import Factura, PagoInfo


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


def generar_ticket_escpos(factura: Factura, ancho: int = 42, pago: PagoInfo | None = None) -> bytes:
    """
    Genera bytecode ESC/POS (Seiko Epson) para impresora térmica POS-80.
    
    ════════════════════════════════════════════════════════════════════════════════
    RESPONSABILIDAD:
      Convierte datos de factura a protocolo ESC/POS para impresoras térmicas.
      No comunica directamente con impresora; solo genera bytecode.
    
    ENTRADA:
      factura: src.factura_model.Factura - Datos de venta con cliente y líneas
      ancho: int - Caracteres disponibles en papel (42 para 80mm, 32 para 58mm)
      pago: src.factura_model.PagoInfo - Opcional, datos de efectivo/cambio
    
    SALIDA:
      bytes: Secuencia de bytes ESC/POS listo para impresora térmica
    
    PROTOCOLO ESC/POS:
      - \\x1b@ = Reset impresora
      - \\x1bE\\x01/\\x00 = Bold ON/OFF
      - \\x1ba\\x01/\\x00 = Centrar ON/OFF
      - \\x1dV\\x00 = Corte de papel
      - cp850 = Codificación para caracteres españoles
    
    ESTRUCTURA DEL OUTPUT:
      [RESET] [CABECERA] [DATOS CLIENTE] [LÍNEAS] [TOTAL] [PIE] [CORTE]
    
    COMUNICACIÓN:
      - ✅ Entrada: src.factura_model.Factura, EMAIL_EMISOR, TELEFONO_EMISOR
      - ✅ Salida: bytes ESC/POS
      - ✅ Usado por: main.py, web/app.py, poll_and_print.py
      - ❌ NO comunica con impresora: Ver imprimir_ticket_usb_windows()
    
    EXCEPCIONES:
      ValueError: Si factura sin líneas
    
    EJEMPLO:
      factura = Factura(...)
      ticket_bytes = generar_ticket_escpos(factura, ancho=42)
      # ticket_bytes listo para imprimir_ticket_usb_windows()
    """
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
    if pago and pago.metodo_pago in ('efectivo', 'mixto') and pago.efectivo_entregado > 0:
        txt(_alinear_izq_der("Efectivo entregado", _normalizar_importe(pago.efectivo_entregado), ancho))
        if pago.cambio > 0:
            txt(_alinear_izq_der("Cambio a devolver", _normalizar_importe(pago.cambio), ancho))
    txt("IVA incluido")
    separador()
    cmd(b"\x1ba\x01")
    txt(_centrar_texto("Gracias por tu compra", ancho))
    txt(_centrar_texto("Zoo Picasso", ancho))
    cmd(b"\n\n\n")
    cmd(b"\x1dV\x00")
    return b"".join(lineas)


def preview_ticket(factura: Factura, ancho: int = 42) -> str:
    """
    Genera preview de ticket como texto plano (sin impresora).
    
    ════════════════════════════════════════════════════════════════════════════════
    RESPONSABILIDAD:
      Valida layout del ticket sin necesidad de impresora.
      Útil para testing, debugging y preview en UI web.
    
    ENTRADA:
      factura: src.factura_model.Factura
      ancho: int - Caracteres disponibles (42 o 32)
    
    SALIDA:
      str: Ticket formateado como texto puro (sin ESC/POS)
    
    COMUNICACIÓN:
      - ✅ Entrada: src.factura_model.Factura
      - ✅ Salida: str (texto plano)
      - ✅ Usado por: Tests, validación de layout
    
    EJEMPLO:
      preview = preview_ticket(factura)
      print(preview)  # Muestra layout sin enviar a impresora
    """
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
    """
    Envía ticket ESC/POS a impresora Windows por RAW printing.
    
    ════════════════════════════════════════════════════════════════════════════════
    RESPONSABILIDAD:
      Imprime bytecode ESC/POS en impresora predeterminada Windows.
      Acceso a impresoras a nivel SO (win32print API).
    
    ENTRADA:
      ticket: bytes en formato ESC/POS (salida de generar_ticket_escpos)
    
    SALIDA:
      str: Nombre de la impresora utilizada
    
    SO SOPORTADO:
      ✅ Windows (require pywin32)
      ❌ Linux/Mac: Lanza RuntimeError
    
    DEPENDENCIAS EXTERNAS:
      - pywin32: Acceso a APIs de Windows (win32print)
      - Instalación: uv sync (ya incluido en pyproject.toml)
    
    CONFIGURACIÓN:
      - Variable env: ESC_POS_PRINTER_NAME (opcional)
      - Default: Usa impresora predeterminada del SO
    
    API WINDOWS UTILIZADA:
      - win32print.GetDefaultPrinter() → Nombre impresora predeterminada
      - win32print.OpenPrinter() → Conecta con impresora
      - win32print.StartDocPrinter() → Inicia documento RAW
      - win32print.WritePrinter() → Envía bytes
      - win32print.EndDocPrinter() → Cierra documento
      - win32print.ClosePrinter() → Desconecta
    
    COMUNICACIÓN:
      - ✅ Entrada: bytes ESC/POS (de generar_ticket_escpos)
      - ✅ Salida: str (nombre de impresora)
      - ✅ Comunica con: Impresora USB/Spooler Windows
      - ✅ Usado por: main.py, tickets_main.py, poll_and_print.py
    
    EXCEPCIONES:
      RuntimeError: Si no es Windows o pywin32 no disponible
      Exception: Si impresora no accesible
    
    EJEMPLO:
      ticket_bytes = generar_ticket_escpos(factura)
      impresora_usada = imprimir_ticket_usb_windows(ticket_bytes)
      print(f"Imprimió en: {impresora_usada}")
    """
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