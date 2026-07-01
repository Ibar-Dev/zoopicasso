# Agente de Impresión - Guía de Inicio Rápido

## 🚀 Inicio en 5 Minutos

### Windows

```batch
REM 1. Descargar proyecto
git clone https://github.com/Ibar-Dev/zoopicasso.git
cd zoopicasso\generar_para_email

REM 2. Ejecutar instalador
install_local_agent.bat

REM 3. El agente empezará a consultar por tickets
```

### Linux/Mac

```bash
# 1. Descargar proyecto
git clone https://github.com/Ibar-Dev/zoopicasso.git
cd zoopicasso/generar_para_email

# 2. Dar permisos y ejecutar
chmod +x install_local_agent.sh
./install_local_agent.sh

# 3. El agente empezará a consultar por tickets
```

## ✅ Verificar que funciona

```bash
# Ejecutar test de verificación
python test_printer_agent.py

# Debería mostrar:
# ✓ TODOS LOS TESTS PASARON
```

## 📍 Configuración Personalizada

### Cambiar servidor (Producción)

```bash
# Windows
set PRINTER_SERVER_URL=https://zoopicasso.onrender.com
python poll_and_print.py

# Linux/Mac
export PRINTER_SERVER_URL=https://zoopicasso.onrender.com
python poll_and_print.py
```

### Cambiar carpeta de tickets

```bash
# Windows
set TICKETS_FOLDER=D:/Mi_Carpeta_Tickets/
python poll_and_print.py

# Linux/Mac
export TICKETS_FOLDER=/home/usuario/tickets/
python poll_and_print.py
```

## 📚 Documentación Completa

Ver [POLL_AND_PRINT_README.md](POLL_AND_PRINT_README.md)

## 🐛 Troubleshooting

### "No se encuentra Python"
- Windows: Reinstala Python desde https://python.org y marca "Add to PATH"
- Linux: `sudo apt-get install python3`
- Mac: `brew install python3`

### "Impresora no conectada"
```python
# Ver impresoras disponibles
python -c "from src.printer import listar_impresoras_usb; print(listar_impresoras_usb())"
```

### "No hay conexión con servidor"
```bash
# Verificar que servidor está corriendo
curl http://localhost:8000/api/health
```

### Ver logs
```bash
# Windows
type C:\Facturas_Tickets\poll_and_print.log

# Linux/Mac
tail -f ~/Facturas_Tickets/poll_and_print.log
```

## 📊 Cómo Funciona

```
┌──────────────────────────┐
│   Cliente Web (Render)   │  Genera factura + ticket
│   POST /api/generar      │
└────────────┬─────────────┘
             │
             ↓ Enqueues ticket
┌──────────────────────────┐
│  Cola Persistente        │  data/cola_impresion.json
│  tickets_pendientes[]    │
└────────────┬─────────────┘
             │
             ↓ Consulta cada 3s
┌──────────────────────────┐
│   Agente Local (Windows) │  poll_and_print.py
│   GET /api/impresion/... │
└────────────┬─────────────┘
             │
             ├─ Imprime en USB
             └─ Descarga Excel
```

## 📝 Logs

Los logs se guardan en:
- Windows: `C:\Facturas_Tickets\poll_and_print.log`
- Linux/Mac: `$HOME/Facturas_Tickets/poll_and_print.log`

Ejemplo:
```
2024-06-23 14:30:15 [INFO] ✅ Conexión verificada
2024-06-23 14:30:23 [INFO] ✅ Ticket impreso en Epson TM-T20II
2024-06-23 14:30:24 [INFO] ✅ Excel guardado: factura_2024_001.xlsx
```

## 🔒 Seguridad

- El endpoint `/api/impresion/siguiente` actualmente NO requiere autenticación
- Para producción, considera agregar protección

## 🆘 Soporte

1. Revisar logs en `TICKETS_FOLDER/poll_and_print.log`
2. Ejecutar `python test_printer_agent.py`
3. Consultar [POLL_AND_PRINT_README.md](POLL_AND_PRINT_README.md)

---

**Próximo paso:** Ver [POLL_AND_PRINT_README.md](POLL_AND_PRINT_README.md) para documentación completa
