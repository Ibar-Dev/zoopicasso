#!/usr/bin/env bash
set -euo pipefail

DRY_RUN="${DRY_RUN:-0}"

run_cmd() {
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[DRY_RUN] $*"
    return 0
  fi
  "$@"
}

run_sudo() {
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[DRY_RUN] sudo $*"
    return 0
  fi
  sudo "$@"
}

if [[ $# -lt 2 ]]; then
  echo "Uso: $0 <dominio|NO_DOMAIN> <ruta_repo_destino>"
  echo "Ejemplo con dominio: $0 facturas.tudominio.com /opt/facturas-app"
  echo "Ejemplo sin dominio:  $0 NO_DOMAIN /opt/facturas-app"
  echo "Simulación: DRY_RUN=1 $0 NO_DOMAIN /tmp/facturas-app"
  exit 1
fi

DOMINIO="$1"
DESTINO="$2"
APP_DIR="$DESTINO/generar_para_email"
SIN_DOMINIO=false

if [[ "$DOMINIO" == "NO_DOMAIN" ]]; then
  SIN_DOMINIO=true
fi

echo "[1/8] Instalando paquetes base"
run_sudo apt-get update -y
run_sudo apt-get install -y curl ca-certificates nginx certbot python3-certbot-nginx

if ! command -v uv >/dev/null 2>&1; then
  echo "[2/8] Instalando uv"
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[DRY_RUN] curl -LsSf https://astral.sh/uv/install.sh | sh"
  else
    curl -LsSf https://astral.sh/uv/install.sh | sh
  fi
fi

export PATH="$HOME/.local/bin:$PATH"

if [[ ! -d "$APP_DIR" ]]; then
  echo "No existe $APP_DIR"
  echo "Sube el repo y vuelve a ejecutar."
  exit 1
fi

echo "[3/8] Sincronizando dependencias"
cd "$APP_DIR"
if [[ "$DRY_RUN" == "1" ]]; then
  echo "[DRY_RUN] uv sync"
else
  uv sync
fi

echo "[4/8] Preparando directorios"
run_cmd mkdir -p facturas logs data

echo "[5/8] Instalando servicio systemd"
run_sudo cp deploy/facturas-web.service /etc/systemd/system/facturas-web.service
CLAVE_SECRETA="$(openssl rand -hex 32)"
run_sudo sed -i "s|/opt/facturas-app|$DESTINO|g" /etc/systemd/system/facturas-web.service
run_sudo sed -i "s|CAMBIA_ESTA_CLAVE_SUPER_SECRETA|$CLAVE_SECRETA|g" /etc/systemd/system/facturas-web.service
if [[ "$SIN_DOMINIO" == true ]]; then
  run_sudo sed -i "s|CAMBIA_HTTPS_ONLY|false|g" /etc/systemd/system/facturas-web.service
else
  run_sudo sed -i "s|CAMBIA_HTTPS_ONLY|true|g" /etc/systemd/system/facturas-web.service
fi

run_sudo systemctl daemon-reload
run_sudo systemctl enable facturas-web
run_sudo systemctl restart facturas-web

echo "[6/8] Configurando Nginx"
run_sudo cp deploy/facturas-nginx.conf /etc/nginx/sites-available/facturas-web
if [[ "$SIN_DOMINIO" == true ]]; then
  run_sudo sed -i "s|TU_DOMINIO_AQUI|_|g" /etc/nginx/sites-available/facturas-web
else
  run_sudo sed -i "s|TU_DOMINIO_AQUI|$DOMINIO|g" /etc/nginx/sites-available/facturas-web
fi

run_sudo ln -sf /etc/nginx/sites-available/facturas-web /etc/nginx/sites-enabled/facturas-web
run_sudo rm -f /etc/nginx/sites-enabled/default
run_sudo nginx -t
run_sudo systemctl reload nginx

echo "[7/8] Activando HTTPS (Let's Encrypt)"
if [[ "$SIN_DOMINIO" == true ]]; then
  echo "Sin dominio: se omite Let's Encrypt. La app quedara en HTTP por IP."
else
  run_sudo certbot --nginx -d "$DOMINIO" --non-interactive --agree-tos -m admin@"$DOMINIO" --redirect || true
fi

echo "[8/8] Verificación"
if [[ "$DRY_RUN" == "1" ]]; then
  echo "[DRY_RUN] systemctl --no-pager --full status facturas-web | head -n 20"
else
  systemctl --no-pager --full status facturas-web | head -n 20 || true
fi
if [[ "$SIN_DOMINIO" == true ]]; then
  IP_PUBLICA="$(hostname -I | awk '{print $1}')"
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[DRY_RUN] curl -fsS http://127.0.0.1/api/health"
  else
    curl -fsS "http://127.0.0.1/api/health" || true
  fi
  echo "Deploy terminado. URL temporal: http://$IP_PUBLICA"
else
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[DRY_RUN] curl -fsS https://$DOMINIO/api/health"
  else
    curl -fsS "https://$DOMINIO/api/health" || true
  fi
  echo "Deploy terminado. URL: https://$DOMINIO"
fi
