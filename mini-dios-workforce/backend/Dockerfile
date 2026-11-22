# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DIOS_AUDIT_DB=/data/audit.db \
    PORT=8000

WORKDIR /app

COPY requirements.txt .
# Offline/air-gapped support: if a local ./wheels directory is vendored, install offline; otherwise use PyPI.
RUN if [ -d /wheels ]; then \
      pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt; \
    else \
      pip install --no-cache-dir -r requirements.txt; \
    fi

COPY . .
RUN mkdir -p /data

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --retries=5 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", \"8000\")}/api/health')" || exit 1

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips=*"]
