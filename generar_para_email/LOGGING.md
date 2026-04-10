# Sistema de Logging Centralizado

## Descripción

El sistema de logging centralizado está configurado en el módulo `src/settings.py`. Se ejecuta automáticamente al importar el módulo settings en la aplicación, creando logs estructurados en consola y archivo.

## Configuración

Todas las configuraciones se manejan a través de variables en el archivo `.env`:

```env
# Nivel de logging: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)
LOG_LEVEL=INFO

# Archivo de log (relativo a generar_para_email/ o ruta absoluta)
LOG_FILE=logs/app.log

# Tamaño máximo del archivo de log antes de rotación, en bytes (default: 5242880 = 5MB)
LOG_MAX_BYTES=5242880

# Cantidad de archivos de log rotados a mantener (default: 5)
LOG_BACKUP_COUNT=5

# Ruta del contador de facturas (opcional).
# Si es relativa, se resuelve desde generar_para_email/.
# Si no se define, usa: data/contador_facturas.json
CONTADOR_PATH=data/contador_facturas.json
```

## Niveles de Logging

- **DEBUG**: Información detallada para diagnóstico (rutas, valores de configuración)
- **INFO**: Mensajes informativos normales (facturas generadas, inicialización)
- **WARNING**: Advertencias para situaciones anómalas pero no críticas
- **ERROR**: Errores que requieren atención inmediata
- **CRITICAL**: Fallos graves que detienen la aplicación

## Formato de Logs

```
[AAAA-MM-DD HH:MM:SS] [NIVEL----] [módulo:función:línea] Mensaje
```

Ejemplo:
```
[2026-04-08 10:15:32] [INFO    ] [factura_writer:generar_factura_xlsx:258] Factura 2026-004 generada exitosamente en: /home/ibardev/Development/zoo_picasso/generar_para_email/facturas/factura_2026_004.xlsx
```

## Ubicación de Logs

- **Consola (stderr)**: Todos los niveles >= LOG_LEVEL
- **Archivo (logs/app.log)**: Todos los niveles >= DEBUG (para máxima detalle en archivo)

Los archivos se rotan automáticamente:
- Se crea un nuevo `app.log` cuando el archivo alcanza LOG_MAX_BYTES
- Los archivos antiguos se renombran a `app.log.1`, `app.log.2`, etc.
- Se mantienen los últimos LOG_BACKUP_COUNT archivos

## Cómo usar en módulos

Cada módulo debe importar y usar el logger de la siguiente forma:

```python
import logging

logger = logging.getLogger(__name__)

# Usar en el código:
logger.info(f"Operación completada: {valor}")
logger.warning(f"Situación anómala detectada: {situacion}")
logger.error(f"Error crítico: {error}", exc_info=True)
```

El módulo `src/settings.py` se importa automáticamente en `main.py`, configurando el logging centralizado.

## Puntos Críticos Documentados

Cada módulo documenta sus puntos de fallo en comentario al inicio:

### factura_counter.py
- Archivo contador corrupto o inaccesible
- Permisos insuficientes para escribir en `data/`
- Concurrencia: dos procesos leyendo/escribiendo simultáneamente

### factura_writer.py
- Permisos insuficientes para escribir en RUTA_FACTURAS
- RUTA_FACTURAS_PRINCIPAL no configurada o ruta inválida
- Copia a Windows Documents falla silenciosamente con WARNING
- openpyxl genera excepciones si los estilos son inválidos
- Memoria insuficiente para generar archivos

## Ejemplos de Debugging

### Cambiar nivel a DEBUG para máxima verbosidad:
```env
LOG_LEVEL=DEBUG
```

### Monitorear el archivo de log en tiempo real (Linux/Mac):
```bash
tail -f generar_para_email/logs/app.log
```

### Monitorear el archivo de log en tiempo real (Windows):
```powershell
Get-Content -Path "generar_para_email/logs/app.log" -Wait
```

### Buscar errores en el log:
```bash
grep "ERROR\|CRÍTICO" generar_para_email/logs/app.log
```

### Revisar últimas 50 líneas del log:
```bash
tail -50 generar_para_email/logs/app.log
```

## Interpretación de Mensajes Comunes

| Mensaje | Significado | Acción |
|---------|-----------|--------|
| `CRÍTICO: No se pudo acceder al directorio del contador` | Permisos de archivo o ruta inválida | Verificar permisos en `data/` |
| `CRÍTICO: Archivo contador corrupto` | JSON inválido en contador | Restaurar desde backup o eliminar |
| `WARNING: No se pudo copiar factura a Documents` | Sin permisos en carpeta Windows | Verificar permisos en Documents |
| `CRÍTICO: No se puede crear directorio de facturas` | Sin permisos para crear carpeta | Verificar permisos de la ruta |
| `Factura AAAA-NNN generada exitosamente` | Todo OK | No requiere acción |

## Integración con Otros Servicios

El archivo de log en `logs/app.log` puede ser monitoreado por:
- Herramientas de monitoreo (Sentry, ELK Stack, Datadog)
- Scripts de alertas que busquen palabras clave "ERROR" o "CRÍTICO"
- Análisis de logs para tendencias de fallos

## Limpieza de Logs Antiguos

Los archivos rotados se mantienen automáticamente. Para limpiar manualmente:

```bash
rm generar_para_email/logs/app.log.*
```

No eliminar `app.log` en ejecución (el archivo seguirá escribiendo).
