# poll_and_print.py

import time
import base64
import requests

import os

from src.printer import imprimir_ticket_usb_windows

# Configuración - Reemplazar con la URL real de Render
BASE_URL = "https://zoopicasso.onrender.com"
URL_POLL = f"{BASE_URL}/api/impresion/siguiente"
URL_DESCARGA = f"{BASE_URL}/api/descargar/"
CARPETA_TICKETS = "C:/Facturas_Tickets/"

# Asegurar que la carpeta existe localmente
if not os.path.exists(CARPETA_TICKETS):
    try:
        os.makedirs(CARPETA_TICKETS)
    except Exception as e:
        print(f"[!] No se pudo crear la carpeta {CARPETA_TICKETS}: {e}")

def descargar_excel(nombre_archivo):
    """Descarga el archivo Excel desde Render y lo guarda localmente."""
    try:
        url = f"{URL_DESCARGA}{nombre_archivo}"
        print(f"[*] Sincronizando Excel: {nombre_archivo}...")
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            ruta_local = os.path.join(CARPETA_TICKETS, nombre_archivo)
            with open(ruta_local, "wb") as f:
                f.write(res.content)
            print(f"[+] Excel guardado en: {ruta_local}")
        else:
            print(f"[!] Error al descargar Excel ({res.status_code}): {nombre_archivo}")
    except Exception as e:
        print(f"[!] Fallo crítico al descargar Excel {nombre_archivo}: {e}")

def iniciar_repartidor():
    print("[*] Iniciando el Agente Local de Impresión y Sincronización...")
    print(f"[*] Carpeta de destino: {CARPETA_TICKETS}")

    while True:
        try:
            # 1. El repartidor pregunta si hay paquetes en la repisa
            respuesta = requests.get(URL_POLL, timeout=5)

            # 2. Evaluamos la respuesta del servidor
            if respuesta.status_code == 200:
                datos = respuesta.json()
                if datos.get("hay_ticket"):
                    print(f"\n[+] ¡Nuevo ítem detectado!")

                    # 3. Procesar Ticket (Impresión)
                    ticket_b64 = datos.get("ticket_b64")
                    if ticket_b64:
                        ticket_bytes = base64.b64decode(ticket_b64)
                        # Guardamos el respaldo local del binario
                        nombre_bin = os.path.join(CARPETA_TICKETS, f"ticket_{int(time.time())}.bin")
                        with open(nombre_bin, "wb") as f:
                            f.write(ticket_bytes)
                        
                        # Enviamos a la impresora
                        impresora = imprimir_ticket_usb_windows(ticket_bytes)
                        print(f"[*] Ticket impreso ({impresora}) y respaldado en .bin")

                    # 4. Procesar Excel (Sincronización)
                    archivo_xlsx = datos.get("archivo_xlsx")
                    if archivo_xlsx:
                        descargar_excel(archivo_xlsx)

            elif respuesta.status_code == 204:
                # No hay paquetes pendientes
                pass

        except requests.exceptions.RequestException as e:
            # Protocolo de emergencia: si se cae internet, no cerramos el programa
            print(f"[-] Problema de conexión. Reintentando en 5s... (Error: {e})")
            time.sleep(5)
            continue

        # Descanso de 3 segundos entre viajes para no saturar Render
        time.sleep(3)


if __name__ == "__main__":
    iniciar_repartidor()
