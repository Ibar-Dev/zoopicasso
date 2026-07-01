@echo off
REM ============================================================================
REM install_local_agent.bat - Instalador del Agente de Impresión Local
REM ============================================================================
REM
REM Este script:
REM   1. Verifica Python
REM   2. Crea virtual environment
REM   3. Instala dependencias
REM   4. Crea carpeta de tickets
REM   5. Ejecuta poll_and_print.py
REM
REM Uso: double-click en install_local_agent.bat
REM
REM ============================================================================

setlocal enabledelayedexpansion

REM Colores para output (Windows 10+)
for /F %%A in ('echo prompt $H^| cmd') do set "BS=%%A"

REM Cambiar a directorio del script
cd /d "%~dp0"

echo.
echo ============================================================================
echo  INSTALADOR: Agente Local de Impresion y Sincronizacion
echo ============================================================================
echo.

REM ────────────────────────────────────────────────────────────────────────
REM Paso 1: Verificar Python
REM ────────────────────────────────────────────────────────────────────────

echo [1/5] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Python no esta instalado o no esta en PATH
    echo Descarga Python desde https://www.python.org/
    echo Asegurate de marcar "Add Python to PATH" en la instalacion
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo   [OK] %PYTHON_VERSION% encontrado

REM ────────────────────────────────────────────────────────────────────────
REM Paso 2: Crear virtual environment
REM ────────────────────────────────────────────────────────────────────────

echo.
echo [2/5] Preparando virtual environment...
if exist "venv" (
    echo   [OK] Virtual environment ya existe
) else (
    echo   Creando venv...
    python -m venv venv
    if errorlevel 1 (
        echo   ERROR: No se pudo crear virtual environment
        pause
        exit /b 1
    )
    echo   [OK] Virtual environment creado
)

REM Activar venv
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: No se pudo activar virtual environment
    pause
    exit /b 1
)

REM ────────────────────────────────────────────────────────────────────────
REM Paso 3: Instalar dependencias
REM ────────────────────────────────────────────────────────────────────────

echo.
echo [3/5] Instalando dependencias...
python -m pip install --upgrade pip -q
python -m pip install requests -q
if errorlevel 1 (
    echo   ERROR: No se pudo instalar dependencias
    pause
    exit /b 1
)
echo   [OK] Dependencias instaladas

REM ────────────────────────────────────────────────────────────────────────
REM Paso 4: Crear carpeta de tickets
REM ────────────────────────────────────────────────────────────────────────

echo.
echo [4/5] Preparando carpeta de tickets...
set TICKETS_FOLDER=C:\Facturas_Tickets
if exist "%TICKETS_FOLDER%" (
    echo   [OK] Carpeta ya existe: %TICKETS_FOLDER%
) else (
    echo   Creando carpeta: %TICKETS_FOLDER%
    mkdir "%TICKETS_FOLDER%" >nul 2>&1
    if errorlevel 1 (
        echo   ERROR: No se pudo crear carpeta
        echo   Intenta usar una ruta diferente o ejecuta como administrador
        pause
        exit /b 1
    )
    echo   [OK] Carpeta creada
)

REM ────────────────────────────────────────────────────────────────────────
REM Paso 5: Mostrar configuración y ejecutar
REM ────────────────────────────────────────────────────────────────────────

echo.
echo [5/5] Listo para ejecutar
echo.
echo ============================================================================
echo  CONFIGURACION
echo ============================================================================
echo.
echo   Servidor:           http://localhost:8000
echo   Carpeta de tickets: %TICKETS_FOLDER%
echo   Log file:           %TICKETS_FOLDER%\poll_and_print.log
echo.
echo CAMBIAR SERVIDOR (Produccion):
echo   set PRINTER_SERVER_URL=https://zoopicasso.onrender.com
echo   python poll_and_print.py
echo.
echo ============================================================================
echo.

REM Confirmar inicio
set /p START="Iniciar agente ahora? (s/n): "
if /i "%START%"=="s" (
    echo.
    echo Iniciando agente...
    echo (Presiona Ctrl+C para detener)
    echo.
    
    REM Asegurar que TICKETS_FOLDER existe antes de ejecutar
    if not exist "%TICKETS_FOLDER%" mkdir "%TICKETS_FOLDER%"
    
    REM Ejecutar agente
    set TICKETS_FOLDER=%TICKETS_FOLDER%
    python poll_and_print.py
) else (
    echo.
    echo Para iniciar manualmente despues, ejecuta:
    echo   venv\Scripts\activate.bat
    echo   python poll_and_print.py
    echo.
)

pause
