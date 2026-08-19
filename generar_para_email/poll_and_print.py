#!/usr/bin/env python3
"""
poll_and_print.py - Agente Local de Impresión y Sincronización
===============================================================

Agente que corre continuamente en Windows (local).
Responsabilidades:
  1. Consulta servidor por tickets pendientes (cola_impresion)
  2. Descarga tickets ESC/POS en base64
  3. Imprime tickets en impresora USB Windows
  4. Descarga archivos Excel asociados
  5. Maneja desconexiones de internet gracefully

Flujo:
  ┌─ Servidor (Render/Web)
  │  └─ Cola persistente: cola_impresion.json
  │     └─ items = [{"ticket": b64, "archivo_xlsx": "factura_2024_001.xlsx"}]
  │
  ├─ Poll (GET /api/impresion/siguiente)
  │  ├─ Si 200 OK: hay_ticket=true, ticket_b64=..., archivo_xlsx=...
  │  └─ Si 204 No Content: cola vacía, reintentar después
  │
  ├─ Impresión (Windows USB)
  │  └─ Decodifica base64 → bytes → imprimir_ticket_usb_windows()
  │
  └─ Sincronización (GET /api/descargar/{archivo})
     └─ Descarga Excel a carpeta local

Instalación:
  # En Windows
  python -m pip install requests
  # En generar_para_email/
  python poll_and_print.py

Configuración:
  La carpeta de destino y el servidor se guardan en agente_config.json
  (junto a este script). Opciones en orden de precedencia:
    - --carpeta RUTA        → carpeta donde guardar archivos (se guarda)
    - --elegir-carpeta      → abre selector de carpeta nativo
    - --servidor URL        → URL base del servidor (se guarda)
    - TICKETS_FOLDER        → variable de entorno (solo para esa ejecución)
    - PRINTER_SERVER_URL    → variable de entorno (solo para esa ejecución)
    - POLL_INTERVAL         → segundos entre consultas (default: 3)
    - RECONNECT_DELAY       → segundos de espera en desconexión (default: 5)

Logs:
  Cada acción genera log:
    [+] Éxito
    [-] Error de conexión
    [!] Error crítico
    [*] Acción en progreso
"""

import time
import base64
import requests
import logging
import os
import sys
import hashlib
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

# Importar funciones de impresión
sys.path.insert(0, str(Path(__file__).parent))
from src.printer import imprimir_ticket_usb_windows


# ────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN PERSISTENTE DEL AGENTE
# ────────────────────────────────────────────────────────────────────────────

# Archivo donde se guarda la configuración elegida por el usuario.
CONFIG_RUTA = Path(__file__).resolve().parent / "agente_config.json"

CARPETA_CONFIG_KEY = "carpeta_tickets"
SERVER_URL_CONFIG_KEY = "servidor_url"


def cargar_config() -> dict:
    """Carga la configuración guardada por el usuario. Retorna {} si no existe."""
    if not CONFIG_RUTA.exists():
        return {}
    try:
        datos = json.loads(CONFIG_RUTA.read_text(encoding="utf-8"))
        return datos if isinstance(datos, dict) else {}
    except Exception:
        return {}


def guardar_config(config: dict) -> None:
    """Persiste la configuración del usuario en CONFIG_RUTA."""
    try:
        CONFIG_RUTA.write_text(
            json.dumps(config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as e:
        print(f"[!] No se pudo guardar la configuración en {CONFIG_RUTA}: {e}")


# ────────────────────────────────────────────────────────────────────────────
# SELECTOR DE CARPETA (el usuario elige dónde guardar los archivos)
# ────────────────────────────────────────────────────────────────────────────

def elegir_carpeta_dialogo() -> Optional[Path]:
    """Abre un selector de carpeta nativo (tkinter). Retorna None si cancela."""
    try:
        import tkinter as tk
        from tkinter import filedialog

        raiz = tk.Tk()
        raiz.withdraw()
        raiz.attributes("-topmost", True)
        try:
            carpeta = filedialog.askdirectory(
                title="Elige la carpeta donde guardar tickets y facturas"
            )
        finally:
            raiz.destroy()
        return Path(carpeta) if carpeta else None
    except Exception:
        return None


def pedir_carpeta_consola() -> Optional[Path]:
    """Fallback sin ventanas: pide la ruta por consola."""
    print("=" * 70)
    print("CONFIGURACIÓN DE CARPETA")
    print("=" * 70)
    print("¿Dónde quieres guardar los tickets y las facturas descargadas?")
    print("(Deja vacío y pulsa Enter para usar el Escritorio)")
    ruta = input("Ruta: ").strip()
    if not ruta:
        return (Path.home() / "Desktop").resolve()
    return Path(ruta).expanduser()


def resolver_carpeta(arg_carpeta: Optional[str]) -> Path:
    """
    Determina la carpeta de guardado, en este orden:
      1. --carpeta / --elegir-carpeta (argumento CLI)
      2. Variable de entorno TICKETS_FOLDER
      3. Carpeta guardada en agente_config.json
      4. Primera ejecución: se pregunta al usuario y se guarda la respuesta
      5. Fallback final: Escritorio del usuario
    """
    config = cargar_config()

    if arg_carpeta:
        carpeta = Path(arg_carpeta).expanduser()
        config[CARPETA_CONFIG_KEY] = str(carpeta)
        guardar_config(config)
    else:
        env_carpeta = os.getenv("TICKETS_FOLDER", "").strip()
        if env_carpeta:
            carpeta = Path(env_carpeta).expanduser()
        elif config.get(CARPETA_CONFIG_KEY):
            carpeta = Path(config[CARPETA_CONFIG_KEY]).expanduser()
        else:
            carpeta = elegir_carpeta_dialogo() or pedir_carpeta_consola()
            config[CARPETA_CONFIG_KEY] = str(carpeta)
            guardar_config(config)

    return carpeta.resolve()


# ────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ────────────────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(
    description="Agente local de impresión y sincronización de facturas."
)
parser.add_argument(
    "--carpeta",
    help="Carpeta local donde guardar tickets y facturas (se guarda en la configuración).",
)
parser.add_argument(
    "--elegir-carpeta",
    action="store_true",
    help="Abre el selector de carpeta para cambiar dónde se guardan los archivos.",
)
parser.add_argument(
    "--servidor",
    help="URL base del servidor (se guarda en la configuración).",
)
args = parser.parse_args()

config_agente = cargar_config()
if args.elegir_carpeta:
    carpeta_nueva = elegir_carpeta_dialogo() or pedir_carpeta_consola()
    config_agente[CARPETA_CONFIG_KEY] = str(carpeta_nueva)
    guardar_config(config_agente)
    print(f"[+] Carpeta configurada: {carpeta_nueva}")

if args.servidor:
    config_agente[SERVER_URL_CONFIG_KEY] = args.servidor
    guardar_config(config_agente)

# URL del servidor: --servidor > PRINTER_SERVER_URL > configuración guardada > localhost
BASE_URL = (
    args.servidor
    or os.getenv("PRINTER_SERVER_URL", "").strip()
    or config_agente.get(SERVER_URL_CONFIG_KEY, "")
    or "http://localhost:8000"
)

# Carpeta local donde guardar tickets y archivos (elegida y guardada por el usuario)
TICKETS_FOLDER = resolver_carpeta(args.carpeta)

# Intervalos (segundos)
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "3"))        # Entre consultas
RECONNECT_DELAY = int(os.getenv("RECONNECT_DELAY", "5"))   # Después de error
TIMEOUT_REQUEST = 10  # Timeout para requests

# Crear carpeta si no existe
TICKETS_FOLDER.mkdir(parents=True, exist_ok=True)

# Configurar logging
LOG_FILE = TICKETS_FOLDER / "poll_and_print.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────
# CLASE: AGENTE DE IMPRESIÓN
# ────────────────────────────────────────────────────────────────────────────

class AgenteImpresion:
    """
    Agente de impresión y sincronización local.
    
    Mantiene sesión HTTP, consulta server, imprime, descarga archivos.
    Maneja reintentos automáticos en caso de desconexión.
    """
    
    def __init__(self, url_base: str, carpeta: Path):
        """
        Inicializa agente.
        
        Args:
            url_base: URL del servidor (ej: http://localhost:8000)
            carpeta: Carpeta local para guardar tickets y archivos
        """
        self.url_base = url_base
        self.carpeta = carpeta
        self.session = requests.Session()
        self.conectado = False
        self.estadisticas = {
            "tickets_impresos": 0,
            "archivos_sincronizados": 0,
            "errores_conexion": 0,
            "errores_impresion": 0,
        }
    
    def verificar_conexion(self) -> bool:
        """
        Verifica que el servidor esté accesible.
        
        Returns:
            True si servidor responde, False si hay error
        """
        try:
            resp = self.session.get(f"{self.url_base}/api/health", timeout=5)
            if resp.status_code == 200:
                self.conectado = True
                logger.info(f"✅ Conexión verificada con {self.url_base}")
                return True
        except Exception as e:
            logger.warning(f"⚠️  No hay conexión: {e}")
        
        self.conectado = False
        return False
    
    def consultar_tickets(self) -> Optional[dict]:
        """
        Consulta servidor por ticket pendiente.
        
        Returns:
            Dict con {"hay_ticket": bool, "ticket_b64": str, "archivo_xlsx": str}
            O None si error
        
        HTTP Status:
            200 - OK con ticket
            204 - Cola vacía (reintentar después)
            401 - No autenticado
            5xx - Error servidor
        """
        try:
            url = f"{self.url_base}/api/impresion/siguiente"
            resp = self.session.get(url, timeout=TIMEOUT_REQUEST)
            
            if resp.status_code == 200:
                return resp.json()
            
            elif resp.status_code == 204:
                # Cola vacía - es normal
                return {"hay_ticket": False}
            
            elif resp.status_code == 401:
                logger.error("❌ No autenticado (401). Verificar credenciales.")
                return None
            
            else:
                logger.warning(f"⚠️  Error en consulta de tickets ({resp.status_code})")
                return None
        
        except requests.exceptions.Timeout:
            logger.warning(f"⏱️  Timeout al consultar tickets")
            return None
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"❌ Error de conexión: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error inesperado al consultar tickets: {e}")
            return None
    
    def imprimir_ticket(self, ticket_b64: str) -> bool:
        """
        Imprime ticket en impresora USB Windows.
        
        Args:
            ticket_b64: Ticket en base64
        
        Returns:
            True si éxito, False si error
        """
        try:
            # Decodificar base64
            ticket_bytes = base64.b64decode(ticket_b64)
            
            # Guardar respaldo local
            nombre_bin = f"ticket_{int(time.time())}.bin"
            ruta_local = self.carpeta / nombre_bin
            with open(ruta_local, "wb") as f:
                f.write(ticket_bytes)
            
            # Imprimir
            impresora = imprimir_ticket_usb_windows(ticket_bytes)
            
            logger.info(f"✅ Ticket impreso en {impresora} (respaldo: {nombre_bin})")
            self.estadisticas["tickets_impresos"] += 1
            
            return True
        
        except Exception as e:
            logger.error(f"❌ Error al imprimir ticket: {e}", exc_info=True)
            self.estadisticas["errores_impresion"] += 1
            return False
    
    def descargar_excel(self, nombre_archivo: str) -> bool:
        """
        Descarga archivo Excel desde servidor.
        
        Args:
            nombre_archivo: Nombre del archivo (ej: factura_2024_001.xlsx)
        
        Returns:
            True si éxito, False si error
        """
        try:
            url = f"{self.url_base}/api/descargar/{nombre_archivo}"
            
            logger.info(f"📥 Descargando Excel: {nombre_archivo}...")
            resp = self.session.get(url, timeout=TIMEOUT_REQUEST)
            
            if resp.status_code == 404:
                logger.warning(f"⚠️  Archivo no encontrado: {nombre_archivo}")
                return False
            
            if resp.status_code == 401:
                logger.error("❌ No autenticado (401) al descargar Excel")
                return False
            
            if resp.status_code != 200:
                logger.warning(f"⚠️  Error al descargar ({resp.status_code}): {nombre_archivo}")
                return False
            
            # Guardar archivo
            ruta_local = self.carpeta / nombre_archivo
            with open(ruta_local, "wb") as f:
                f.write(resp.content)
            
            # Verificar integridad
            tamanio = ruta_local.stat().st_size
            logger.info(f"✅ Excel guardado: {nombre_archivo} ({tamanio} bytes)")
            self.estadisticas["archivos_sincronizados"] += 1
            
            return True
        
        except requests.exceptions.Timeout:
            logger.warning(f"⏱️  Timeout al descargar: {nombre_archivo}")
            return False
        except Exception as e:
            logger.error(f"❌ Error al descargar Excel: {e}", exc_info=True)
            return False
    
    def procesar_ticket(self, datos: dict) -> bool:
        """
        Procesa un ticket: imprime y descarga archivos asociados.
        
        Args:
            datos: Dict con {"hay_ticket": bool, "ticket_b64": str, "archivo_xlsx": str}
        
        Returns:
            True si éxito, False si error
        """
        if not datos.get("hay_ticket"):
            return False
        
        logger.info("\n" + "="*70)
        logger.info("🎫 NUEVO TICKET DETECTADO")
        logger.info("="*70)
        
        ticket_b64 = datos.get("ticket_b64")
        archivo_xlsx = datos.get("archivo_xlsx")
        
        exito = True
        
        # 1. Imprimir ticket
        if ticket_b64:
            if not self.imprimir_ticket(ticket_b64):
                exito = False
        else:
            logger.warning("⚠️  No hay datos de ticket para imprimir")
            exito = False
        
        # 2. Descargar Excel (si existe)
        if archivo_xlsx:
            if not self.descargar_excel(archivo_xlsx):
                exito = False
        else:
            logger.info("ℹ️  Sin archivo Excel asociado")
        
        logger.info("="*70 + "\n")
        return exito
    
    def mostrar_estadisticas(self):
        """Muestra estadísticas de funcionamiento."""
        logger.info(
            f"\n📊 ESTADÍSTICAS:\n"
            f"  ✅ Tickets impresos: {self.estadisticas['tickets_impresos']}\n"
            f"  📥 Archivos sincronizados: {self.estadisticas['archivos_sincronizados']}\n"
            f"  ❌ Errores de impresión: {self.estadisticas['errores_impresion']}\n"
            f"  🔌 Errores de conexión: {self.estadisticas['errores_conexion']}\n"
        )
    
    def iniciar(self):
        """
        Inicia el ciclo de polling continuo.
        
        El agente:
          1. Verifica conexión
          2. Consulta tickets
          3. Imprime y descarga
          4. Espera interval
          5. Repite (con manejo de errores)
        """
        logger.info("="*70)
        logger.info("🚀 INICIANDO AGENTE LOCAL DE IMPRESIÓN Y SINCRONIZACIÓN")
        logger.info("="*70)
        logger.info(f"📍 Servidor: {self.url_base}")
        logger.info(f"📁 Carpeta: {self.carpeta}")
        logger.info(f"⏱️  Intervalo de consulta: {POLL_INTERVAL} segundos")
        logger.info(f"🔌 Timeout de conexión: {TIMEOUT_REQUEST} segundos")
        logger.info("="*70 + "\n")
        
        contador_ciclos = 0
        intentos_conexion = 0
        
        while True:
            contador_ciclos += 1
            
            try:
                # Verificar conexión periódicamente (cada 10 ciclos)
                if contador_ciclos % 10 == 0:
                    if not self.verificar_conexion():
                        intentos_conexion += 1
                        if intentos_conexion > 3:
                            logger.error("❌ Servidor no responde. Reintentando...")
                            self.estadisticas["errores_conexion"] += 1
                            intentos_conexion = 0
                        time.sleep(RECONNECT_DELAY)
                        continue
                
                # Consultar tickets
                datos = self.consultar_tickets()
                if datos is None:
                    # Error en consulta
                    self.estadisticas["errores_conexion"] += 1
                    time.sleep(RECONNECT_DELAY)
                    continue
                
                # Procesar si hay ticket
                if datos.get("hay_ticket"):
                    self.procesar_ticket(datos)
                
                # Esperar antes del siguiente ciclo
                time.sleep(POLL_INTERVAL)
            
            except KeyboardInterrupt:
                logger.info("\n🛑 AGENTE DETENIDO POR EL USUARIO")
                self.mostrar_estadisticas()
                break
            
            except Exception as e:
                logger.error(f"❌ Error crítico en ciclo {contador_ciclos}: {e}", exc_info=True)
                time.sleep(RECONNECT_DELAY)


# ────────────────────────────────────────────────────────────────────────────
# PUNTO DE ENTRADA
# ────────────────────────────────────────────────────────────────────────────

def main():
    """Punto de entrada principal."""
    
    logger.info(f"Agente iniciado a las {datetime.now().isoformat()}")
    logger.info(f"Python: {sys.version}")
    logger.info(f"Carpeta: {TICKETS_FOLDER}")
    logger.info(f"Log: {LOG_FILE}")
    logger.info(f"Configuración guardada en: {CONFIG_RUTA}")
    
    agente = AgenteImpresion(BASE_URL, TICKETS_FOLDER)
    agente.iniciar()


if __name__ == "__main__":
    main()
