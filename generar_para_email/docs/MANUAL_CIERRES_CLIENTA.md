# GUÍA DE CIERRES DE GANANCIAS
## Zoo Picasso - Manual para Operadores y Gerentes

---

## INTRODUCCIÓN: ¿QUÉ ES UN CIERRE?

Un **cierre** es un reporte que registra el dinero que Zoo Picasso ganó en un período específico. 

Cada cierre:
- **Calcula** el total de dinero recaudado
- **Organiza** las ganancias por tipo de animal (perro, gato, ave, etc.)
- **Genera un archivo Excel** que puedes guardar o imprimir
- **Registra quién hizo el cierre** y cuándo

Los cierres sirven para:
✅ Control diario: Saber cuánto ganamos en la mañana vs. tarde  
✅ Auditoría: Tener registro de todas las transacciones  
✅ Cierre contable: Finalizar el mes y preparar el siguiente  

---

## LOS 4 TIPOS DE CIERRES

### 📊 TABLA COMPARATIVA

| **Tipo** | **Horario** | **Se puede repetir?** | **¿Archiva datos?** | **Requiere otro cierre?** |
|----------|-------------|----------------------|-------------------|---------------------------|
| 🌅 **Mañana** | 06:00 - 14:00 | ❌ Solo 1x/día | ❌ NO | ❌ Ninguno |
| 🌆 **Tarde** | 14:00 - 22:00 | ❌ Solo 1x/día | ❌ NO | ✅ Cierre Mañana |
| 🌞 **Día Completo** | 06:00 - 22:00 | ❌ Solo 1x/día | ❌ NO | ✅ Mañana + Tarde |
| 📋 **Mensual** | Mes entero | ❌ Solo 1x/mes | ✅ **SÍ (PERMANENTE)** | ❌ Ninguno |

---

### DIFERENCIA CLAVE: CIERRES DIARIOS vs CIERRE MENSUAL

#### 🔵 CIERRES DIARIOS (Mañana, Tarde, Día Completo)
- Son **informativos**: Solo generan un Excel, no modifican datos
- **Se pueden repetir** varias veces durante el día si necesitas revisar
- **NO archivan nada**: Los datos siguen siendo "activos"
- Útiles para **control turno a turno**

#### 🔴 CIERRE MENSUAL
- Es **definitivo e irreversible**: Una sola vez por mes
- **ARCHIVA PERMANENTEMENTE** todas las ventas del mes
- **NO se puede deshacer**: Es la acción más importante del mes
- Necesaria para **cerrar contabilidad del mes**

---

## ¿POR QUÉ SOLO ARCHIVAMOS EN CIERRE MENSUAL?

### La Razón: Necesitamos Consolidar Datos

**Si archiváramos en cierres diarios, la lógica se rompería.**

```
Escenario problemático:
├─ 14:00: Haces Cierre Mañana → Archiva facturas 6-14h ❌
├─ 22:00: Intentas Cierre Tarde
│         Pero... ¿qué datos archiva si los de mañana ya están archivados?
└─ 23:00: Intentas Cierre Día Completo
          Pero... ¿cómo consolida mañana + tarde si ambos están archivados?
```

### La Solución Correcta: Archivar Solo al Final del Mes

```
Proceso correcto:
├─ Día 1-30: Todos los cierres (mañana, tarde, día) usan DATOS ACTIVOS
│            Se generan Excel informativos, pero NO se archiva
│            Los datos siguen "activos" para consolidaciones
│
├─ Día 30: Se hace CIERRE MENSUAL
│          En ese momento, TODOS los datos del mes se archivan de una vez
│          Los datos pasan de "activos" a "archivados"
│
└─ Día 1 (Mes siguiente): Sistema limpio, listo para nuevo mes
```

### Analogía: Control de Caja

```
🌅 Cierre de Mañana  → Como contar la caja al mediodía
                       (Documentas cuánto hay, pero el dinero sigue en la caja)

🌆 Cierre de Tarde   → Como contar la caja al anochecer
                       (Documentas cuánto hay, pero el dinero sigue en la caja)

📋 Cierre Mensual    → Como hacer el depósito al banco
                       (AHORA sí, sacas todo de la caja = ARCHIVAS)
                       (A partir de ahora, el dinero está en el banco = ARCHIVADO)
```

### ¿Dónde Quedan los Datos Mientras Tanto?

**Buena noticia:** Los datos están completamente seguros.

- 📁 **Ubicación:** Base de datos en disco del servidor
- 🔒 **Seguridad:** Persistente, no se pierden aunque el servidor se reinicie
- ✅ **Acceso:** Disponibles para todos los cierres hasta cierre mensual
- 🌐 **Incluso si el servidor se cierra:** Los datos siguen en disco, se recuperan al reiniciar

**Ejemplo real:**
```
Día 1-15: Generas facturas, sistema funciona
Día 16: El servidor se cierra por inactividad
        ¿Se pierden datos del 1-15? NO ✅
Día 17: Vuelves a conectarte, el servidor se reinicia
        ¿Aparecen datos del 1-15? SÍ, intactos ✅
Día 30: Haces cierre mensual
        Archiva TODAS las facturas, incluidas las del 1-15 ✅
```

---

## FLUJO VISUAL DE CIERRES

```
┌─────────────────────────────────────────────────────────┐
│                    DURANTE EL DÍA                      │
│                                                         │
│  Mañana (6-14h)                                         │
│  ├─ Opción: Hacer cierre de mañana                      │
│  │  (genera Excel, dinero mañana: $450.75)              │
│  │                                                      │
│  └─ Sin este cierre, NO puedes hacer cierre de tarde    │
│                                                         │
│  Tarde (14-22h)                                         │
│  ├─ Opción: Hacer cierre de tarde                       │
│  │  (genera Excel, dinero tarde: $520.50)               │
│  │  ⚠️  REQUIERE: Cierre mañana ya hecho                 │
│  │                                                      │
│  └─ Sin este cierre, NO puedes hacer día completo       │
│                                                         │
│  Final del Día                                          │
│  └─ Opción: Hacer cierre día completo                   │
│     (genera Excel, TOTAL: $971.25)                      │
│     ⚠️  REQUIERE: AMBOS cierres (mañana + tarde)         │
│                                                         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                    FIN DEL MES                          │
│                                                         │
│  En cualquier momento del mes...                        │
│  └─ Opción: Hacer cierre mensual                        │
│     (ARCHIVA todo, data limpia para mes nuevo)          │
│     ⚠️  ADVERTENCIA: NO SE PUEDE DESHACER               │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## PASO A PASO: CIERRE DE MAÑANA 🌅

### CUÁNDO HACERLO
Después de completar el turno de la mañana (alrededor de las 2:00 PM), haz el cierre de mañana.

### PASOS EXACTOS

**1. Ingresa a la sección "Cierres"**
   - En la interfaz principal de Zoo Picasso
   - Busca la sección o menú llamado "Cierres" o "Ganancias"

**2. Haz clic en el botón "Cierre de Mañana"**
   - Aparecerá un resumen de los datos:
     - Total dinero recolectado en la mañana
     - Cantidad de facturas/atenciones
     - Dinero por cada tipo de animal (perro, gato, ave, etc.)

**3. Revisa los números**
   - ¿Se ven correctos?
   - ¿Coinciden con lo que esperabas?
   - Si hay error, contacta al administrador

**4. Confirma con "Descargar Excel"**
   - El archivo se descarga automáticamente
   - Nombre: `cierre_diario_2026_06_15.xlsx`

**5. Archivo guardado**
   - Aparecerá en tu carpeta "Descargas"
   - Puedes abrirlo, revisar o imprimir

### EJEMPLO PRÁCTICO

```
Mañana en Zoo Picasso - 15 de Junio

Facturas registradas:
├─ Factura #1: Baño perro = $45.00
├─ Factura #2: Corte gato = $35.50
├─ Factura #3: Baño 2 perros = $80.00
├─ Factura #4: Vacuna ave = $55.00
├─ ... (9 facturas más)
└─ Total: 12 facturas

CIERRE DE MAÑANA GENERA:
├─ Total dinero: $450.75
├─ Cantidad facturas: 12
└─ Desglose:
   ├─ Perros: $200.00
   ├─ Gatos: $100.50
   ├─ Aves: $150.25
   └─ Otros: $0.00
```

### QUÉ CAMBIA Y QUÉ NO CAMBIA

✅ **Lo que SÍ pasa:**
- Se genera un Excel con los datos
- Se registra en el sistema que hiciste cierre de mañana

❌ **Lo que NO pasa:**
- Los datos NO se modifican
- Las facturas siguen siendo "activas"
- Puedes seguir generando nuevas facturas
- El dinero sigue disponible para cierre de tarde

### ⚠️ ADVERTENCIA
- **No puedes hacer cierre de mañana dos veces** en el mismo día
- Si intentas, el sistema te dirá: "Ya completaste el cierre de mañana hoy"

---

## PASO A PASO: CIERRE DE TARDE 🌆

### CUÁNDO HACERLO
Después de completar el turno de la tarde (alrededor de las 10:00 PM), haz el cierre de tarde.

### PASOS EXACTOS

**1. Ingresa a la sección "Cierres"**

**2. Haz clic en el botón "Cierre de Tarde"**
   - El sistema verifica automáticamente:
     - ¿Ya hiciste cierre de mañana? Si no → Error
     - ¿Ya hiciste cierre de tarde hoy? Si sí → Error

**3. Si todo está bien, verás el resumen de la tarde**
   - Total dinero recolectado en la tarde
   - Cantidad de facturas/atenciones
   - Dinero por cada tipo de animal

**4. Confirma con "Descargar Excel"**
   - El archivo se descarga automáticamente
   - Nombre: `cierre_diario_2026_06_15.xlsx` (mismo nombre que mañana)

**5. Archivo guardado**
   - Nuevamente en tu carpeta "Descargas"

### EJEMPLO PRÁCTICO

```
Tarde en Zoo Picasso - 15 de Junio

Facturas registradas (14:00 - 22:00):
├─ Factura #13: Baño perro = $50.00
├─ Factura #14: Consulta veterinaria ave = $95.00
├─ Factura #15: Corte gato + baño = $70.00
├─ Factura #16: Vacuna perro = $65.50
├─ ... (11 facturas más)
└─ Total: 15 facturas

CIERRE DE TARDE GENERA:
├─ Total dinero: $520.50
├─ Cantidad facturas: 15
└─ Desglose:
   ├─ Perros: $250.00
   ├─ Gatos: $120.00
   ├─ Aves: $150.50
   └─ Otros: $0.00
```

### ⚠️ REQUISITOS
**Antes de hacer cierre de tarde, OBLIGATORIAMENTE debes:**
1. ✅ Haber hecho cierre de mañana
2. ✅ Si no lo hiciste → El sistema te dirá: "Primero debes hacer el cierre de mañana"

### ⚠️ ADVERTENCIA
- **No puedes hacer cierre de tarde dos veces** en el mismo día
- **No puedes hacer cierre de tarde sin cierre de mañana**

---

## PASO A PASO: CIERRE DEL DÍA COMPLETO 🌞

### CUÁNDO HACERLO
Al final del día, después de completar AMBOS turnos (mañana y tarde), haz el cierre del día completo.

### PASOS EXACTOS

**1. Ingresa a la sección "Cierres"**

**2. Haz clic en el botón "Cierre del Día Completo"**
   - El sistema verifica automáticamente:
     - ¿Hiciste cierre de mañana? Si no → Error
     - ¿Hiciste cierre de tarde? Si no → Error
     - ¿Ya hiciste cierre de día completo? Si sí → Error

**3. Si todo está bien, verás el resumen del día COMPLETO**
   - Total dinero recolectado (mañana + tarde)
   - Cantidad total de facturas
   - Dinero por cada tipo de animal

**4. Confirma con "Descargar Excel"**
   - El archivo se descarga automáticamente
   - Nombre: `cierre_diario_2026_06_15.xlsx`

**5. Archivo guardado**
   - En tu carpeta "Descargas"

### EJEMPLO PRÁCTICO

```
Día Completo en Zoo Picasso - 15 de Junio

CIERRE DE MAÑANA (06:00 - 14:00):
├─ Total: $450.75
└─ Facturas: 12

CIERRE DE TARDE (14:00 - 22:00):
├─ Total: $520.50
└─ Facturas: 15

CIERRE DEL DÍA COMPLETO GENERA:
├─ Total dinero: $971.25 (450.75 + 520.50)
├─ Cantidad facturas: 27 (12 + 15)
└─ Desglose:
   ├─ Perros: $450.00
   ├─ Gatos: $220.50
   ├─ Aves: $300.75
   └─ Otros: $0.00
```

### VENTAJA DEL CIERRE DÍA COMPLETO
En vez de tener 2 Excel separados (uno de mañana, uno de tarde), tienes 1 solo Excel con TODO consolidado. Más fácil para auditoría.

### ⚠️ REQUISITOS
**Antes de hacer cierre día completo, OBLIGATORIAMENTE debes:**
1. ✅ Haber hecho cierre de mañana
2. ✅ Haber hecho cierre de tarde
3. ✅ Si falta cualquiera → El sistema te lo indicará

### ⚠️ ADVERTENCIA
- **No puedes hacer cierre de día completo dos veces** en el mismo día
- **No puedes hacer cierre de día completo sin AMBOS cierres (mañana + tarde)**

---

## PASO A PASO: CIERRE MENSUAL 📋

### ⚠️ ADVERTENCIA CRÍTICA

El cierre mensual es **PERMANENTE E IRREVERSIBLE**. 

Una vez que lo hagas:
- **NO se puede deshacer**
- **NO se puede volver atrás**
- Los datos se archivan para siempre

**Solo hazlo cuando estés 100% seguro de que el mes está cerrado contablemente.**

### CUÁNDO HACERLO
Al final del mes (últimos días), cuando ya no hay más facturas que generar y quieres "cerrar" ese mes para comenzar el siguiente.

### PASOS EXACTOS

**1. Ingresa a la sección "Cierres"**

**2. Busca el botón rojo "CIERRE MENSUAL"**
   - ⚠️ Está en rojo para destacar que es importante
   - A diferencia de los otros, este es diferente

**3. Haz clic en "CIERRE MENSUAL"**
   - Aparecerá una ventana de confirmación
   - Leerá algo como: "⚠️ Esta acción es IRREVERSIBLE. ¿Descargar Excel y archivar todas las ventas de JUNIO?"

**4. LEE CUIDADOSAMENTE la ventana**
   - ¿Está correctamente el mes? (ej: JUNIO)
   - ¿Es realmente el final del mes?
   - ¿No hay más facturas que registrar?

**5. Si estás completamente seguro, haz clic en "SÍ, CERRAR JUNIO"**
   - El sistema comienza el proceso
   - Genera un Excel con TODOS los datos del mes

**6. El Excel se descarga automáticamente**
   - Nombre: `cierre_mensual_2026_06.xlsx`
   - Contiene: Todas las facturas, total, desglose por animal

**7. Los datos se ARCHIVAN PERMANENTEMENTE**
   - Todas las facturas del mes pasan a "archivadas"
   - Ya no aparecen en el resumen diario
   - El acumulado del mes vuelve a $0.00

### EJEMPLO PRÁCTICO

```
JUNIO 2026 - Mes Completo en Zoo Picasso

Durante el mes se generaron:
├─ 1 de junio: 8 facturas = $350.00
├─ 2 de junio: 12 facturas = $520.75
├─ 3 de junio: 15 facturas = $620.50
├─ ... (27 días más)
└─ 30 de junio: 14 facturas = $480.00
   TOTAL MES: 47 facturas, $4,525.75

USUARIO HACE CIERRE MENSUAL

CIERRE MENSUAL GENERA:
├─ Total dinero archivado: $4,525.75
├─ Cantidad facturas archivadas: 47
├─ Desglose por animal:
│  ├─ Perros: $1,800.00
│  ├─ Gatos: $1,200.50
│  ├─ Aves: $1,200.00
│  └─ Reptiles: $325.25
└─ Período: Junio 2026

DESPUÉS DEL CIERRE:
├─ Resumen mes actual: $0.00 (todo archivado)
├─ Próximas facturas: Automáticamente para JULIO
└─ Datos archivados: Disponibles para auditoría
```

### QUÉ CAMBIA DESPUÉS DEL CIERRE MENSUAL

| Aspecto | Antes | Después |
|---------|--------|---------|
| Resumen Junio | $4,525.75 | $0.00 |
| Cantidad facturas activas | 47 | 0 |
| Excel disponible | Sí | Sí (descargado) |
| Se puede repetir | N/A | ❌ NO |
| Datos se pierden | N/A | ❌ NO (archivados) |
| Mes siguiente | N/A | 📅 Julio comienza limpio |

### EJEMPLO: ¿QUÉ PASA CON LOS DATOS ARCHIVADOS?

**Antes del cierre (estado activo):**
```
Sistema muestra:
├─ Resumen mes: $4,525.75
├─ Facturas activas: 47
└─ Dinero disponible: $4,525.75
```

**Después del cierre (estado archivado):**
```
Sistema muestra:
├─ Resumen mes: $0.00 (ya no aparecen activas)
├─ Facturas activas: 0
├─ Dinero disponible: $0.00
│
├─ PERO en historial/auditoría:
│  └─ Todas las 47 facturas están archivadas
│     y vinculadas al cierre mensual
│     (no se pierden, solo cambian de estado)
```

---

## PREGUNTAS FRECUENTES

### P: ¿Puedo hacer cierre de tarde sin hacer cierre de mañana?
**R:** No. Si intentas, el sistema te dirá: "Primero debes hacer el cierre de mañana". Es obligatorio en ese orden.

### P: ¿Puedo hacer cierre de mañana dos veces en el mismo día?
**R:** No. Solo una vez. Si intentas hacer cierre de mañana una segunda vez hoy, el sistema lo rechazará.

### P: ¿Qué pasa si me olvido de hacer un cierre diario?
**R:** Nada grave. Los cierres diarios (mañana, tarde, día completo) son **opcionales**. No pasa nada si no los haces. Lo importante es el cierre mensual.

### P: ¿Puedo deshacer un cierre mensual?
**R:** **NO**. Es permanente e irreversible. Una vez archivadas las facturas, no se pueden reactivar. Por eso antes de hacer cierre mensual debes estar 100% seguro.

### P: ¿Qué pasa si hago cierre mensual y luego llega una nueva factura de junio?
**R:** La nueva factura se registrará automáticamente como de JULIO (mes siguiente), no de junio. Por eso antes de cerrar mes debes asegurarte que ya no hay más facturas que registrar.

### P: ¿Dónde quedan los archivos Excel de cierres?
**R:** Se descargan automáticamente a tu carpeta "Descargas" del navegador. Puedes guardarlos en otra carpeta o imprimirlos si lo necesitas.

### P: ¿Qué pasa con el dinero archivado? ¿Se pierde?
**R:** No. Los datos se archivan pero siguen siendo accesibles. Se registra que fueron archivados el día X por el usuario Y. Es para auditoría y referencias futuras.

### P: ¿Puedo hacer cierre mensual en cualquier momento o solo el último día?
**R:** Puedes hacerlo en cualquier momento del mes. Pero la recomendación es hacerlo al final del mes, cuando no haya más facturas que registrar. Una vez que lo hagas, ese mes está "cerrado" y no puedes volver a cerrar de nuevo.

### P: ¿Qué pasa si hay un error en el cierre mensual?
**R:** Si algo sale mal durante el proceso (error de sistema, disco lleno, etc.), el cierre se cancela automáticamente y los datos NO se modifican. Puedes reintentar. No hay riesgo de datos corruptos.

### P: ¿Hay un límite de cierres mensuales?
**R:** Sí. Solo uno por mes. Junio tiene un cierre mensual. Julio tiene otro. No puedes hacer 2 cierres de junio.

---

## RESOLUCIÓN DE PROBLEMAS

### ❌ Error: "Ya completaste el cierre de mañana hoy"

**Causa:** Intentaste hacer cierre de mañana pero ya lo habías hecho.

**Solución:** 
- Es normal. Solo puedes hacer 1 cierre de mañana por día
- Si necesitas revisar los datos, ve al historial de cierres
- Continúa con cierre de tarde

---

### ❌ Error: "Primero debes hacer el cierre de mañana"

**Causa:** Intentaste hacer cierre de tarde pero aún no hiciste cierre de mañana.

**Solución:**
- Primero haz cierre de mañana
- Luego podrás hacer cierre de tarde
- El orden es obligatorio

---

### ❌ Error: "Descargar Excel no funciona"

**Causa:** Problema del navegador o bloqueador de descargas.

**Solución:**
- Verifica que tu navegador permita descargas
- Desactiva bloqueadores de publicidad temporalmente
- Intenta desde otro navegador
- Si persiste, contacta al administrador

---

### ❌ Error: "No hay ventas activas para cerrar"

**Causa:** Intentaste hacer cierre mensual pero no hay facturas en el mes.

**Solución:**
- Es un aviso. Significa que junio está vacío
- Puedes hacer el cierre igual (resultará en $0.00)
- Verifica la fecha del mes seleccionado

---

### ❌ Error: "Sistema no responde" durante cierre mensual

**Causa:** Problema de conexión o servidor lento.

**Solución:**
- **NO** cierres la ventana
- Espera a que se complete (puede tardar 1-2 minutos)
- Si sigue sin responder después de 5 minutos, contacta al administrador
- Los datos NO se pierden si hay un timeout

---

## BUENAS PRÁCTICAS

### ✅ DO (Haz esto)

✅ Haz cierre diario cada día (mañana + tarde + día completo)
- Ayuda a detectar errores rápido
- Facilita auditoría

✅ Revisa los números en cada cierre
- ¿Coinciden con tus registros?
- ¿Se ven razonables?

✅ Guarda/imprime los Excel de cierres
- Para referencias futuras
- Para auditoría

✅ Haz cierre mensual cuando estés completamente seguro
- Último día del mes
- Tras revisar todas las facturas
- Con otro gerente si es posible

✅ Contacta al administrador si hay dudas
- Mejor preguntar que equivocarse
- Especialmente antes de cierre mensual

---

### ❌ DON'T (No hagas esto)

❌ No hagas cierre mensual apurado
- Es irreversible, necesita cuidado

❌ No ignores los errores del sistema
- Si dice "error", investiga antes de reintentar

❌ No cierres el navegador durante un cierre mensual
- Aunque parezca que no está respondiendo, espera

❌ No pierdas los Excel de cierres
- Son datos importantes para auditoría

---

## RESUMEN VISUAL: FLUJO RECOMENDADO DIARIO

```
MAÑANA
│
└─→ 14:00 (fin turno) 
    │
    ├─ Hacer "Cierre de Mañana" ✅
    │  (genera Excel, total: $450.75)
    │
    └─ Guardar Excel en carpeta

TARDE
│
└─→ 22:00 (fin turno)
    │
    ├─ Hacer "Cierre de Tarde" ✅
    │  (requiere: cierre mañana hecho)
    │  (genera Excel, total: $520.50)
    │
    └─ Guardar Excel en carpeta

FINAL DEL DÍA
│
└─→ Antes de cerrar sistema
    │
    ├─ Opcional: Hacer "Cierre Día Completo" ✅
    │  (requiere: ambos cierres)
    │  (genera Excel consolidado: $971.25)
    │
    └─ Guardar Excel
       └─ Día terminado ✓

---

FIN DEL MES
│
└─→ 30 de junio
    │
    ├─ Revisar que no haya más facturas por registrar
    │
    ├─ Hacer "CIERRE MENSUAL" ⚠️
    │  (IRREVERSIBLE)
    │  (genera Excel final: $4,525.75)
    │
    ├─ Descargar y guardar Excel
    │
    ├─ Mes archivado permanentemente
    │
    └─ Julio comienza limpio (próximo mes)
```

---

## 🤖 AUTOMATIZACIÓN: CIERRES AUTOMÁTICOS

A partir de junio de 2026, **los cierres se hacen automáticamente** a horarios fijos cada día.

### Horarios de Cierres Automáticos

| Hora | Tipo de Cierre | Descripción |
|------|---|---|
| **14:00** | 🌅 Mañana | Calcula ventas de 06:00-14:00 automáticamente |
| **22:00** | 🌆 Tarde | Calcula ventas de 14:00-22:00 automáticamente |
| **22:05** | 🌞 Día Completo | Consolida mañana + tarde automáticamente |
| **22:00 (último día)** | 📋 Mes | Archiva todo el mes (último día a las 22:00) |

### ¿Dónde Ven los Cierres Automáticos?

Los archivos Excel de cierres automáticos se guardan **automáticamente** en carpetas específicas:

```
C:\Documentos\
├─ facturas_cierre_mannanas    ← Cierres de Mañana
├─ facturas_cierre_tardes      ← Cierres de Tarde
├─ facturas_cierre_dia         ← Cierres de Día Completo
└─ facturas_cierre_mes         ← Cierres Mensuales
```

**NO NECESITAS HACER NADA.** Los archivos aparecen automáticamente a las horas indicadas.

### Panel de Control: Estado de Automatización

En la pantalla del sistema, hay un panel que muestra el **estado de la automatización**:

```
┌─────────────────────────────────────────────────────────┐
│  🤖 ESTADO DE AUTOMATIZACIÓN                           │
├─────────────────────────────────────────────────────────┤
│  Status:  ✅ Activa                                     │
│                                                         │
│  Próximas ejecuciones:                                  │
│  • Mañana: Mañana 14:00                                 │
│  • Tarde: Mañana 22:00                                  │
│  • Día Completo: Mañana 22:05                           │
│  • Mes: 30 de Junio 22:00                               │
│                                                         │
│  [⏸️ Pausa]                                            │
└─────────────────────────────────────────────────────────┘
```

**Qué significa cada estado**:

| Estado | Significado | Acción |
|--------|-----------|--------|
| ✅ **Activa** | Automatización funciona normalmente | Ninguna - todo OK |
| ⏸️ **Pausada** | Cierres automáticos pausados temporalmente | Haz clic en "▶️ Reanudar" |
| ⚠️ **Con errores** | Último cierre automático falló | Ver detalles de error abajo |

### Cuando Hay Errores: ⚠️ Con errores

Si ves "⚠️ Con errores" en rojo, significa que un cierre automático intentó ejecutarse pero falló.

**Ejemplo**:
```
┌─────────────────────────────────────────────────────────┐
│  🤖 ESTADO DE AUTOMATIZACIÓN                           │
├─────────────────────────────────────────────────────────┤
│  Status:  ⚠️ Con errores  (ROJO)                       │
│                                                         │
│  ❌ Errores detectados:                                 │
│  Tarde: Network path not found                          │
│  Día Completo: Network path not found                   │
│                                                         │
│  🕒 Timestamp: 2026-06-23 22:00:15                      │
│                                                         │
│  [▶️ Reanudar]                                         │
└─────────────────────────────────────────────────────────┘
```

**¿Qué hacer**:
1. Anota qué tipo de cierre falló (en este ejemplo: "Tarde" y "Día Completo")
2. Verifica que las carpetas de cierres sean accesibles
3. Si es problema de red: Intenta reconectar
4. Cuando se arregle: Haz clic en "▶️ Reanudar" o espera al próximo cierre
5. Si continúa fallando: Contacta al administrador

### Panel de Rutas: Verificación de Carpetas

Debajo del panel de automatización hay un panel que verifica **si las carpetas son accesibles**:

```
┌─────────────────────────────────────────────────────────┐
│  📁 ESTADO DE RUTAS DE CIERRE                          │
├─────────────────────────────────────────────────────────┤
│  ✅ Mañana                                              │
│     \\DESKTOP-4UE66NT\C$\Documentos\...                 │
│                                                         │
│  ✅ Tarde                                               │
│     \\DESKTOP-4UE66NT\C$\Documentos\...                 │
│                                                         │
│  ❌ Día Completo                                        │
│     \\DESKTOP-4UE66NT\C$\Documentos\...                 │
│     Último check: 2026-06-23 10:30:45                   │
│                                                         │
│  ✅ Mes                                                 │
│     \\DESKTOP-4UE66NT\C$\Documentos\...                 │
└─────────────────────────────────────────────────────────┘
```

**Interpretación**:
- ✅ **(Verde)**: Carpeta accesible, cierres se guardarán correctamente
- ❌ **(Rojo)**: Carpeta no accesible, próximo cierre fallará

**Si ves ❌ (Rojo)**:
- Los cierres automáticos fallarán cuando llegue la hora
- Verás "⚠️ Con errores" en el panel superior
- Revisa la conexión de red antes de la próxima ejecución

### Pausa y Reanudación Manual

Si necesitas **pausar temporalmente** los cierres automáticos:

1. Abre el panel "🤖 ESTADO DE AUTOMATIZACIÓN"
2. Haz clic en el botón **"⏸️ Pausa"**
3. El estado cambia a "⏸️ Pausada"
4. Los cierres NO se ejecutarán automáticamente
5. Cuando necesites reanudar, haz clic en **"▶️ Reanudar"**

**¿Cuándo pausar**:
- Si hay mantenimiento del servidor
- Si hay problemas con la red
- Si necesitas hacer ajustes en el sistema

**Nota**: La pausa se **guarda automáticamente**, así que si el servidor se reinicia, seguirá pausado.

---

## CONTACTO Y SOPORTE

Si tienes preguntas o problemas:

📧 **Contacta al administrador del sistema**
- Email: [admin@zoopicasso.com]
- Teléfono: [número de soporte]

📋 **Información a proporcionar:**
- Qué tipo de cierre intentaste hacer
- Hora aproximada
- Error exacto que viste
- Fecha del cierre

---

## VERSIÓN DEL DOCUMENTO

- **Fecha:** 23 de Junio, 2026
- **Versión:** 2.0 (Automatización completa + Paneles de control + Health checks)
- **Para:** Zoo Picasso
- **Audiencia:** Operadores, Gerentes, Administradores
- **Páginas:** 28

### Cambios en v2.0
- ✨ Sección nueva: Automatización y Cierres Automáticos
- ✨ Panel de Control del estado de automatización
- ✨ Panel de verificación de rutas de almacenamiento
- ✨ Health checks cada 30 minutos
- ✨ Manejo visual de errores con feedback en tiempo real
- ✨ Capacidad de pausar/reanudar automatización

---

*Este manual está diseñado para ser claro, práctico y fácil de seguir. Si tienes sugerencias para mejorarlo, contacta al administrador.*
