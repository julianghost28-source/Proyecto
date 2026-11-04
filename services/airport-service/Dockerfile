FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/packages/pis-platform:/app/services/airport-service \
    PORT=8010

WORKDIR /app

COPY packages/pis-platform /app/packages/pis-platform
COPY services/airport-service /app/services/airport-service

RUN pip install --no-cache-dir /app/packages/pis-platform

WORKDIR /app/services/airport-service

EXPOSE 8010

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8010/health', timeout=3)"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8010"]
