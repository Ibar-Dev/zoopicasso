FROM python:3.14-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias para Playwright
RUN apt-get update && apt-get install -y \
    sqlite3 \
    curl \
    libglib2.0-0 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxext6 \
    libxrender1 \
    libxkbcommon0 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libpangocairo-1.0-0 \
    libpango-1.0-0 \
    libcairo2 \
    libdrm2 \
    libgbm1 \
    libasound2 \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    && rm -rf /var/lib/apt/lists/*

# Copiar proyecto
COPY generar_para_email/ .

# Instalar todas las dependencias Python
RUN pip install --no-cache-dir \
    -e . \
    pytest \
    pytest-cov \
    pytest-playwright \
    pytest-asyncio \
    httpx

# Descargar navegadores Playwright
RUN playwright install chromium

# Puerto para FastAPI
EXPOSE 8000

# Por defecto: ejecutar tests (excluyendo e2e que requiere navegador)
CMD ["pytest", "tests/", "-v", "--cov=src", "--cov=web", "--ignore=tests/e2e/"]
