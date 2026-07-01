#!/bin/bash
################################################################################
# install_local_agent.sh - Instalador del Agente de Impresión Local (Linux/Mac)
################################################################################
#
# Este script:
#   1. Verifica Python
#   2. Crea virtual environment
#   3. Instala dependencias
#   4. Crea carpeta de tickets
#   5. Ejecuta poll_and_print.py
#
# Uso: chmod +x install_local_agent.sh && ./install_local_agent.sh
#
################################################################################

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directorio del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "================================================================================"
echo "  INSTALADOR: Agente Local de Impresión y Sincronización"
echo "================================================================================"
echo ""

# ──────────────────────────────────────────────────────────────────────────────
# Paso 1: Verificar Python
# ──────────────────────────────────────────────────────────────────────────────

echo -e "${BLUE}[1/5]${NC} Verificando Python..."

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}  ERROR:${NC} Python no está instalado"
    echo ""
    echo "  Linux (Debian/Ubuntu):"
    echo "    sudo apt-get update && sudo apt-get install python3 python3-venv python3-pip"
    echo ""
    echo "  macOS (Homebrew):"
    echo "    brew install python3"
    echo ""
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo -e "  ${GREEN}[OK]${NC} $PYTHON_VERSION encontrado"

# ──────────────────────────────────────────────────────────────────────────────
# Paso 2: Crear virtual environment
# ──────────────────────────────────────────────────────────────────────────────

echo ""
echo -e "${BLUE}[2/5]${NC} Preparando virtual environment..."

if [ -d "venv" ]; then
    echo -e "  ${GREEN}[OK]${NC} Virtual environment ya existe"
else
    echo "  Creando venv..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo -e "  ${RED}ERROR:${NC} No se pudo crear virtual environment"
        exit 1
    fi
    echo -e "  ${GREEN}[OK]${NC} Virtual environment creado"
fi

# Activar venv
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR:${NC} No se pudo activar virtual environment"
    exit 1
fi

# ──────────────────────────────────────────────────────────────────────────────
# Paso 3: Instalar dependencias
# ──────────────────────────────────────────────────────────────────────────────

echo ""
echo -e "${BLUE}[3/5]${NC} Instalando dependencias..."

pip install --upgrade pip -q
pip install requests -q

if [ $? -ne 0 ]; then
    echo -e "  ${RED}ERROR:${NC} No se pudo instalar dependencias"
    exit 1
fi

echo -e "  ${GREEN}[OK]${NC} Dependencias instaladas"

# ──────────────────────────────────────────────────────────────────────────────
# Paso 4: Crear carpeta de tickets
# ──────────────────────────────────────────────────────────────────────────────

echo ""
echo -e "${BLUE}[4/5]${NC} Preparando carpeta de tickets..."

# Detectar SO y usar carpeta apropiada
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    TICKETS_FOLDER="$HOME/Facturas_Tickets"
else
    # Linux
    TICKETS_FOLDER="$HOME/Facturas_Tickets"
fi

if [ -d "$TICKETS_FOLDER" ]; then
    echo -e "  ${GREEN}[OK]${NC} Carpeta ya existe: $TICKETS_FOLDER"
else
    echo "  Creando carpeta: $TICKETS_FOLDER"
    mkdir -p "$TICKETS_FOLDER"
    if [ $? -ne 0 ]; then
        echo -e "  ${RED}ERROR:${NC} No se pudo crear carpeta"
        exit 1
    fi
    echo -e "  ${GREEN}[OK]${NC} Carpeta creada"
fi

# ──────────────────────────────────────────────────────────────────────────────
# Paso 5: Mostrar configuración y ejecutar
# ──────────────────────────────────────────────────────────────────────────────

echo ""
echo -e "${BLUE}[5/5]${NC} Listo para ejecutar"
echo ""
echo "================================================================================"
echo "  CONFIGURACION"
echo "================================================================================"
echo ""
echo "  Servidor:           http://localhost:8000"
echo "  Carpeta de tickets: $TICKETS_FOLDER"
echo "  Log file:           $TICKETS_FOLDER/poll_and_print.log"
echo ""
echo "CAMBIAR SERVIDOR (Producción):"
echo "  export PRINTER_SERVER_URL=https://zoopicasso.onrender.com"
echo "  python poll_and_print.py"
echo ""
echo "================================================================================"
echo ""

# Preguntar si iniciar
read -p "Iniciar agente ahora? (s/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]; then
    echo ""
    echo -e "${GREEN}Iniciando agente...${NC}"
    echo "(Presiona Ctrl+C para detener)"
    echo ""
    
    # Asegurar que carpeta existe
    mkdir -p "$TICKETS_FOLDER"
    
    # Ejecutar agente
    export TICKETS_FOLDER="$TICKETS_FOLDER"
    python poll_and_print.py
else
    echo ""
    echo "Para iniciar manualmente después, ejecuta:"
    echo "  source venv/bin/activate"
    echo "  export TICKETS_FOLDER=$TICKETS_FOLDER"
    echo "  python poll_and_print.py"
    echo ""
fi
