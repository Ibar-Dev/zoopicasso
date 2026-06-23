# Cierres Module - Maintenance & Development Checklist

---

## ✅ Pre-Deployment Checklist

### Before Merging Changes to `main`:

#### Timezone Handling
- [ ] All timestamp queries use `datetime(..., 'localtime')` conversion
- [ ] Test with sales near period boundaries (06:00, 14:00, 22:00)
- [ ] Confirm `TZ` environment variable is set correctly
- [ ] Verify in database: `SELECT datetime('now'), datetime('now', 'localtime');`

#### Automation State Persistence
- [ ] Pause/resume saves to `data/automation_state.json`
- [ ] State loads correctly on app restart
- [ ] File format is valid JSON
- [ ] Test pause state persists across multiple restarts

#### UI Synchronization
- [ ] `setInterval(cargarEstadoCierres, 30000)` present in `index.html` line 2375
- [ ] Button states update within 30 seconds after closure
- [ ] Multi-tab test: One tab triggers closure, other updates
- [ ] No console errors related to state polling

#### Sequential Validation
- [ ] Tarde button disabled until Mañana completed TODAY
- [ ] Día Completo button disabled until BOTH Mañana AND Tarde completed TODAY
- [ ] Date-specific check (not just existence of past closures)
- [ ] Error messages displayed for invalid sequences

#### Database Integrity
- [ ] No duplicate closures for same date+type
- [ ] All closures have valid `cierre_id`, `fecha`, `tipo_cierre`
- [ ] Excel files generated and saved to configured directory
- [ ] Automation log shows successful registrations

#### APScheduler Status
- [ ] No import errors in startup logs
- [ ] Cron triggers scheduled correctly
- [ ] Automation state shows "available: true"
- [ ] Test that pause/resume works without errors

### Database Validation Queries

```sql
-- Check for duplicate closures (should be empty)
SELECT fecha, tipo_cierre, COUNT(*) as count
FROM cierres_diarios
GROUP BY fecha, tipo_cierre
HAVING count > 1;

-- Verify today's closures
SELECT * FROM cierres_diarios 
WHERE fecha = DATE('now')
ORDER BY created_at DESC;

-- Check for orphaned Excel files
SELECT COUNT(*) FROM cierres_diarios
WHERE archivo_excel IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM sqlite_temp_master);

-- Verify automation state file
-- (Check manually: cat data/automation_state.json)
```

---

## 🧪 Manual Test Cases

### Test 1: Period Time Conversion

**Purpose**: Verify UTC→LocalTime conversion works

**Steps**:
1. Create a sale at 14:00 local time (boundary)
2. Run `cerrar_mañana()` - **should NOT include this sale**
3. Run `cerrar_tarde()` - **should include this sale**
4. Verify Excel files show different totals

**Expected Result**: ✅ Sale correctly categorized in Tarde

**Command**:
```bash
# Create test sale at 14:00 local
python -c "
from src.ventas_store import agregar_venta
agregar_venta(
    numero_factura='TEST001',
    cliente_nombre='Test',
    monto=100.00,
    categoria='perro'
)
"

# Run closures
python -c "
from src.monthly_closure import cerrar_mañana, cerrar_tarde
print(cerrar_mañana('test'))
print(cerrar_tarde('test'))
"
```

---

### Test 2: Automation Persistence

**Purpose**: Verify pause state survives restart

**Steps**:
1. Pause automation via UI
2. Check `data/automation_state.json` contains `"enabled": false`
3. Restart application
4. Verify automation stays paused (next scheduled job delayed or not running)
5. Check logs show "Restituyendo estado pausado"

**Expected Result**: ✅ State persisted and restored

**Verification**:
```bash
# Check file exists and has correct content
cat generar_para_email/data/automation_state.json
# Should output:
# {
#   "enabled": false,
#   "timestamp": "2026-06-23T10:30:45"
# }

# Check logs
grep "Restituyendo estado pausado" generar_para_email/logs/app.log
```

---

### Test 3: Button Sync Across Tabs

**Purpose**: Verify auto-refresh works in multi-tab scenario

**Steps**:
1. Open app in Tab A
2. Open app in Tab B (same user, same browser)
3. Click "Cierre Mañana" in Tab A
4. Wait **max 30 seconds**
5. Check Tab B: Tarde button should be **enabled** automatically
6. Observe no page refresh was needed

**Expected Result**: ✅ Buttons synchronized within 30s

**Browser Console** (to verify refresh happening):
```javascript
// In browser console, add this before test
const originalFetch = window.fetch;
let refreshCount = 0;
window.fetch = function(...args) {
  if (args[0].includes('estado-cierres')) {
    refreshCount++;
    console.log(`Refresh #${refreshCount} at ${new Date().toLocaleTimeString()}`);
  }
  return originalFetch.apply(this, args);
};
```

---

### Test 4: Sequential Validation

**Purpose**: Verify buttons are correctly disabled/enabled

**Steps**:
1. Load page fresh (new day)
2. **Mañana button** - should be **enabled**
3. **Tarde button** - should be **disabled**
4. **Día Completo button** - should be **disabled**
5. Click "Cierre Mañana" → Complete
6. **Tarde button** - should now be **enabled**
7. **Día Completo button** - still **disabled**
8. Click "Cierre Tarde" → Complete
9. **Día Completo button** - should now be **enabled**

**Expected Result**: ✅ Buttons enable in correct sequence

**Inspect Element** (to check button state):
```javascript
// Check button attributes
console.log('Mañana:', document.getElementById('btn-cierre-mañana').disabled);
console.log('Tarde:', document.getElementById('btn-cierre-tarde').disabled);
console.log('Día Completo:', document.getElementById('btn-cierre-dia-completo').disabled);
```

---

### Test 5: No Duplicate Closures

**Purpose**: Verify same-day duplicates are prevented

**Steps**:
1. Complete "Cierre Mañana" at 14:05
2. Try completing "Cierre Mañana" again immediately
3. Should see error message
4. Verify database has only 1 entry (not 2)

**Expected Result**: ✅ Error: "Ya completaste el cierre de mañana hoy"

**Database Check**:
```sql
SELECT COUNT(*) FROM cierres_diarios
WHERE fecha = DATE('now')
  AND tipo_cierre = 'morning';
-- Should return: 1
```

---

### Test 6: Excel File Generation

**Purpose**: Verify Excel files are created correctly

**Steps**:
1. Complete any closure (e.g., Cierre Mañana)
2. Check configured closure folder (`CIERRES_DIR`)
3. Verify Excel file exists with correct name format
4. Open Excel file and verify data is present

**Expected Result**: ✅ File exists in correct location

**Expected Filename Format**:
```
Cierre_de_la_mañana_2026-06-23_143022.xlsx    (morning)
Cierre_de_la_tarde_2026-06-23_220000.xlsx     (afternoon)
Cierre_del_dia_completo_2026-06-23_220500.xlsx (full day)
Cierre_del_mes_2026-06-30_220000.xlsx         (monthly)
```

---

### Test 7: Timezone Edge Cases

**Purpose**: Test sales near period boundaries

**Create test sales at boundaries**:

```python
from datetime import datetime, timezone
from src.ventas_store import agregar_venta

# Create sale at 05:59 (should NOT be captured by mañana)
agregar_venta('TEST-0559', 'Test', 10.00, 'perro')

# Create sale at 06:00 (should be captured)
agregar_venta('TEST-0600', 'Test', 10.00, 'perro')

# Create sale at 13:59 (should be captured by mañana)
agregar_venta('TEST-1359', 'Test', 10.00, 'perro')

# Create sale at 14:00 (should NOT be in mañana, should be in tarde)
agregar_venta('TEST-1400', 'Test', 10.00, 'perro')

# Create sale at 21:59 (should be in tarde)
agregar_venta('TEST-2159', 'Test', 10.00, 'perro')

# Create sale at 22:00 (should NOT be captured by tarde)
agregar_venta('TEST-2200', 'Test', 10.00, 'perro')
```

**Then verify**:
```python
from src.ventas_store import resumen_ventas_mañana, resumen_ventas_tarde

mañana = resumen_ventas_mañana('2026-06-23')
tarde = resumen_ventas_tarde('2026-06-23')

# Mañana should have: 06:00, 13:59 = 2 sales
assert mañana['cantidad_ventas'] == 2
assert mañana['total'] == 20.00

# Tarde should have: 14:00, 21:59 = 2 sales
assert tarde['cantidad_ventas'] == 2
assert tarde['total'] == 20.00
```

**Expected Result**: ✅ All boundary cases correct

---

### Test 8: UI Error Feedback (NEW - 2026-06-23)

**Purpose**: Verify error visibility in automation panel

**Setup**:
1. Ensure automation is running (green "✅ Activa")
2. Prepare a scenario that will cause closure to fail:
   - Option A: Disconnect network folder (for network path error)
   - Option B: Modify database permissions (for database error)
   - Option C: Manually inject error in backend for testing

**Manual Error Injection** (for testing without real failures):
```python
# In web/scheduler.py, temporarily modify _wrap_cierre
def _wrap_cierre(cierre_type: str, cierre_func):
    def wrapper():
        if not automation_state["enabled"]:
            logger.debug(f"⏸️ Cierre de {cierre_type} saltado")
            return
        try:
            # Inject test error
            raise Exception("TEST ERROR: Network path unreachable")
        except Exception as e:
            automation_state["last_error"][cierre_type] = {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"❌ Error en cierre de {cierre_type}: {e}")
```

**Steps**:
1. Trigger the failing closure (manual or automatic)
2. Check browser console for any errors
3. Within 60 seconds, observe UI automation panel
4. Verify error displays in red

**Expected UI Changes**:
- Status text: "⏸️ Pausada" → "⚠️ Con errores" (RED)
- Error message shows: "❌ Errores detectados:\n tarde: TEST ERROR: Network..."
- Timestamp shows when error occurred
- Buttons remain interactive (can try pause/resume)

**Expected Result**: ✅ Errors visible in red, user informed

**Browser Inspector** (to verify):
```javascript
// In browser DevTools console:
document.querySelector('[id*="automation-status"]').innerText
// Should show: "⚠️ Con errores"

document.querySelector('[id*="automation-proximos"]').innerText
// Should show: "❌ Errores detectados:\ntarde: TEST ERROR..."
```

---

### Test 9: Automation Pause State Persistence (Extended)

**Purpose**: Verify pause state survives app restart with error preservation

**Steps**:
1. Start application with errors in last_error (from Test 8)
2. Pause automation via UI
3. Verify file `data/automation_state.json` contains `"enabled": false`
4. Check that errors are still visible in UI
5. Stop application completely
6. Restart application
7. Observe errors still displayed (should NOT auto-clear on restart)
8. Resume automation
9. Verify errors persist until next automatic closure

**Expected Result**: ✅ Pause state persisted, errors preserved through restart

**Verification**:
```bash
# 1. Check pause state file
cat generar_para_email/data/automation_state.json
# Should show: {"enabled": false, "timestamp": "..."}

# 2. Check that last_error is still tracked
# (This is in-memory, not persisted, so clears on restart)
# After restart, errors should be gone from last_error dict
# Until next failure occurs
```

---

### Test 10: Defensive Backend Check

**Purpose**: Verify backend defensive check prevents execution when paused

**Setup**:
1. Ensure logging is enabled to DEBUG level
2. Enable automatic closure at a specific time (or manually trigger)

**Steps**:
1. Open `generar_para_email/logs/app.log` and tail it
2. Pause automation (pause() function)
3. Wait for next scheduled closure time (or force trigger)
4. Check logs for message: "⏸️ Cierre de {type} saltado (automatización pausada)"
5. Verify closure did NOT execute (no "Iniciando cierre" log)
6. Resume automation
7. Wait for next closure, verify it now shows "Iniciando cierre"

**Expected Result**: ✅ Defensive check logged, closure skipped while paused

**Log Analysis**:
```bash
# When paused, should see:
grep "saltado" generar_para_email/logs/app.log
# Output: ⏸️ Cierre de tarde saltado (automatización pausada)

# When resuming, should NOT see "Iniciando cierre" until next scheduled time
grep "Iniciando cierre" generar_para_email/logs/app.log | tail -1
```

---

### Test 11: Error Clearing After Fix

**Purpose**: Verify errors are cleared when closure succeeds after failure

**Scenario**:
1. Closure fails (shows error in UI) - from Test 8
2. UI shows "⚠️ Con errores" in red
3. Fix the underlying issue (reconnect network, restore permissions, etc.)
4. Next automatic closure succeeds
5. Observe UI updates

**Steps**:
1. Verify error is showing: Status = "⚠️ Con errores", Color = RED
2. Fix the network/permission issue
3. Manually trigger next closure OR wait for scheduler
4. Monitor network tab in browser DevTools
5. Observe GET /api/automation/status response
6. Within 60 seconds, UI should update

**Expected UI Changes**:
- Status text: "⚠️ Con errores" → "✅ Activa" (GREEN)
- Message area clears, shows next scheduled times instead
- last_error dict in API response is now empty

**Expected Result**: ✅ Error clears, UI reflects success

**Network Tab Check**:
```json
// GET /api/automation/status response after fix:
{
  "enabled": true,
  "jobs": [
    {"name": "Mañana", "next_run": "2026-06-24T14:00:00"},
    ...
  ],
  "last_execution": {
    "tarde": {"ok": true, "timestamp": "2026-06-23T22:00:15"}
  },
  "last_error": {}  // ← Should be empty after success
}
```

---

## 🤖 Automated Testing (Unit Tests)

### File: `tests/test_cierres_timezone.py`

```python
import pytest
from datetime import datetime, timezone, timedelta
from src.ventas_store import (
    agregar_venta,
    resumen_ventas_mañana,
    resumen_ventas_tarde
)

@pytest.fixture
def setup_test_sales():
    """Create test sales at various times"""
    fecha = datetime.now().strftime('%Y-%m-%d')
    
    # Sales at boundaries
    sales_times = {
        '05:59': 'should_not_be_captured',
        '06:00': 'mañana',
        '13:59': 'mañana',
        '14:00': 'tarde',
        '21:59': 'tarde',
        '22:00': 'should_not_be_captured',
    }
    
    for time_str, _ in sales_times.items():
        agregar_venta(f'TEST-{time_str}', 'Test', 10.00, 'perro')
    
    yield fecha
    
    # Cleanup (optional)

def test_mañana_includes_06_to_14():
    """Morning should capture 06:00-14:00"""
    mañana = resumen_ventas_mañana('2026-06-23')
    assert mañana['cantidad_ventas'] >= 2  # 06:00 and 13:59

def test_tarde_includes_14_to_22():
    """Afternoon should capture 14:00-22:00"""
    tarde = resumen_ventas_tarde('2026-06-23')
    assert tarde['cantidad_ventas'] >= 2  # 14:00 and 21:59

def test_boundary_14_goes_to_tarde():
    """Exactly 14:00 should go to tarde, not mañana"""
    mañana = resumen_ventas_mañana('2026-06-23')
    tarde = resumen_ventas_tarde('2026-06-23')
    
    # Sale at exactly 14:00 should be in tarde
    assert tarde['cantidad_ventas'] > 0
    # And should NOT push mañana beyond boundary
    assert 'TEST-1400' not in str(mañana)
```

### File: `tests/test_cierres_automation.py`

```python
import json
from pathlib import Path
from web.scheduler import (
    _save_automation_state_to_file,
    _load_automation_state_from_file,
    pause_automation,
    resume_automation,
    automation_state
)

def test_save_automation_state():
    """Verify state saved to JSON file"""
    _save_automation_state_to_file(False)
    
    state_file = Path('generar_para_email/data/automation_state.json')
    assert state_file.exists()
    
    with open(state_file) as f:
        data = json.load(f)
    assert data['enabled'] is False

def test_load_automation_state():
    """Verify state loaded from file"""
    _save_automation_state_to_file(False)
    
    loaded = _load_automation_state_from_file()
    assert loaded is False

def test_pause_saves_state():
    """Pause should save disabled state"""
    pause_automation()
    
    loaded = _load_automation_state_from_file()
    assert loaded is False
    assert automation_state['enabled'] is False

def test_resume_saves_state():
    """Resume should save enabled state"""
    resume_automation()
    
    loaded = _load_automation_state_from_file()
    assert loaded is True
    assert automation_state['enabled'] is True
```

---

## 🐛 Debugging Common Issues

### Issue: Button stays disabled even after completing prerequisite

**Diagnostic Steps**:
```bash
# 1. Check database has entry for today
sqlite3 generar_para_email/data/ventas.db \
  "SELECT * FROM cierres_diarios WHERE fecha = DATE('now');"

# 2. Verify date format is YYYY-MM-DD
sqlite3 generar_para_email/data/ventas.db \
  "SELECT DATE('now');"

# 3. Check logs for errors
grep "ERROR\|error" generar_para_email/logs/app.log | tail -20

# 4. Manually trigger state update
curl http://localhost:8000/api/ganancias/estado-cierres
```

**Common Causes**:
- ❌ Wrong date in database (check system date)
- ❌ Closure not registered (check logs for registration errors)
- ❌ Browser cache (clear and reload)

---

### Issue: Closures capture wrong time periods

**Diagnostic Steps**:
```bash
# 1. Check timezone configuration
timedatectl  # Linux/Mac
Get-TimeZone # Windows

# 2. Verify timezone in database
sqlite3 generar_para_email/data/ventas.db
SELECT datetime('now'), datetime('now', 'localtime');
# Times should differ by timezone offset

# 3. Check query using localtime conversion
sqlite3 generar_para_email/data/ventas.db
SELECT COUNT(*) FROM ventas
WHERE CAST(strftime('%H', datetime(created_at, 'localtime')) AS INTEGER) >= 6
  AND CAST(strftime('%H', datetime(created_at, 'localtime')) AS INTEGER) < 14;

# 4. Check without localtime (should show different result)
sqlite3 generar_para_email/data/ventas.db
SELECT COUNT(*) FROM ventas
WHERE CAST(strftime('%H', created_at) AS INTEGER) >= 6
  AND CAST(strftime('%H', created_at) AS INTEGER) < 14;
```

**Common Causes**:
- ❌ System timezone wrong (`TZ` environment variable)
- ❌ Database using UTC instead of local
- ❌ Old query code without `localtime` conversion

**Fix**:
```bash
# Set timezone
export TZ=Europe/Madrid
# or
sudo timedatectl set-timezone Europe/Madrid

# Restart application
systemctl restart app  # or restart manually
```

---

### Issue: Automation pause state lost after restart

**Diagnostic Steps**:
```bash
# 1. Check if state file exists
ls -la generar_para_email/data/automation_state.json

# 2. Check file content
cat generar_para_email/data/automation_state.json

# 3. Check logs for state restoration
grep "Restituyendo\|paused" generar_para_email/logs/app.log

# 4. Check automation_state in-memory
# (Add debug log in init_scheduler)
```

**Common Causes**:
- ❌ File not created (first pause didn't save)
- ❌ File corrupted (JSON syntax error)
- ❌ `data/` directory doesn't exist or not writable

**Fix**:
```bash
# Delete corrupted file
rm generar_para_email/data/automation_state.json

# Ensure directory exists and is writable
mkdir -p generar_para_email/data
chmod 755 generar_para_email/data

# Restart app
systemctl restart app
```

---

## 📝 Common Development Tasks

### Task: Add a New Closure Type (e.g., "Cierre de Mediodía")

**Steps**:

1. **Update UI** (`web/templates/index.html`):
```javascript
// Add to tiposDescripcion object (around line 2336)
'mediodía': { 
  color: '#FF6B6B', 
  icono: '⏰', 
  descripcion: 'Cierre de Mediodía (10:00-16:00)' 
},

// Add button HTML (around line 180)
<button id="btn-cierre-mediodía" class="ghost" type="button">⏰ Mediodía</button>

// Add event listener (around line 1600)
btnCierreMediodía.addEventListener('click', async () => {
  // ... similar to existing closures
});
```

2. **Update Backend** (`web/app.py`):
```python
# Add endpoint (around line 700)
@app.post("/api/ganancias/cierre-mediodía")
def cierre_mediodía_endpoint(payload: MonthlyClosurePayload, request: Request):
    # ... copy from existing endpoint, change tipo_cierre="mediodía"
```

3. **Update Queries** (`src/ventas_store.py`):
```python
def resumen_ventas_mediodía(fecha: str) -> dict:
    """Resumen de ventas activas en MEDIODÍA (10:00-16:00)"""
    # Copy from resumen_ventas_mañana, change hour range
    # 10:00 = HOUR >= 10
    # 16:00 = HOUR < 16
```

4. **Update Closure Logic** (`src/monthly_closure.py`):
```python
def cerrar_mediodía(usuario: str) -> tuple[dict, Path | None]:
    """Cierre de mediodía (10:00-16:00)"""
    from src.ventas_store import resumen_ventas_mediodía
    fecha = datetime.now().strftime("%Y-%m-%d")
    anio_mes = datetime.now().strftime("%Y-%m")
    resumen = resumen_ventas_mediodía(fecha)
    return _cerrar_dia_generico(usuario, "mediodía", resumen, fecha, anio_mes)
```

5. **Update Scheduler** (`web/scheduler.py`):
```python
# Add to init_scheduler() around line 150
scheduler.add_job(
    _wrap_cierre("mediodía", cerrar_mediodía),
    trigger=CronTrigger(hour=16, minute=0),
    id="cierre_mediodía",
    name="Cierre de mediodía automático",
    replace_existing=True,
    max_instances=1,
)
logger.info("📅 Programado: Cierre de mediodía a las 16:00")
```

6. **Add Tests** (`tests/test_cierres_new_types.py`):
```python
def test_resumen_ventas_mediodía():
    """Test new mediodía period"""
    mediodía = resumen_ventas_mediodía('2026-06-23')
    assert 'cantidad_ventas' in mediodía
    assert 'periodo' in mediodía
```

---

### Task: Change Automation Schedule (e.g., Move Mañana to 15:00)

**File**: `web/scheduler.py` - `init_scheduler()` function

**Change**:
```python
# BEFORE
scheduler.add_job(
    _wrap_cierre("mañana", cerrar_mañana),
    trigger=CronTrigger(hour=14, minute=0),  # <- 14:00
    id="cierre_mañana",
)

# AFTER
scheduler.add_job(
    _wrap_cierre("mañana", cerrar_mañana),
    trigger=CronTrigger(hour=15, minute=0),  # <- 15:00
    id="cierre_mañana",
)
```

**Also Update**:
- `index.html` line ~2339 description "14:00" → "15:00"
- `CIERRES_ARCHITECTURE.md` schedule table
- User documentation

---

### Task: Change Period Times (e.g., Mañana 05:00-13:00 instead of 06:00-14:00)

**⚠️ WARNING**: Not recommended. Affects many locations.

**Locations to Update**:

1. **Queries** (`src/ventas_store.py`):
```python
# resumen_ventas_mañana
AND CAST(strftime('%H', datetime(created_at, 'localtime')) AS INTEGER) >= 5   # was 6
AND CAST(strftime('%H', datetime(created_at, 'localtime')) AS INTEGER) < 13   # was 14
```

2. **UI** (`index.html`):
```javascript
'mañana': { 
  descripcion: 'Cierre de Mañana (05:00-13:00)'  // was (06:00-14:00)
},
```

3. **Documentation**: Update all `.md` files

**Better Approach**: 
Move period times to configuration file (`config/periods.json`) and load at startup.

---

## 📊 Monitoring & Alerting

### Log Patterns to Watch

**Good Signs** (everything working):
```
✅ [AUTOMÁTICO] Iniciando cierre de mañana...
✅ ✓ Cierre de mañana completado automáticamente
✅ Scheduler de cierres automáticos iniciado
✅ Cierre mañana. usuario=SISTEMA periodo=mañana ventas=18 total=542.50
```

**Warning Signs** (investigate):
```
⚠️ No se pudo cargar estado de automatización
⚠️ Scheduler ya está en ejecución
⚠️ APScheduler no está instalado
```

**Error Signs** (fix immediately):
```
❌ [AUTOMÁTICO] Error en cierre automático
❌ ✗ Error en cierre automático de tarde
❌ No se pudo configurar la carpeta
❌ Error al inicializar scheduler
```

### Monitoring Queries

```sql
-- Check closure frequency
SELECT tipo_cierre, COUNT(*) as count, MAX(created_at) as last_run
FROM cierres_diarios
WHERE DATE(fecha) >= DATE('now', '-7 days')
GROUP BY tipo_cierre;

-- Check for failures (archived but not registered)
SELECT COUNT(*) FROM ventas
WHERE estado = 'archived'
  AND DATE(created_at) = DATE('now')
  AND NOT EXISTS (
    SELECT 1 FROM cierres_diarios 
    WHERE DATE(fecha) = DATE('now')
  );

-- Check Excel file generation
SELECT COUNT(*) as total, COUNT(CASE WHEN archivo_excel IS NOT NULL THEN 1 END) as with_file
FROM cierres_diarios
WHERE DATE(fecha) >= DATE('now', '-7 days');
```

---

## 🔗 Documentation Structure

```
generar_para_email/docs/
├── CIERRES_BUGS_FIXED.md          (This file)
│   └── What bugs were fixed & how
├── CIERRES_ARCHITECTURE.md
│   └── How system is designed & works
├── CIERRES_MAINTENANCE.md
│   └── How to maintain & debug (current file)
├── MANUAL_CIERRES_CLIENTA.md
│   └── User guide for end-users
└── README.md
    └── General project info
```

---

## 📞 When in Doubt

1. **Check logs** first: `generar_para_email/logs/app.log`
2. **Run test case** from "Manual Test Cases" section above
3. **Verify database** using provided SQL queries
4. **Check configuration** - timezone, `CIERRES_DIR`, `DATA_DIR`
5. **Consult architecture** document for design details
6. **Review bug fixes** document for known issues

---

## ✅ Maintenance Schedule

| Task | Frequency | Owner |
|------|-----------|-------|
| Review logs for errors | Daily | DevOps |
| Test manual closures | Weekly | QA |
| Verify automation runs | Daily | Automated |
| Check database integrity | Weekly | DBA |
| Update documentation | When changes made | Dev Team |
| Audit Excel file generation | Monthly | Finance |
| Test disaster recovery | Quarterly | DevOps |

---

**Last Updated**: 2026-06-23
**Version**: 1.0
**Status**: Production Ready ✅
