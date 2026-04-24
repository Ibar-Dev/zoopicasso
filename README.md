# Zoo Picasso — Sistema de tickets y facturas

Dos aplicaciones independientes para Zoo Picasso:

- **Tickets** — Genera, guarda e imprime tickets en TPV (interfaz web, impresora térmica ESC/POS por USB)
- **Facturas** — Genera facturas en `.xlsx` para LibreOffice Calc (interfaz escritorio, sin impresora)

## Requisitos

- [uv](https://docs.astral.sh/uv/) — gestiona Python y dependencias automáticamente

---

## App de Tickets

El codigo de tickets fue refactorizado y ahora vive dentro de `generar_para_email/`:

- Entry point: `generar_para_email/tickets_main.py`
- Modulos: `generar_para_email/tickets_src/`
- Test manual: `generar_para_email/test_manual_tickets.py`
- Datos: `generar_para_email/data/contador.json` y `generar_para_email/data/tickets.xlsx`

### Instalación

```bash
uv sync
```

### Ejecución

```bash
cd generar_para_email
uv run tickets_main.py
```

Abre automáticamente el navegador en `http://localhost:8080`.

### Impresora

Modelo: **POS-80** conectada por USB (`VID 1FC9` / `PID 2016`, rollo 80mm, 48 caracteres de ancho).

**En Windows** es necesario instalar el driver WinUSB con [Zadig](https://zadig.akeo.ie):

1. Conectar la impresora por USB
2. Abrir Zadig → seleccionar el dispositivo POS-80
3. Instalar driver **WinUSB**

### Tests manuales

```bash
cd generar_para_email
uv run test_manual_tickets.py                                   # Sin impresora
ZOO_PICASSO_TEST_PRINT=1 uv run test_manual_tickets.py          # Con impresora
```

---

## App de Facturas (Gisselle Marin Tabares)

Genera facturas en formato `.xlsx` para enviar por email.
Los precios son finales (IVA incluido) y no se suma IVA adicional.

Incluye dos modos:
- Escritorio (Flet)
- Web (FastAPI + login en navegador)

### Ejecutar facturas

```bash
uv run generar_para_email/main.py
```

Las facturas se guardan en `generar_para_email/facturas/factura_YYYY_NNN.xlsx`.

### Ejecutar versión web (local)

```bash
cd generar_para_email
uv run uvicorn web.app:app --host 127.0.0.1 --port 8000
```

Abrir en navegador: `http://127.0.0.1:8000`

### Deploy barato en VPS (recomendado)

Recomendación de coste: VPS básico (3-6 EUR/mes) para evitar suspensión y pérdida de persistencia.

1. Subir repo al VPS en `/opt/facturas-app`
2. Ejecutar:

```bash
cd /opt/facturas-app/generar_para_email
chmod +x deploy/install_vps.sh
./deploy/install_vps.sh tu-dominio.com /opt/facturas-app
```

Sin dominio (modo mas barato):

```bash
cd /opt/facturas-app/generar_para_email
chmod +x deploy/install_vps.sh
./deploy/install_vps.sh NO_DOMAIN /opt/facturas-app
```

Este modo publica por IP en HTTP y omite Let's Encrypt.

Esto configura:
- Servicio systemd `facturas-web`
- Nginx reverse proxy
- HTTPS con Let's Encrypt

Alternativas de dominio gratis para habilitar HTTPS luego:
- DuckDNS
- No-IP (plan gratuito)

### Deploy en Render (muy simple)

Este repo ya incluye `render.yaml` para desplegar la app web de facturas.

1. En Render: **New +** → **Blueprint**
2. Conectar el repo `Ibar-Dev/zoopicasso`
3. Render detecta `render.yaml` y crea el servicio `facturas-gisselle-web`
4. Esperar a que termine el deploy y abrir la URL pública (`https://...onrender.com`)

Notas:

- La app web queda publicada desde `generar_para_email`.
- `WEB_SESSION_SECRET` se genera automáticamente en Render.
- En Render se usa HTTPS, por eso `WEB_SESSION_HTTPS_ONLY=true`.
- Si el servicio free queda inactivo, Render puede tardar unos segundos en “despertar”.

### HTTPS gratis con DuckDNS (recomendado)

1. Crear subdominio gratis en DuckDNS (ejemplo: `misfacturas.duckdns.org`) y copiar token.
2. En el VPS crear credenciales:

```bash
sudo mkdir -p /etc/facturas
sudo tee /etc/facturas/duckdns.env > /dev/null <<'EOF'
DUCKDNS_SUBDOMAIN=misfacturas
DUCKDNS_TOKEN=TU_TOKEN_DUCKDNS
EOF
sudo chmod 600 /etc/facturas/duckdns.env
```

3. Activar auto-actualización de IP:

```bash
cd /opt/facturas-app/generar_para_email
chmod +x deploy/duckdns_update.sh
sudo cp deploy/duckdns-update.service /etc/systemd/system/
sudo cp deploy/duckdns-update.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now duckdns-update.timer
sudo systemctl start duckdns-update.service
```

4. Reconfigurar app con dominio DuckDNS:

```bash
cd /opt/facturas-app/generar_para_email
./deploy/install_vps.sh misfacturas.duckdns.org /opt/facturas-app
```

5. Verificar:

```bash
curl -I https://misfacturas.duckdns.org/api/health
```

Archivos de despliegue:
- `generar_para_email/deploy/install_vps.sh`
- `generar_para_email/deploy/facturas-web.service`
- `generar_para_email/deploy/facturas-nginx.conf`

### Operación y mantenimiento (VPS)

Scripts incluidos:
- `generar_para_email/deploy/backup_data.sh`
- `generar_para_email/deploy/restore_data.sh`
- `generar_para_email/deploy/update_app.sh`

Dar permisos una sola vez:

```bash
cd /opt/facturas-app/generar_para_email/deploy
chmod +x backup_data.sh restore_data.sh update_app.sh
```

Backup manual:

```bash
./backup_data.sh /opt/facturas-app/generar_para_email /var/backups/facturas 30
```

Restore:

```bash
./restore_data.sh /opt/facturas-app/generar_para_email /var/backups/facturas/facturas_backup_YYYYMMDD_HHMMSS.tar.gz
```

Actualizar app (pull + sync + test web + restart):

```bash
./update_app.sh /opt/facturas-app
```

Backup automático diario (cron):

```bash
sudo crontab -e
```

Añadir línea:

```bash
30 2 * * * /opt/facturas-app/generar_para_email/deploy/backup_data.sh /opt/facturas-app/generar_para_email /var/backups/facturas 30 >> /var/log/facturas_backup.log 2>&1
```

### Instalación en Windows (ordenador de Gisselle)

1. Instalar uv: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
2. Copiar la carpeta `generar_para_email/` al PC de destino
3. Doble clic en `generar_para_email/Facturas.bat`

---

## Estructura del proyecto

```text
zoo_picasso/
├── main.py                         # Wrapper de compatibilidad para tickets
├── test_manual.py                  # Wrapper de compatibilidad para test tickets
├── Facturas.bat                    # Atajo Windows para lanzar facturas
├── render.yaml                     # Deploy web de facturas
└── generar_para_email/             # App unificada (facturas + tickets)
    ├── main.py                     # Facturas escritorio (Flet)
    ├── tickets_main.py             # Tickets TPV (Flet)
    ├── test_manual_tickets.py      # Test manual de tickets
    ├── pyproject.toml              # Dependencias unificadas
    ├── src/                        # Dominio de facturas
    ├── tickets_src/                # Dominio de tickets
    ├── web/                        # Facturas web (FastAPI)
    ├── data/                       # Contadores y Excel runtime
    └── facturas/                   # Facturas generadas
```
