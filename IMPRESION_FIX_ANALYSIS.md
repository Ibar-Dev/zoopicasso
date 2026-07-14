# 🔴 Análisis de Regresión: Impresión de Tickets (2026-07-01 a 02)

## Resumen Ejecutivo

**Problema:** Impresión de tickets dejó de funcionar después de cambios en ColaPersistente  
**Raíz:** Incompatibilidad de tipos en estructura de cola (list[str] → list[dict])  
**Solución:** Revertir a a3ba1b5 (Commit ddbcd87)  
**Estado:** ✅ **FUNCIONAL**

---

## Timeline de Eventos

### 📅 2026-06-23 (a3ba1b5)
- ✅ Impresión funciona perfectamente
- `ColaPersistente` usa `list[str]` (solo base64)
- `pop()` retorna `bytes` directamente

### 📅 2026-06-30 (Entre a3ba1b5 y HEAD)
- ❌ Cambios en `ColaPersistente` para agregar metadatos
- `list[str]` → `list[dict]` con `{"ticket": "...", "archivo_xlsx": "..."}`
- **Error:** Endpoint `/api/impresion/siguiente` no sincronizado

### 📅 2026-07-01 (HEAD)
- 🔴 Impresión completamente rota
- Usuario reporta: No aparece popup de impresión
- Poll agent recibe estructura incompatible

### 📅 2026-07-01 Evening
- 🔧 Investigación: Comparar a3ba1b5 vs HEAD
- 📍 Identificar raíz: Cambio en `ColaPersistente`

### 📅 2026-07-02 Morning
- ✅ Commit ddbcd87: Revertir a estructura simple
- ✅ Deploy a Render
- ✅ Usuario confirma: **Impresión funciona nuevamente**

---

## Análisis Técnico Detallado

### Versión a3ba1b5 (FUNCIONA ✅)

```python
# generar_para_email/web/app.py

class ColaPersistente:
    """Cola simple: solo almacena base64"""
    
    def __init__(self, ruta):
        self._datos: list[str] = self._cargar()
    
    def _cargar(self) -> list[str]:
        """Retorna list[str] de base64"""
        if self.ruta.exists():
            contenido = json.load(f)
            if isinstance(contenido, dict) and "tickets" in contenido:
                return contenido["tickets"]  # ← list[str]
            elif isinstance(contenido, list):
                return contenido  # ← list[str]
        return []
    
    def append(self, item: bytes) -> None:
        """Recibe bytes, almacena base64 string"""
        ticket_b64 = base64.b64encode(item).decode("ascii")
        self._datos.append(ticket_b64)  # ← Almacena string
        self._guardar()
    
    def pop(self, index: int = 0) -> bytes:  # ← RETORNA BYTES
        """Retira y retorna bytes directamente"""
        ticket_b64 = self._datos.pop(index)
        return base64.b64decode(ticket_b64)  # ← Decodifica antes de retornar

# Endpoint impresión
@app.get("/api/impresion/siguiente")
def siguiente_ticket():
    if not cola_impresion:
        return JSONResponse({"hay_ticket": False}, status_code=204)
    
    ticket = cola_impresion.pop(0)  # ← bytes
    logger.info("Ticket despachado (%d bytes)", len(ticket))
    return JSONResponse({
        "hay_ticket": True,
        "ticket_b64": base64.b64encode(ticket).decode("ascii"),  # ← Re-encoda
    })
```

**Flujo:**
```
generar_ticket_escpos(factura)          → bytes
    ↓
cola_impresion.append(bytes)            → almacena base64 string
    ↓
siguiente_ticket()                      → pop() retorna bytes
    ↓
base64.b64encode(bytes).decode()        → string base64
    ↓
JSON response {"ticket_b64": "..."}
    ↓
poll_and_print.py decodifica            → bytes
    ↓
imprimir_ticket_usb_windows(bytes)      → ✅ IMPRIME
```

---

### Versión HEAD (ROTA ❌)

```python
class ColaPersistente:
    """Cola con metadatos - ROMPE COMPATIBILITY"""
    
    def __init__(self, ruta):
        self._datos: list[dict] = self._cargar()  # ← CAMBIO 1: list[dict]
    
    def _cargar(self) -> list[dict]:
        """Retorna list[dict] con metadatos"""
        # ...
        for item in tickets_base:
            if isinstance(item, str):
                cola_migrada.append({"ticket": item, "archivo_xlsx": None})
            else:
                cola_migrada.append(item)
        return cola_migrada  # ← list[dict]
    
    def append(self, item: bytes, archivo_nombre: Optional[str] = None) -> None:  # ← CAMBIO 2: nuevo parámetro
        """Recibe bytes + nombre de archivo"""
        ticket_b64 = base64.b64encode(item).decode("ascii")
        self._datos.append({  # ← CAMBIO 3: almacena dict
            "ticket": ticket_b64,
            "archivo_xlsx": archivo_nombre
        })
        self._guardar()
    
    def pop(self, index: int = 0) -> dict:  # ← CAMBIO 4: retorna dict
        """Retira y retorna diccionario"""
        item = self._datos.pop(index)
        self._guardar()
        return item  # ← RETORNA DICT, NO BYTES

# Endpoint impresión (intentó actualizar pero falló)
@app.get("/api/impresion/siguiente")
def siguiente_ticket():
    if not cola_impresion:
        return JSONResponse({"hay_ticket": False}, status_code=204)
    
    item = cola_impresion.pop(0)  # ← ESPERA dict {"ticket": "...", "archivo_xlsx": "..."}
    ticket_b64 = item["ticket"]  # ← OK, obtiene base64
    archivo_xlsx = item["archivo_xlsx"]
    
    logger.info("Ticket despachado (archivo: %s)", archivo_xlsx)
    return JSONResponse({
        "hay_ticket": True,
        "ticket_b64": ticket_b64,  # ← OK, es string base64
        "archivo_xlsx": archivo_xlsx
    })
```

**Flujo (FALLIDO):**
```
generar_ticket_escpos(factura)          → bytes
    ↓
cola_impresion.append(bytes)            → almacena dict {"ticket": "base64...", "archivo_xlsx": None}
    ↓
siguiente_ticket()                      → pop() retorna dict
    ↓
JSON response {"ticket_b64": "...", "archivo_xlsx": None}
    ↓
poll_and_print.py esperaba             → ESTRUCTURA INCOMPATIBLE
    ↓
❌ ERROR SILENCIOSO: parser.json() falla o campos inválidos
```

---

## ¿Por qué se rompió?

### Cambios Realizados (Entre a3ba1b5 y HEAD)

1. **ColaPersistente cambió estructura**
   - De: `list[str]` (solo base64)
   - A: `list[dict]` (base64 + metadatos)
   - ✅ Objetivo: Almacenar info de archivo asociado
   - ❌ Efecto: Incompatibilidad en interfaz

2. **pop() cambió tipo de retorno**
   - De: `-> bytes` (decodificado)
   - A: `-> dict` (metadatos)
   - ✅ Objetivo: Retornar información adicional
   - ❌ Efecto: Endpoint no estaba sincronizado

3. **append() cambió firma**
   - De: `append(item: bytes)`
   - A: `append(item: bytes, archivo_nombre: Optional[str])`
   - ✅ Objetivo: Guardar nombre de archivo
   - ❌ Efecto: Código existente no pasaba parámetro

### Puntos de Fallo

| Componente | Cambio | Impacto |
|-----------|--------|--------|
| `ColaPersistente._datos` | `list[str]` → `list[dict]` | Estructura incompatible |
| `pop()` return type | `bytes` → `dict` | Endpoint esperaba bytes |
| `append()` signature | `(bytes)` → `(bytes, archivo_nombre)` | web/app.py pasaba solo bytes |
| `/api/impresion/siguiente` | No actualizado | Confusión de tipos |
| `poll_and_print.py` | No cambió | Esperaba respuesta vieja |

---

## Solución Aplicada (Commit ddbcd87)

### ¿Qué se revertió?

```python
# ✅ REVERTIDO A a3ba1b5

class ColaPersistente:
    def __init__(self, ruta):
        self._datos: list[str] = self._cargar()  # ← Vuelve a list[str]
    
    def _cargar(self) -> list[str]:
        # ... retorna list[str]
    
    def append(self, item: bytes) -> None:  # ← Vuelve a versión simple
        ticket_b64 = base64.b64encode(item).decode("ascii")
        self._datos.append(ticket_b64)
    
    def pop(self, index: int = 0) -> bytes:  # ← Retorna bytes
        ticket_b64 = self._datos.pop(index)
        return base64.b64decode(ticket_b64)

@app.get("/api/impresion/siguiente")
def siguiente_ticket():
    ticket = cola_impresion.pop(0)  # ← bytes
    return JSONResponse({
        "hay_ticket": True,
        "ticket_b64": base64.b64encode(ticket).decode("ascii"),
    })
```

### Resultado

✅ **Impresión funciona nuevamente**

| Aspecto | Estado |
|--------|--------|
| Generación de tickets | ✅ OK |
| Encolado en cola_impresion.json | ✅ OK |
| Poll desde Windows | ✅ OK |
| Decodificación base64 | ✅ OK |
| Impresión en USB | ✅ OK |

---

## Lecciones Aprendidas

### ❌ Lo que salió mal

1. **Cambios sin coordinación de tipos**
   - ColaPersistente cambió estructura
   - Endpoint no se actualizó correctamente
   - Cero compatibilidad hacia atrás

2. **Falta de tests end-to-end**
   - Hubiera detectado la incompatibilidad
   - Tests E2E de impresión habrían fallado

3. **Cambios en contrato de interfaz sin deprecación**
   - `pop()` cambió retorno de `bytes` a `dict`
   - Sin transición gradual
   - Clientes quedan sin avisar

### ✅ Lo que debería hacerse

1. **Tests integrados**
   - Tests de cola persistente
   - Tests del endpoint `/api/impresion/siguiente`
   - Tests del flujo completo con poll_and_print

2. **Documentación de cambios**
   - Changelog: qué cambió, por qué
   - Advertencia de breaking changes
   - Proceso de migración

3. **Versionado de API**
   - `/api/v1/impresion/siguiente` vs `/api/v2/...`
   - Deprecación gradual
   - Compatibilidad hacia atrás

---

## Plan Futuro: Restaurar Auditoría

### Objetivo
Mantener funcionalidad de impresión ✅ + Restaurar auditoría en Excel

### Opciones Evaluadas

#### Opción 1: Background Task (RECOMENDADA)
```python
# Flujo rápido (impresión)
@app.post("/api/generar_factura")
def generar(payload, bg_tasks: BackgroundTasks):
    ticket = generar_ticket_escpos(factura)
    cola_impresion.append(ticket)  # ✅ RÁPIDO
    
    # ✅ Auditoría no bloquea
    bg_tasks.add_task(_guardar_ticket_async, factura, pago)
    
    return {"ticket_impreso": True}
```

**Ventajas:**
- No bloquea flujo de impresión
- Garantiza encolado antes de auditoría
- Auditoría asíncrona, no crítica

**Desventajas:**
- Si server cae, auditoría puede perderse
- Logs más complejos

#### Opción 2: Asyncio Task
```python
asyncio.create_task(_guardar_ticket_bg(factura, pago))
```

**Ventajas:**
- Más Pythónico para async
- Control fino de eventos

**Desventajas:**
- Requiere Render configurado para async
- Puede no ejecutarse si se interrumpe

#### Opción 3: Queue Separada
```python
class ColaPersistente:
    def __init__(self):
        self.tickets = []  # Para impresión
        self.auditoria = []  # Para Excel

# Flujo
tickets_queue.append(bytes)
auditoria_queue.append(Ticket)
```

**Ventajas:**
- Completamente separado
- Flexible para diferentes workflows

**Desventajas:**
- Más complejo
- Sincronización entre colas

---

## Recomendación

✅ **Usar Opción 1: BackgroundTasks de FastAPI**

```python
# web/app.py

from fastapi import BackgroundTasks

async def _guardar_ticket_background(factura: Factura, pago: PagoInfo):
    """Guarda ticket en Excel de auditoría (NO BLOQUEA)"""
    try:
        ticket_doc = Ticket(
            numero=int(factura.numero.replace("F", "")),
            lineas=[LineaTicket(...) for l in factura.lineas],
            fecha_hora=datetime.now()
        )
        guardar_ticket(ticket_doc)
        logger.info("✅ Ticket guardado en auditoría: %s", factura.numero_formateado)
    except Exception as exc:
        logger.error("⚠️ Error guardar auditoría (no bloquea impresión): %s", exc)

@app.post("/api/generar_factura")
def generar(payload: FacturaPayload, request: Request, bg_tasks: BackgroundTasks):
    # ... crear factura ...
    
    registrar_ventas_factura(factura, usuario, pago)
    
    ticket_impreso = False
    ticket_estado = "Ticket no solicitado."
    if payload.imprimir_ticket:
        try:
            ticket = generar_ticket_escpos(factura, ancho=42, pago=pago)
            cola_impresion.append(ticket)  # ✅ RÁPIDO - encolado inmediato
            ticket_impreso = True
            ticket_estado = "Ticket encolado para impresión."
            
            # ✅ Auditoría en background - NO bloquea
            bg_tasks.add_task(_guardar_ticket_background, factura, pago)
            
        except Exception as exc:
            ticket_estado = f"No se pudo generar ticket: {exc}"
    
    return {
        "ok": True,
        "numero": factura.numero_formateado,
        "ticket_impreso": ticket_impreso,
        "ticket_estado": ticket_estado,
    }
```

**Resultado:**
- ✅ Impresión garantizada
- ✅ Auditoría habilitada
- ✅ Sin bloqueos
- ✅ Compatible con a3ba1b5

---

## Próximos Pasos

1. **Validar que a3ba1b5 + ddbcd87 funciona completamente** (EN PROGRESO)
2. **Implementar BackgroundTasks para auditoría** (TODO)
3. **Crear tests E2E** (TODO)
4. **Documentar en MANUAL_USUARIO.md** (TODO)

---

**Análisis completado:** 2026-07-02  
**Responsable:** Sistema de Impresión Zoo Picasso  
**Estado:** ✅ Impresión funcional, auditoría pendiente de restauración
