# poll_and_print.py

import time
import base64
import requests

from src.printer import imprimir_ticket_usb_windows

URL_RENDER = "https://TU-APP-EN-RENDER.com/api/impresion/siguiente"
CARPETA_TICKETS = "C:/Facturas_Tickets/"


def iniciar_repartidor():
    print("[*] Iniciando el Agente Local de Impresión...")

    while True:
        try:
            # 1. El repartidor pregunta si hay paquetes en la repisa
            respuesta = requests.get(URL_RENDER, timeout=5)

            # 2. Evaluamos la respuesta del servidor
            if respuesta.status_code == 200:
                datos = respuesta.json()
                if datos.get("hay_ticket"):
                    print("[+] ¡Ticket encontrado! Descargando...")

                    # 3. Abrimos el "tupper" hermético (Base64)
                    ticket_b64 = datos["ticket_b64"]
                    ticket_bytes = base64.b64decode(ticket_b64)

                    # 4. Guardamos el respaldo local con nombre único basado en el tiempo
                    nombre_archivo = f"{CARPETA_TICKETS}ticket_{int(time.time())}.bin"
                    with open(nombre_archivo, "wb") as f:
                        f.write(ticket_bytes)
                    print(f"[*] Respaldo guardado en: {nombre_archivo}")

                    # 5. Entregamos el paquete crudo al Spooler de Windows
                    impresora = imprimir_ticket_usb_windows(ticket_bytes)
                    print(f"[*] Ticket enviado a la impresora: {impresora}\n")

            elif respuesta.status_code == 204:
                # No hay tickets pendientes
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
