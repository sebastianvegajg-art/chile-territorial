FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CT_AUTODETECTAR_LOTE=1 \
    PORT=8000

WORKDIR /app

COPY apps/api/requirements.txt ./apps/api/requirements.txt
RUN pip install --upgrade pip && pip install -r apps/api/requirements.txt

COPY apps ./apps
COPY analytics ./analytics
COPY contracts ./contracts
COPY pipelines ./pipelines
COPY infra/preparar-datos-oficiales.py ./infra/preparar-datos-oficiales.py

RUN mkdir -p /app/data/published /app/data/raw /app/data/quarantine \
    && useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["sh", "-c", "python infra/preparar-datos-oficiales.py --solo-faltantes && exec uvicorn apps.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
