#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Uso: $0 <ruta_app> <archivo_backup.tar.gz>"
  echo "Ejemplo: $0 /opt/facturas-app/generar_para_email /var/backups/facturas/facturas_backup_20260408_130000.tar.gz"
  exit 1
fi

APP_DIR="$1"
ARCHIVE="$2"
TMP_DIR="/tmp/facturas_restore_$$"

if [[ ! -f "$ARCHIVE" ]]; then
  echo "No existe backup: $ARCHIVE"
  exit 1
fi

sudo systemctl stop facturas-web

mkdir -p "$TMP_DIR"
tar -xzf "$ARCHIVE" -C "$TMP_DIR"

rm -rf "$APP_DIR/data" "$APP_DIR/facturas" "$APP_DIR/logs"
cp -a "$TMP_DIR/data" "$APP_DIR/data"
cp -a "$TMP_DIR/facturas" "$APP_DIR/facturas"
cp -a "$TMP_DIR/logs" "$APP_DIR/logs"

rm -rf "$TMP_DIR"

sudo systemctl start facturas-web
sudo systemctl --no-pager --full status facturas-web | head -n 15 || true

echo "Restore completado desde: $ARCHIVE"
