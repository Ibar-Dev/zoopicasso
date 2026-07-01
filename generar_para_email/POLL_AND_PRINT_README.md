# poll_and_print.py - Agente de Impresión Local

## 📋 Descripción

Agente Windows que corre continuamente para:
1. **Consultar servidor** por tickets pendientes (`/api/impresion/siguiente`)
2. **Imprimir tickets** en impresora USB Windows
3. **Descargar archivos** Excel asociados
4. **Manejar desconexiones** de internet gracefully

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────┐
│  Servidor FastAPI (Render o local)     │
│  ├─ POST /api/generar (cliente web)    │
│  ├─ Cola: data/cola_impresion.json     │
│  └─ Endpoint: GET /api/impresion/siguiente
│
└──────────────────┬──────────────────────┘
                   │ (consulta cada 3 seg)
                   ↓
        ┌─────────────────────┐
        │   poll_and_print.py │
        │   (Windows local)   │
        ├─────────────────────┤
        │ 1. Consultar cola   │
        │ 2. Imprimir (USB)   │
        │ 3. Descargar Excel  │
        │ 4. Logs/Stats       │
        └─────────────────────┘
                   ↓
        ┌─────────────────────┐
        │  C:/Facturas_Tickets│
        │ (carpeta local)     │
        └─────────────────────┘
```

## 🚀 Instalación

### Requisitos
- Python 3.9+
- Windows 10/11
- Impresora USB ESC/POS

### Paso 1: Descargar el proyecto

```bash
git clone https://github.com/Ibar-Dev/zoopicasso.git
cd zoopicasso/generar_para_email
```

### Paso 2: Instalar dependencias

```bash
# Crear virtual environment (recomendado)
python -m venv venv
venv\Scripts\activate

# Instalar dependencias
python -m pip install requests

# O usar uv (más rápido)
uv sync
```

### Paso 3: Ejecutar

```bash
# Opción A: Terminal
python poll_and_print.py

# Opción B: Script de instalación (recomendado en Windows)
./install_local_agent.bat

# Opción C: Como servicio Windows (tareas programadas)
# Ver sección "Ejecución como Servicio" abajo
```

## ⚙️ Configuración

### Variables de Entorno

Por defecto, apunta a localhost. Para producción:

```bash
# Windows CMD
set PRINTER_SERVER_URL=https://zoopicasso.onrender.com
set TICKETS_FOLDER=C:/Facturas_Tickets/
set POLL_INTERVAL=3
set RECONNECT_DELAY=5
python poll_and_print.py

# Windows PowerShell
$env:PRINTER_SERVER_URL="https://zoopicasso.onrender.com"
$env:TICKETS_FOLDER="C:/Facturas_Tickets/"
python poll_and_print.py

# Linux/Mac
export PRINTER_SERVER_URL="https://zoopicasso.onrender.com"
export TICKETS_FOLDER="/home/tickets/"
python poll_and_print.py
```

### Parámetros

| Variable | Default | Descripción |
|----------|---------|-------------|
| `PRINTER_SERVER_URL` | `http://localhost:8000` | URL base del servidor |
| `TICKETS_FOLDER` | `C:/Facturas_Tickets/` | Carpeta local de tickets |
| `POLL_INTERVAL` | `3` | Segundos entre consultas |
| `RECONNECT_DELAY` | `5` | Segundos de espera tras error |

## 🔌 Flujo de Operación

### Ciclo Normal

```
1️⃣  Verificar conexión (cada 10 ciclos)
    ↓
2️⃣  GET /api/impresion/siguiente
    ↓
    ├─ 200 OK → hay_ticket: true
    │   ├─ Decodificar base64 → bytes
    │   ├─ Guardar respaldo local (.bin)
    │   ├─ Imprimir en USB
    │   ├─ Si hay Excel → Descargar
    │   └─ Log: ✅ Éxito
    │
    └─ 204 No Content → hay_ticket: false
        └─ Esperar 3 segundos, reintentar
    
    └─ 401 Unauthorized → Error de auth
        └─ Log error crítico
    
    └─ Error conexión
        └─ Esperar 5 segundos, reintentar
```

### Manejo de Errores

| Escenario | Acción | Reintento |
|-----------|--------|-----------|
| Cola vacía (204) | Esperar | 3 segundos |
| Timeout | Log warning | 5 segundos |
| No autenticado (401) | Log error crítico | Manual |
| Impresora no disponible | Log error, respaldo .bin | Siguiente ticket |
| Archivo no encontrado (404) | Log warning, continuar | N/A |
| Error de conexión | Incrementar contador | 5 segundos |

## 📊 Logs y Estadísticas

### Archivos de Log

```
C:/Facturas_Tickets/
├─ poll_and_print.log       ← Log principal
├─ ticket_1719820640.bin    ← Respaldo de ticket impreso
├─ factura_2024_001.xlsx    ← Excel sincronizado
└─ ...
```

### Ejemplo de Log

```
2024-06-23 14:30:15 [INFO] 🚀 INICIANDO AGENTE LOCAL DE IMPRESIÓN Y SINCRONIZACIÓN
2024-06-23 14:30:15 [INFO] 📍 Servidor: http://localhost:8000
2024-06-23 14:30:15 [INFO] 📁 Carpeta: C:/Facturas_Tickets/
2024-06-23 14:30:15 [INFO] ⏱️  Intervalo de consulta: 3 segundos

2024-06-23 14:30:20 [INFO] ✅ Conexión verificada con http://localhost:8000

2024-06-23 14:30:23 [INFO] ======================================================================
2024-06-23 14:30:23 [INFO] 🎫 NUEVO TICKET DETECTADO
2024-06-23 14:30:23 [INFO] ======================================================================
2024-06-23 14:30:23 [INFO] ✅ Ticket impreso en Epson TM-T20II (respaldo: ticket_1719820640.bin)
2024-06-23 14:30:24 [INFO] 📥 Descargando Excel: factura_2024_001.xlsx...
2024-06-23 14:30:24 [INFO] ✅ Excel guardado: factura_2024_001.xlsx (65536 bytes)
2024-06-23 14:30:24 [INFO] ======================================================================

2024-06-23 14:30:27 [INFO] 📊 ESTADÍSTICAS:
2024-06-23 14:30:27 [INFO]   ✅ Tickets impresos: 1
2024-06-23 14:30:27 [INFO]   📥 Archivos sincronizados: 1
2024-06-23 14:30:27 [INFO]   ❌ Errores de impresión: 0
2024-06-23 14:30:27 [INFO]   🔌 Errores de conexión: 0
```

## 💻 Ejecución como Servicio Windows

### Opción 1: Task Scheduler (Tareas Programadas)

```bash
# 1. Crear archivo de batch
# Guardar como: iniciar_agente.bat
@echo off
cd C:\ruta\a\zoopicasso\generar_para_email
python poll_and_print.py

# 2. Abrir Task Scheduler (Tareas Programadas)
# WIN + R → taskschd.msc

# 3. Crear tarea
# Nombre: Agente de Impresión Zoopicasso
# Trigger: Al iniciar, En línea
# Acción: Ejecutar iniciar_agente.bat
# Opciones: Ejecutar con privilegios más altos
```

### Opción 2: NSSM (Non-Sucking Service Manager)

```bash
# Descargar NSSM: https://nssm.cc/download
# Extraer a: C:\nssm\

# Instalar servicio
C:\nssm\nssm.exe install PrinterAgent "C:\path\to\python.exe" "poll_and_print.py"

# Iniciar servicio
net start PrinterAgent

# Ver estado
nssm status PrinterAgent

# Detener servicio
net stop PrinterAgent

# Desinstalar
C:\nssm\nssm.exe remove PrinterAgent confirm
```

### Opción 3: py2exe (Ejecutable independiente)

```bash
# Instalar herramientas
pip install py2exe

# Crear setup.py (ver ejemplo abajo)
python setup.py py2exe

# Resultado: dist/poll_and_print.exe
```

## 🔍 Debugging

### Ver qué pasa en tiempo real

```bash
# Ejecutar con output a pantalla
python poll_and_print.py

# Ver últimas líneas del log
type C:\Facturas_Tickets\poll_and_print.log | tail -20
```

### Verificar conexión al servidor

```bash
# Verificar que el servidor responde
curl http://localhost:8000/api/health

# Ver cola de impresión
python -c "import json; print(json.dumps(json.load(open('data/cola_impresion.json')), indent=2))"
```

### Probar manualmente

```python
import requests
import base64
from src.printer import imprimir_ticket_usb_windows

# Consultar tickets
resp = requests.get("http://localhost:8000/api/impresion/siguiente")
if resp.status_code == 200:
    datos = resp.json()
    ticket_b64 = datos["ticket_b64"]
    ticket_bytes = base64.b64decode(ticket_b64)
    
    # Imprimir
    impresora = imprimir_ticket_usb_windows(ticket_bytes)
    print(f"Impreso en: {impresora}")
```

## ⚠️ Troubleshooting

### "No se encuentra la impresora"

```python
# Ver impresoras disponibles
from src.printer import listar_impresoras_usb
impresoras = listar_impresoras_usb()
print(impresoras)

# Verificar que la impresora esté conectada en USB
# Devices → Printers and Devices
```

### "ConnectionRefusedError: [Errno 111]"

```
Problema: No hay conexión con el servidor
Soluciones:
  1. Verificar que servidor está corriendo en http://localhost:8000
  2. Cambiar PRINTER_SERVER_URL a la URL correcta
  3. Verificar firewall
```

### "Timeout waiting for connection"

```
Problema: Servidor responde muy lentamente
Soluciones:
  1. Aumentar RECONNECT_DELAY a 10
  2. Verificar conexión de red
  3. Revisar logs del servidor (uvicorn)
```

## 📈 Monitoreo

### Ver estadísticas

```bash
# El agente muestra automáticamente al Ctrl+C:
# 📊 ESTADÍSTICAS:
#   ✅ Tickets impresos: 42
#   📥 Archivos sincronizados: 42
#   ❌ Errores de impresión: 0
#   🔌 Errores de conexión: 3
```

### Dashboard (Futuro)

```python
# TODO: Crear endpoint GET /api/impresion/stats
# Que retorne estadísticas en tiempo real
# {
#   "tickets_procesados": 42,
#   "ultima_actualizacion": "2024-06-23T14:30:00Z",
#   "estado": "conectado",
#   "impresora": "Epson TM-T20II"
# }
```

## 🔒 Seguridad

### HTTPS en Producción

```python
# Si usas HTTPS, configure SSL:
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
session.verify = False  # Solo para desarrollo

# En producción:
session.verify = True  # Validar certificado
```

### Credenciales

El agente actualmente **no usa autenticación** en el endpoint `/api/impresion/siguiente`.

Para agregar seguridad:

```python
# Opción 1: Usar sesión autenticada (cookies)
# session.post("/api/login", json={"usuario": "...", "password": "..."})

# Opción 2: Bearer token
# headers = {"Authorization": f"Bearer {token}"}
# session.get("/api/impresion/siguiente", headers=headers)

# Opción 3: API Key
# headers = {"X-API-Key": os.getenv("PRINTER_API_KEY")}
```

## 📚 Desarrollo

### Estructura de clases

```python
class AgenteImpresion:
    - __init__(url_base, carpeta)
    - verificar_conexion() → bool
    - consultar_tickets() → dict | None
    - imprimir_ticket(b64) → bool
    - descargar_excel(nombre) → bool
    - procesar_ticket(datos) → bool
    - mostrar_estadisticas()
    - iniciar()  # Ciclo principal
```

### Extensiones futuras

```python
# TODO: Agregar autenticación
# TODO: Agregar reintentos inteligentes
# TODO: Agregar soporte para múltiples impresoras
# TODO: Agregar caché de archivos descargados
# TODO: Agregar notificaciones por email/webhook
# TODO: Crear dashboard web de monitoreo
```

## 📞 Contacto y Soporte

- Reportar bugs en: GitHub Issues
- Documentación: [README.md](README.md)
- Servidor: [web/app.py](web/app.py)

---

**Última actualización:** 2026-07-01  
**Versión:** 1.0  
**Estado:** ✅ Producción
