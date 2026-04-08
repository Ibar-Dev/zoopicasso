#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Uso: $0 <dominio|NO_DOMAIN> <ruta_repo_destino>"
  echo "Ejemplo con dominio: $0 facturas.tudominio.com /opt/facturas-app"
  echo "Ejemplo sin dominio:  $0 NO_DOMAIN /opt/facturas-app"
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
sudo apt-get update -y
sudo apt-get install -y curl ca-certificates nginx certbot python3-certbot-nginx

if ! command -v uv >/dev/null 2>&1; then
  echo "[2/8] Instalando uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi

export PATH="$HOME/.local/bin:$PATH"

if [[ ! -d "$APP_DIR" ]]; then
  echo "No existe $APP_DIR"
  echo "Sube el repo y vuelve a ejecutar."
  exit 1
fi

echo "[3/8] Sincronizando dependencias"
cd "$APP_DIR"
uv sync

echo "[4/8] Preparando directorios"
mkdir -p facturas logs data

echo "[5/8] Instalando servicio systemd"
sudo cp deploy/facturas-web.service /etc/systemd/system/facturas-web.service
sudo sed -i "s|/opt/facturas-app|$DESTINO|g" /etc/systemd/system/facturas-web.service
sudo sed -i "s|CAMBIA_ESTA_CLAVE_SUPER_SECRETA|$(openssl rand -hex 32)|g" /etc/systemd/system/facturas-web.service
if [[ "$SIN_DOMINIO" == true ]]; then
  sudo sed -i "s|CAMBIA_HTTPS_ONLY|false|g" /etc/systemd/system/facturas-web.service
else
  sudo sed -i "s|CAMBIA_HTTPS_ONLY|true|g" /etc/systemd/system/facturas-web.service
fi

sudo systemctl daemon-reload
sudo systemctl enable facturas-web
sudo systemctl restart facturas-web

echo "[6/8] Configurando Nginx"
sudo cp deploy/facturas-nginx.conf /etc/nginx/sites-available/facturas-web
if [[ "$SIN_DOMINIO" == true ]]; then
  sudo sed -i "s|TU_DOMINIO_AQUI|_|g" /etc/nginx/sites-available/facturas-web
else
  sudo sed -i "s|TU_DOMINIO_AQUI|$DOMINIO|g" /etc/nginx/sites-available/facturas-web
fi

sudo ln -sf /etc/nginx/sites-available/facturas-web /etc/nginx/sites-enabled/facturas-web
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx

echo "[7/8] Activando HTTPS (Let's Encrypt)"
if [[ "$SIN_DOMINIO" == true ]]; then
  echo "Sin dominio: se omite Let's Encrypt. La app quedara en HTTP por IP."
else
  sudo certbot --nginx -d "$DOMINIO" --non-interactive --agree-tos -m admin@"$DOMINIO" --redirect || true
fi

echo "[8/8] Verificación"
systemctl --no-pager --full status facturas-web | head -n 20 || true
if [[ "$SIN_DOMINIO" == true ]]; then
  IP_PUBLICA="$(hostname -I | awk '{print $1}')"
  curl -fsS "http://127.0.0.1/api/health" || true
  echo "Deploy terminado. URL temporal: http://$IP_PUBLICA"
else
  curl -fsS "https://$DOMINIO/api/health" || true
  echo "Deploy terminado. URL: https://$DOMINIO"
fi
