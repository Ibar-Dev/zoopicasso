FROM python:3.11-slim

WORKDIR /app

# Dependencias
COPY requirements-web.txt .
RUN pip install --no-cache-dir -r requirements-web.txt

# Código de la aplicación
COPY web/        web/
COPY src/        src/
COPY core/       core/
COPY tickets_src/__init__.py     tickets_src/__init__.py
COPY tickets_src/ticket_model.py tickets_src/ticket_model.py
COPY tickets_src/excel_writer.py tickets_src/excel_writer.py

# Directorios de runtime (montados como volúmenes en docker-compose)
RUN mkdir -p data facturas logs

EXPOSE 8000
CMD ["uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8000"]
