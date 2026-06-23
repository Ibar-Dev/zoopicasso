# Cierres Module - Architecture & Best Practices

## Overview

The **Cierres** (Closures) module is responsible for daily financial closing reports in the Zoo Picasso application. It captures sales by time period, generates Excel reports, and manages automation.

---

## 📐 High-Level Architecture

### Sequential Closure Flow

```
┌─────────────────────────────────────────────────────────────┐
│                   Cierre de Mañana                          │
│              (06:00 - 14:00 local time)                     │
│  ✓ Always available (first closure of the day)              │
│  ✓ Does NOT archive data                                    │
│  ✓ User can repeat as needed                                │
└────────────────────┬────────────────────────────────────────┘
                     │ [if success]
                     ↓
┌─────────────────────────────────────────────────────────────┐
│                   Cierre de Tarde                           │
│              (14:00 - 22:00 local time)                     │
│  ✓ Only available after Mañana done TODAY                   │
│  ✓ Does NOT archive data                                    │
│  ✓ User can repeat after redoing Mañana                     │
└────────────────────┬────────────────────────────────────────┘
                     │ [if success]
                     ↓
┌─────────────────────────────────────────────────────────────┐
│              Cierre del Día Completo                        │
│              (06:00 - 22:00 consolidated)                   │
│  ✓ Only available after Mañana AND Tarde done TODAY         │
│  ✓ Combines both periods                                    │
│  ✓ Does NOT archive data                                    │
└────────────────────┬────────────────────────────────────────┘
                     │ [independent, once per month]
                     ↓
┌─────────────────────────────────────────────────────────────┐
│              Cierre del Mes                                 │
│           (00:00 - 23:59, month-wide)                       │
│  ✓ Always available on last day of month at 22:00           │
│  ✓ ARCHIVES all active sales to "archived" state            │
│  ✓ Cannot be repeated - data is locked                      │
│  ✓ Runs automatically via scheduler                         │
└─────────────────────────────────────────────────────────────┘
```

### Design Intent
- **Sequential validation**: Prevent data loss by requiring steps in order
- **Flexibility**: Daily closures can be repeated (non-destructive)
- **Safety**: Only monthly closure locks data (destructive)
- **Audit trail**: Every closure recorded with user & timestamp

---

## � Keep-Alive System (Server Heartbeat)

The application includes a **Keep-Alive Manager** to prevent server spin-down on Render Free tier.

**How it works**:
```
Every 5 minutes (unconditional):
┌─────────────────────────────────┐
│ Browser (KeepAliveManager)      │
│ - Checks interval (5 min)       │
│ - Sends GET /api/keep-alive     │
└─────────────────────────────────┘
              ↓
┌─────────────────────────────────┐
│ Server (@app.get("/api/keep..."))│
│ - Receives request              │
│ - Returns {"status": "ok"}      │
│ - Server stays active           │
└─────────────────────────────────┘
```

**Configuration (Opción C)**:
- Interval: 5 minutes (300 seconds)
- Mode: Unconditional (always, no activity verification)
- Endpoint: `/api/keep-alive` (no authentication required)
- Module: `web/static/keep-alive.js`
- Status: Available in browser console via `KeepAliveManager.getStatus()`

**Files involved**:
- `web/static/keep-alive.js` - Client-side module (180+ lines)
- `web/templates/index.html` - Loader script tag + initialization
- `web/app.py` - `/api/keep-alive` endpoint (line 323)

**For detailed information**: See [CIERRES_MAINTENANCE.md](CIERRES_MAINTENANCE.md#-keep-alive-system-v20---opción-c)

---

## �📂 Critical File Locations

### Core Modules

| Component | File Path | Primary Function | Line |
|-----------|-----------|------------------|------|
| **Closure Logic** | `src/monthly_closure.py` | Generates Excel & registers cierres | 179+ |
| **Data Queries** | `src/ventas_store.py` | Calculates sales summaries & validates | 724+ |
| **Automation** | `web/scheduler.py` | Schedules & runs automated cierres | 1+ |
| **API Endpoints** | `web/app.py` | HTTP routes for closures | 572+ |
| **UI Handlers** | `web/templates/index.html` | Button click handlers & state sync | 2309+ |

### Configuration & Data

| Purpose | File Path | Format |
|---------|-----------|--------|
| **Closure Output** | `CIERRES_DIR` (default: Downloads) | Excel files |
| **Database** | `data/ventas.db` | SQLite |
| **Automation State** | `data/automation_state.json` | JSON |
| **User Manual** | `docs/MANUAL_CIERRES_CLIENTA.md` | Markdown |

---

## 🗄️ Database Schema

### Table: `cierres_diarios` (Daily Closures)

```sql
CREATE TABLE cierres_diarios (
    cierre_id TEXT PRIMARY KEY,           -- Unique closure ID
    fecha TEXT NOT NULL,                  -- Date in YYYY-MM-DD format
    anio_mes TEXT NOT NULL,               -- Month in YYYY-MM format
    usuario TEXT,                         -- Username or "SISTEMA"
    created_at TEXT,                      -- ISO timestamp (UTC)
    total REAL,                           -- Revenue in euros
    cantidad_ventas INTEGER,              -- Number of transactions
    archivo_excel TEXT,                   -- Path to generated Excel file
    tipo_cierre TEXT                      -- "morning", "afternoon", "full_day"
);
```

**Example Record**:
```
cierre_id: "morning-2026-06-23-143022123456"
fecha: "2026-06-23"
anio_mes: "2026-06"
usuario: "ivar"
created_at: "2026-06-23T14:30:22Z"
total: 542.50
cantidad_ventas: 18
archivo_excel: "/home/ivar/Downloads/Cierre_de_la_mañana_2026-06-23_143022.xlsx"
tipo_cierre: "morning"
```

### Table: `cierres_mensuales` (Monthly Closures)
```sql
CREATE TABLE cierres_mensuales (
    cierre_id TEXT PRIMARY KEY,           -- Unique closure ID
    anio_mes TEXT NOT NULL UNIQUE,        -- Month in YYYY-MM format
    usuario TEXT,                         -- Username who triggered closure
    created_at TEXT,                      -- ISO timestamp (UTC)
    total REAL,                           -- Revenue in euros
    cantidad_ventas INTEGER,              -- Number of transactions archived
    archivo_excel TEXT,                   -- Path to generated Excel file
    UNIQUE(anio_mes)
);
```

**Why separate tables?**
- Daily closures are ephemeral (can be repeated)
- Monthly closures are permanent (data archived)
- Different query patterns

**Index Recommendation** (for performance):
```sql
CREATE INDEX idx_cierres_diarios_fecha_tipo 
ON cierres_diarios(fecha, tipo_cierre);
```

---

## 🔄 API Request/Response Pattern

### Two-Phase Closure Pattern

All daily closures (Mañana, Tarde, Día Completo) use a **2-phase confirmation flow**:

#### Phase 1: Preview/Review (confirmacion=false)

**Request**:
```json
POST /api/ganancias/cierre-mañana
Content-Type: application/json

{
  "confirmacion": false
}
```

**Response** (JSON):
```json
{
  "ok": true,
  "fecha": "2026-06-23",
  "dinero_bruto": 542.50,
  "cantidad_ventas": 18,
  "por_categoria": {
    "perro": 250.00,
    "gato": 150.00,
    "peluqueria": 142.50
  }
}
```

**Purpose**: User sees what will be closed before confirming.

#### Phase 2: Commit (confirmacion=true)

**Request**:
```json
POST /api/ganancias/cierre-mañana
Content-Type: application/json

{
  "confirmacion": true
}
```

**Response** (File):
```
Status: 200 OK
Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Disposition: attachment; filename="Cierre_de_la_mañana_2026-06-23_143022.xlsx"

[Excel file binary data]
```

**Purpose**: Excel is generated, saved to disk, and registered in database.

### Why 2 Phases?

1. **User Review**: See totals before committing
2. **Error Prevention**: Prevents accidental closures
3. **Data Validation**: Catch issues before registration
4. **UX**: Upload status to configured folder

---

## ⏰ Automation Schedule

### Cron Jobs Defined

Automation runs on **strict schedule**:

```
Trigger     Time    Job                     Function
────────────────────────────────────────────────────────
Daily       14:00   Cierre de Mañana       cerrar_mañana()
Daily       22:00   Cierre de Tarde        cerrar_tarde()
Daily       22:05   Cierre del Día         cerrar_día_completo()
            Completo
Monthly     22:00   Cierre del Mes         cerrar_mes()
(last day)  (on last day of month)
```

### Schedule Definition

**File**: `web/scheduler.py` - `init_scheduler()` function

```python
# Cierre de mañana: 14:00 todos los días
scheduler.add_job(
    _wrap_cierre("mañana", cerrar_mañana),
    trigger=CronTrigger(hour=14, minute=0),
    id="cierre_mañana",
)

# Cierre de tarde: 22:00 todos los días
scheduler.add_job(
    _wrap_cierre("tarde", cerrar_tarde),
    trigger=CronTrigger(hour=22, minute=0),
    id="cierre_tarde",
)

# Cierre de día completo: 22:05
scheduler.add_job(
    _wrap_cierre("día_completo", cerrar_día_completo),
    trigger=CronTrigger(hour=22, minute=5),
    id="cierre_dia_completo",
)

# Cierre de mes: 22:00 en el último día del mes
scheduler.add_job(
    _wrap_cierre("mes", cerrar_mes),
    trigger=CronTrigger(day="last", hour=22, minute=0),
    id="cierre_mes",
)
```

### Automation State Management

**Pause/Resume**:
- User can pause all automation via UI
- State saved to `data/automation_state.json`
- Restored on app restart

**All Jobs Run As**:
- `usuario="SISTEMA"` (system account for audit trail)
- Respects pause state
- Logs all results

**Defensive Programming**:
- Code-level check in `_wrap_cierre()`: `if not automation_state["enabled"]: return`
- Prevents execution even if APScheduler fails
- Logging shows "⏸️ Cierre de {type} saltado (automatización pausada)"

---

## 🔄 UI ↔ Backend Synchronization

### Error Feedback Architecture

The system now provides **complete visibility** of automation status and errors:

```
┌──────────────────────────────────────────────────────────────┐
│                    FRONTEND (index.html)                     │
│                                                              │
│  AutomationUI Object                                         │
│  ├─ loadStatus() [Line ~2776]                                │
│  │  └─ Fetches /api/automation/status every 60 seconds       │
│  │     ├─ On HTTP error: Shows "❌ Error conectando"         │
│  │     ├─ On network error: Shows "❌ Error de red"          │
│  │     └─ On success: Calls updateUI()                       │
│  │                                                            │
│  ├─ updateUI(data) [Line ~2799]                              │
│  │  ├─ If data.last_error exists: Displays errors in RED    │
│  │  │  └─ Shows list of failed closure types with messages  │
│  │  ├─ Else if enabled=true: "✅ Activa" (GREEN)            │
│  │  └─ Else: "⏸️ Pausada" (ORANGE)                           │
│  │                                                            │
│  ├─ pause() [Line ~2854]                                     │
│  │  ├─ POST /api/automation/pause                            │
│  │  ├─ ✅ Validates response.ok before proceeding           │
│  │  └─ Shows error toast if HTTP error                       │
│  │                                                            │
│  └─ resume() [Line ~2873]                                    │
│     ├─ POST /api/automation/resume                           │
│     ├─ ✅ Validates response.ok before proceeding           │
│     └─ Shows error toast if HTTP error                       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                            ↑
                    POST/GET requests
                            ↓
┌──────────────────────────────────────────────────────────────┐
│                     API (app.py)                             │
│                                                              │
│  Endpoints                                                   │
│  ├─ GET /api/automation/status                               │
│  │  └─ Returns: {"enabled", "jobs", "last_error"}            │
│  │                                                            │
│  ├─ POST /api/automation/pause                               │
│  │  ├─ Calls: pause_automation()                             │
│  │  └─ Saves state to file                                   │
│  │                                                            │
│  ├─ POST /api/automation/resume                              │
│  │  ├─ Calls: resume_automation()                            │
│  │  └─ Saves state to file                                   │
│  │                                                            │
│  └─ GET /api/rutas/estado (NEW)                              │
│     └─ Returns health status of 4 route directories          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                            ↑
                 Python function calls
                            ↓
┌──────────────────────────────────────────────────────────────┐
│                   BACKEND (scheduler.py)                     │
│                                                              │
│  Automation State                                            │
│  ├─ automation_state dict (in-memory)                        │
│  │  ├─ "enabled": bool (true=running, false=paused)         │
│  │  ├─ "jobs": list (next scheduled times)                   │
│  │  ├─ "last_execution": dict (last successful run)          │
│  │  └─ "last_error": dict (last failed run with errors)      │
│  │                                                            │
│  └─ data/automation_state.json (persisted)                   │
│     └─ Saves pause/resume state across app restarts          │
│                                                              │
│  Cron Jobs (APScheduler)                                     │
│  ├─ 14:00: _wrap_cierre("mañana", cerrar_mañana)             │
│  │  ├─ ✅ Defensive check: if not enabled: return           │
│  │  ├─ Try: Execute cerrar_mañana(usuario="SISTEMA")        │
│  │  └─ Except: Save error to automation_state["last_error"] │
│  │                                                            │
│  ├─ 22:00: _wrap_cierre("tarde", cerrar_tarde)               │
│  ├─ 22:05: _wrap_cierre("día_completo", cerrar_dia)          │
│  └─ 22:00 (last day): _wrap_cierre("mes", cerrar_mes)        │
│                                                              │
│  Health Check (every 30 minutes)                             │
│  ├─ Validates all 4 route directories exist                  │
│  ├─ Writes result to data/routes_health_check.json           │
│  └─ Returns status via GET /api/rutas/estado                 │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Error Lifecycle Example

```
Scenario: Network folder becomes unreachable during automatic closure

1️⃣ BACKEND (22:00 automatic execution)
   ├─ APScheduler triggers _wrap_cierre("tarde", cerrar_tarde)
   ├─ Defensive check: automation_state["enabled"] = True ✅
   ├─ Calls: cerrar_tarde(usuario="SISTEMA")
   ├─ Tries to write to: \\DESKTOP-4UE66NT\C$\Documentos\...
   └─ ❌ EXCEPTION: Network path not reachable
       └─ Caught in _wrap_cierre()
       └─ Saved to: automation_state["last_error"]["tarde"] = "Network path not reachable"
       └─ Logged: "❌ Error en cierre de tarde: Network path not reachable"

2️⃣ NEXT UI POLL (within 60 seconds)
   ├─ Browser polls: GET /api/automation/status
   ├─ Backend returns: {"enabled": true, "last_error": {"tarde": "Network..."}}
   ├─ updateUI() detects: tieneErrores = true
   └─ Updates UI:
       ├─ statusEl.textContent = "⚠️ Con errores"
       ├─ statusEl.style.color = "#ef4444" (RED)
       └─ proximosEl.innerHTML = "❌ Errores detectados:\n"
                                 "tarde: Network path not reachable\n"
                                 "🕒 23:05:12"

3️⃣ USER SEES (in real-time)
   ├─ Red "⚠️ Con errores" indicator
   ├─ List of failed closure types with error messages
   ├─ Timestamp of when error occurred
   └─ Can now take action: check network, restart server, etc.

4️⃣ AFTER FIX
   ├─ User restarts app or fixes network path
   ├─ Next automatic closure succeeds
   ├─ automation_state["last_error"]["tarde"] is cleared
   ├─ UI updates to green "✅ Activa"
   └─ User knows system is back to normal
```

### Polling Intervals

| Component | Interval | Purpose | File/Location |
|-----------|----------|---------|---|
| **UI Status Refresh** | 60 seconds | Load automation status, display errors | index.html:~2381 |
| **Button State Refresh** | 30 seconds | Check if closure prerequisites met | index.html:~2375 |
| **Health Check** | 30 minutes | Validate route directories exist | scheduler.py:~156 |
| **Manual API Call** | On demand | User-triggered pause/resume/closure | index.html:~2854 |

**Rationale**:
- 60s status: Good balance between UI responsiveness and server load
- 30s buttons: Faster feedback for user actions
- 30m health: Frequent enough to catch issues, not too chatty
- On-demand: Critical operations get immediate confirmation

---

## 🔑 Key Functions Reference

### Time Period Summaries

```python
# Get sales from 06:00-14:00 (local time)
resumen_ventas_mañana(fecha: str) -> dict
# Returns: {"fecha", "periodo", "total", "cantidad_ventas", "por_categoria"}

# Get sales from 14:00-22:00 (local time)
resumen_ventas_tarde(fecha: str) -> dict
# Returns: Same structure as above

# Get all sales for the day (06:00-22:00)
resumen_ventas_dia(fecha: str) -> dict
# Returns: Same structure as above
```

### Validation & State

```python
# Check if a closure type can be performed
puede_hacer_cierre(tipo_cierre: str, fecha: str) -> tuple[bool, str]
# Returns: (can_do_bool, reason_message)
# Example: (False, "Primero debes hacer el cierre de mañana")

# Get today's completion status
obtener_cierres_hoy(fecha: str) -> dict
# Returns: {"hizo_mañana", "hizo_tarde", "hizo_dia_completo", "cierres": [...]}
```

### Perform Closure

```python
# Execute closure and generate Excel
cerrar_mañana(usuario: str) -> tuple[dict, Path | None]
cerrar_tarde(usuario: str) -> tuple[dict, Path | None]
cerrar_día_completo(usuario: str) -> tuple[dict, Path | None]
cerrar_mes(usuario: str) -> tuple[dict, Path | None]

# Returns: (metadata_dict, path_to_excel_or_none)
# metadata_dict contains: {"ok", "fecha", "cantidad_ventas", "total", "mensaje"}
```

### Automation Control

```python
# Pause all scheduled jobs
pause_automation() -> None
# Saves state to data/automation_state.json

# Resume all scheduled jobs
resume_automation() -> None
# Saves state to data/automation_state.json

# Get current automation status
get_automation_status() -> dict
# Returns full state including next scheduled times
```

---

## ⚠️ Common Pitfalls & Solutions

### Pitfall 1: UTC vs Local Time in Queries

**❌ WRONG** (before fix):
```python
CAST(strftime('%H', created_at) AS INTEGER) >= 6  # Uses UTC!
```

**✅ CORRECT** (after fix):
```python
CAST(strftime('%H', datetime(created_at, 'localtime')) AS INTEGER) >= 6
```

**Why**: `created_at` stored in UTC. Extract hours from local time instead.

**Files to Check**: `src/ventas_store.py` lines 724-795

---

### Pitfall 2: Stale UI State After Automation

**❌ PROBLEM**:
- Automation closes Mañana at 14:00
- User's browser still shows Mañana button as available
- Tarde button stays disabled until page reload

**✅ SOLUTION**:
```javascript
setInterval(cargarEstadoCierres, 30000);  // Refresh every 30 seconds
```

**Location**: `web/templates/index.html` line 2375

---

### Pitfall 3: Lost Pause State After Restart

**❌ PROBLEM**:
- User pauses automation at 13:00
- App restarts at 13:55
- 14:00 automation still runs (pause forgotten!)

**✅ SOLUTION**:
```python
# Save to file on pause/resume
_save_automation_state_to_file(False)

# Load from file on startup
saved_state = _load_automation_state_from_file()
if saved_state is not None:
    automation_state["enabled"] = saved_state
```

**File**: `web/scheduler.py` lines 54-76 (save/load functions)

---

### Pitfall 4: Timezone Assumption

**❌ PROBLEM**:
- Server timezone is UTC, but queries assume Madrid time
- Sales at 15:00 Madrid (14:00 UTC) go to Mañana instead of Tarde
- Financial accuracy lost

**✅ SOLUTION**:
Ensure system timezone is correct:
```bash
# Linux/Mac - check and set
timedatectl list-timezones | grep Madrid
sudo timedatectl set-timezone Europe/Madrid

# In code - verify timezone conversion works
SELECT datetime('now'), datetime('now', 'localtime');
```

---

## 🧪 Testing Recommendations

### Unit Tests

Create `tests/test_cierres_module.py`:

```python
def test_resumen_ventas_mañana_uses_localtime():
    """Verify morning query uses local time, not UTC"""
    # Create sale at 14:00 local (13:00 UTC if in UTC+1)
    # Assert: Sale NOT in mañana summary

def test_resumen_ventas_tarde_uses_localtime():
    """Verify afternoon query uses local time"""
    # Create sale at 21:00 local
    # Assert: Sale IS in tarde summary

def test_pause_state_persisted():
    """Verify pause state saved to JSON"""
    pause_automation()
    assert (DATA_DIR / "automation_state.json").exists()
    content = json.load(open(...))
    assert content["enabled"] is False

def test_pause_state_restored_on_restart():
    """Verify pause state loaded on startup"""
    # Manually save {"enabled": False} to file
    init_scheduler()
    assert automation_state["enabled"] is False
```

### Integration Tests

```python
def test_full_closure_flow():
    """Test 2-phase closure pattern"""
    # Phase 1: Preview
    result1 = cierre_mañana_endpoint(confirmacion=False)
    assert result1["ok"] is True
    assert "dinero_bruto" in result1
    
    # Verify NOT registered yet
    cierres_before = conn.execute("SELECT COUNT(*) FROM cierres_diarios").fetchone()
    
    # Phase 2: Commit
    result2 = cierre_mañana_endpoint(confirmacion=True)
    assert result2.status_code == 200
    
    # Verify NOW registered
    cierres_after = conn.execute("SELECT COUNT(*) FROM cierres_diarios").fetchone()
    assert cierres_after[0] == cierres_before[0] + 1
```

---

## 📈 Performance Considerations

### Database Queries

**Current Performance**:
- `resumen_ventas_mañana()`: ~50-100ms (for ~5000 daily sales)
- Recommend index on `(fecha, created_at)` for faster time filtering

**Query Optimization**:
```sql
-- Add this index in production
CREATE INDEX idx_ventas_date_time 
ON ventas(DATE(fecha_venta), 
          CAST(strftime('%H', datetime(created_at, 'localtime')) AS INTEGER));
```

### Auto-Refresh Interval

**Current**: 30 seconds

**Trade-off**:
- 15 seconds: Better UX, more server load
- 30 seconds: Good balance (current)
- 60 seconds: Less load, but stale UI possible

**Adjust in** `index.html` line 2375

---

## 🔗 Related Documentation

- [`CIERRES_BUGS_FIXED.md`](CIERRES_BUGS_FIXED.md) - Bugs fixed & implementation details
- [`CIERRES_MAINTENANCE.md`](CIERRES_MAINTENANCE.md) - Maintenance procedures & checklist
- [`MANUAL_CIERRES_CLIENTA.md`](MANUAL_CIERRES_CLIENTA.md) - User guide for closures
- `src/monthly_closure.py` - Main closure logic (commented)
- `src/ventas_store.py` - Data access layer (commented)

---

## 📞 Quick Reference

**Need to...**

| Task | Location | Function |
|------|----------|----------|
| Fix time period queries | `src/ventas_store.py:724` | `resumen_ventas_mañana()` |
| Add new closure type | `web/scheduler.py` | `init_scheduler()` |
| Change automation time | `web/scheduler.py:142` | CronTrigger |
| Debug period routing | `src/ventas_store.py` | See `localtime` conversion |
| Check automation state | `web/scheduler.py:42` | `automation_state` dict |
| Understand API flow | `web/app.py:572` | Closure endpoints |
| Test UI sync | `web/templates/index.html:2375` | `setInterval()` |

---

**Last Updated**: 2026-06-23
**Maintained By**: Development Team
**Status**: Production Ready ✅
