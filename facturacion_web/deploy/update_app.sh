#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Uso: $0 <ruta_repo>"
  echo "Ejemplo: $0 /opt/facturas-app"
  exit 1
fi

REPO_DIR="$1"
APP_DIR="$REPO_DIR/generar_para_email"

if [[ ! -d "$APP_DIR" ]]; then
  echo "No existe app dir: $APP_DIR"
  exit 1
fi

cd "$REPO_DIR"

if [[ -d .git ]]; then
  git pull --ff-only
else
  echo "Aviso: no es repositorio git, omitiendo git pull"
fi

cd "$APP_DIR"
uv sync
uv run pytest tests/test_web_app.py -q

sudo systemctl restart facturas-web
sudo systemctl --no-pager --full status facturas-web | head -n 20 || true

echo "Actualizacion completada."