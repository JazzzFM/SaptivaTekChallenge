FROM python:3.11-slim

ENV PYTHONUNBUFFERED=True
ENV PYTHONDONTWRITEBYTECODE=1
ENV APP_HOME=/app

WORKDIR $APP_HOME

RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data
RUN mkdir -p data/vector_index

RUN chmod -R 755 data/

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port $PORT --workers 1 --log-level info"]