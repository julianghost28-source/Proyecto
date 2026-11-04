FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/packages/pis-platform:/app/services/notification-service \
    PORT=8000

WORKDIR /app
COPY packages/pis-platform /app/packages/pis-platform
COPY services/notification-service /app/services/notification-service
RUN pip install --no-cache-dir /app/packages/pis-platform

WORKDIR /app/services/notification-service
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000"]
