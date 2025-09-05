FROM python:3.11-slim

WORKDIR /app

# Paquetes base
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    ca-certificates curl && rm -rf /var/lib/apt/lists/*

# Dependencias Python
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Código
COPY app /app/app

ENV PYTHONUNBUFFERED=1
EXPOSE 8080

# Servidor FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
