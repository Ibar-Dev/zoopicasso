#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Uso: $0 <ruta_app> [ruta_backups] [dias_retencion]"
  echo "Ejemplo: $0 /opt/facturas-app/generar_para_email /var/backups/facturas 30"
  exit 1
fi

APP_DIR="$1"
BACKUP_DIR="${2:-/var/backups/facturas}"
RETENTION_DAYS="${3:-30}"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
TMP_DIR="/tmp/facturas_backup_${TIMESTAMP}"
ARCHIVE="${BACKUP_DIR}/facturas_backup_${TIMESTAMP}.tar.gz"

mkdir -p "$BACKUP_DIR"
mkdir -p "$TMP_DIR"

cp -a "$APP_DIR/data" "$TMP_DIR/data"
cp -a "$APP_DIR/facturas" "$TMP_DIR/facturas"
cp -a "$APP_DIR/logs" "$TMP_DIR/logs"

# Guardar lock y pyproject ayuda a reconstruir entorno si hace falta.
cp -a "$APP_DIR/pyproject.toml" "$TMP_DIR/pyproject.toml"
cp -a "$APP_DIR/uv.lock" "$TMP_DIR/uv.lock"

tar -czf "$ARCHIVE" -C "$TMP_DIR" .
rm -rf "$TMP_DIR"

find "$BACKUP_DIR" -type f -name "facturas_backup_*.tar.gz" -mtime +"$RETENTION_DAYS" -delete

echo "Backup creado: $ARCHIVE"