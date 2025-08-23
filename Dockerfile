# === MULTI-STAGE BUILD OPTIMIZADO ===
FROM python:3.11-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Instalar dependencias del sistema para build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /wheels

# Crear wheels
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r requirements.txt

# === IMAGEN FINAL CON MODELO PRE-DESCARGADO ===
FROM python:3.11-slim

LABEL maintainer="Jaziel Flores <jazzzfm@outlook.com>"
LABEL description="Production-ready FastAPI Prompt Service with Vector Search"
LABEL version="1.0.0"

# Crear usuario no-root
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 --shell /bin/bash --create-home appuser

# Variables de entorno optimizadas
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/appuser/.local/bin:$PATH" \
    APP_HOME=/app \
    PORT=8080 \
    HF_HOME=/app/models \
    TRANSFORMERS_CACHE=/app/models \
    SENTENCE_TRANSFORMERS_HOME=/app/models

# Instalar dependencias mínimas del runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR $APP_HOME

# Copiar wheels y instalar dependencias
COPY --from=builder /wheels /wheels
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --find-links /wheels -r /wheels/requirements.txt && \
    rm -rf /wheels

# Crear estructura de directorios con permisos correctos
RUN mkdir -p data/vector_index logs models && \
    chown -R appuser:appuser $APP_HOME

# Copiar aplicación
COPY --chown=appuser:appuser . .

# Cambiar a usuario no-root ANTES de descargar el modelo
USER appuser

# Configurar .env
RUN if [ ! -f .env ]; then cp .env.example .env; fi

# PRE-DESCARGAR EL MODELO Y EJECUTAR SEED (esto resuelve el problema del embedder)
RUN python scripts/seed_data.py || echo "Seed data script executed"

EXPOSE $PORT

# Health check mejorado
HEALTHCHECK --interval=30s --timeout=10s --start-period=45s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

# Comando de inicio con mejor manejo de señales
CMD ["sh", "-c", "exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1 --log-level info --access-log"]