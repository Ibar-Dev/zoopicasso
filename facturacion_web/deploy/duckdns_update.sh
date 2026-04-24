#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DUCKDNS_SUBDOMAIN:-}" || -z "${DUCKDNS_TOKEN:-}" ]]; then
  echo "DUCKDNS_SUBDOMAIN y DUCKDNS_TOKEN son obligatorios"
  exit 1
fi

RESPUESTA="$(curl -fsS "https://www.duckdns.org/update?domains=${DUCKDNS_SUBDOMAIN}&token=${DUCKDNS_TOKEN}&ip=")"
if [[ "$RESPUESTA" != "OK" ]]; then
  echo "DuckDNS fallo: $RESPUESTA"
  exit 1
fi

echo "DuckDNS actualizado: ${DUCKDNS_SUBDOMAIN}.duckdns.org"